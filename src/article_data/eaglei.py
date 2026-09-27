"""EAGLE-I outage aggregates: county customer-hours by month, and by ISO week for 2025.

Source: ORNL EAGLE-I recorded electricity outages 2014-2025 (figshare 24237376,
CC BY 4.0). Each row is a 15-minute snapshot of customers without power in one
county, so customer-hours = sum(customers_out) * 0.25. Years are aggregated one
file at a time in chunks; a year file is ~1.4 GB and never needs to fit in memory.

Coverage ramps up through 2014-2016; claims about mature coverage use 2017 onward.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

import pandas as pd

from article_data.fetch import SOURCES
from article_data.paths import COMPUTED, RAW

HOURS_PER_SNAPSHOT = 0.25
CHUNK_ROWS = 2_000_000
YEARS = range(2014, 2026)
MATURE_FROM = 2017
COUNTY_KEYS = ["fips", "county", "state"]

COUNTY_MONTH = "eaglei-county-month.csv"  # full output, gitignored (large)
COUNTY_BURDEN = "eaglei-county-burden-2017-2025.csv"  # committed fixture
NATIONAL_MONTH = "eaglei-national-month.csv"  # committed fixture
NATIONAL_WEEK_2025 = "eaglei-2025-national-week.csv"  # committed fixture


def _chunks(csv_path: Path) -> Iterable[pd.DataFrame]:
    header = pd.read_csv(csv_path, nrows=0).columns
    value = "customers_out" if "customers_out" in header else "sum"
    for chunk in pd.read_csv(
        csv_path,
        chunksize=CHUNK_ROWS,
        usecols=["fips_code", "county", "state", value, "run_start_time"],
        dtype={"fips_code": str, "county": str, "state": str},
    ):
        chunk = chunk.dropna(subset=[value]).rename(
            columns={"fips_code": "fips", value: "customers_out"}
        )
        chunk["run_start_time"] = pd.to_datetime(chunk["run_start_time"])
        yield chunk


def aggregate_county_month(csv_path: Path) -> pd.DataFrame:
    """One year file -> (fips, county, state, year, month, customer_hours, snapshots)."""
    parts = []
    for chunk in _chunks(csv_path):
        chunk["year"] = chunk["run_start_time"].dt.year
        chunk["month"] = chunk["run_start_time"].dt.month
        parts.append(
            chunk.groupby(COUNTY_KEYS + ["year", "month"])["customers_out"].agg(["sum", "count"])
        )
    g = pd.concat(parts).groupby(level=list(range(5))).sum().reset_index()
    g["customer_hours"] = g.pop("sum") * HOURS_PER_SNAPSHOT
    g = g.rename(columns={"count": "snapshots"})
    return g[COUNTY_KEYS + ["year", "month", "customer_hours", "snapshots"]]


def aggregate_county_week(csv_path: Path) -> pd.DataFrame:
    """One year file -> (fips, county, state, week, customer_hours), ISO week numbers."""
    parts = []
    for chunk in _chunks(csv_path):
        chunk["week"] = chunk["run_start_time"].dt.isocalendar().week.astype(int)
        parts.append(chunk.groupby(COUNTY_KEYS + ["week"])["customers_out"].sum())
    g = pd.concat(parts).groupby(level=list(range(4))).sum().reset_index()
    g["customer_hours"] = g.pop("customers_out") * HOURS_PER_SNAPSHOT
    return g


def county_burden(
    county_month: pd.DataFrame, years: tuple[int, int] = (MATURE_FROM, 2025)
) -> pd.DataFrame:
    """Customer-hours per county summed over ``years`` inclusive, in millions (``ch_m``)."""
    lo, hi = years
    d = county_month[(county_month["year"] >= lo) & (county_month["year"] <= hi)]
    ch = d.groupby("fips")["customer_hours"].sum() / 1e6
    return ch.rename("ch_m").reset_index()


def national_month(county_month: pd.DataFrame) -> pd.DataFrame:
    """Customer-hours by year and month across all counties, in millions."""
    g = county_month.groupby(["year", "month"])["customer_hours"].sum() / 1e6
    return g.rename("customer_hours_m").reset_index()


def national_week(county_week: pd.DataFrame) -> pd.DataFrame:
    g = county_week.groupby("week")["customer_hours"].sum() / 1e6
    return g.rename("customer_hours_m").reset_index()


def run(
    raw_dir: Path = RAW,
    out_dir: Path = COMPUTED,
    years: Iterable[int] = YEARS,
    *,
    source_for: Callable[[int], Path] | None = None,
    delete_after: bool = False,
) -> pd.DataFrame:
    """Aggregate every requested year and write the county-month table plus fixtures.

    ``source_for`` resolves a year to its raw file (default: the fetched copy under
    ``raw_dir``); passing a fetching callable streams the archive one year at a time.
    ``delete_after`` removes each raw year file once aggregated.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    for year in years:
        src = source_for(year) if source_for else SOURCES[f"eaglei_{year}"].path(raw_dir)
        frames.append(aggregate_county_month(src))
        if year == 2025:
            wk = aggregate_county_week(src)
            wk.to_csv(out_dir / "eaglei-2025-county-week.csv", index=False)
            national_week(wk).to_csv(out_dir / NATIONAL_WEEK_2025, index=False, float_format="%.4f")
        if delete_after:
            src.unlink()
    cm = pd.concat(frames, ignore_index=True)
    cm.to_csv(out_dir / COUNTY_MONTH, index=False)
    county_burden(cm).to_csv(out_dir / COUNTY_BURDEN, index=False, float_format="%.6f")
    national_month(cm).to_csv(out_dir / NATIONAL_MONTH, index=False, float_format="%.4f")
    return cm
