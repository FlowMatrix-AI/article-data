"""Penetration gap: counties with the most qualifying homes among the most outage-exposed.

Qualifying homes approximate the standby-generator market from ACS 2023 5-year:
owner-occupied units valued at or above a threshold (B25075 value buckets) scaled by
the county's owner-occupied single-family-detached share (B25032_003 / B25032_002).

The published table was built at a $300,000 threshold (buckets 021-027), which puts
the national total near 33.7M homes. The reference write-up describes the threshold
as $175,000 (buckets 018-027); that gives 50.9M and a different table. The threshold
is a parameter here so both are one call away; the default is the published one.

The tables come from the Census table-based summary files (pipe-delimited, one file
per table, keyless), not the Census Data API, which now requires a key. Same
release, same estimates.

Outage exposure is EAGLE-I county customer-hours over the mature-coverage window
(2017-2025). Counties in the top quartile of exposure are ranked by qualifying
homes; the top 25 is the published table.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from article_data.eaglei import COUNTY_BURDEN
from article_data.fetch import SOURCES
from article_data.paths import COMPUTED, RAW

COUNTY_GEO_PREFIX = "0500000US"  # summary level 050 = county
# B25075 value buckets: 018 = $175,000-199,999, 021 = $300,000-399,999, 027 = $2,000,000+.
VALUE_BUCKETS = [f"B25075_E{i:03d}" for i in range(1, 28)]
THRESHOLDS = {175_000: 18, 300_000: 21}
DEFAULT_THRESHOLD = 300_000
OWNER_TOTAL = "B25032_E002"
OWNER_DETACHED = "B25032_E003"
EXPOSURE_QUANTILE = 0.75
TOP_N = 25


def read_county_table(path: Path, columns: list[str]) -> pd.DataFrame:
    """County rows of a table-based summary file, indexed by 5-digit FIPS."""
    df = pd.read_csv(path, sep="|", usecols=["GEO_ID", *columns], dtype={"GEO_ID": str})
    df = df[df["GEO_ID"].str.startswith(COUNTY_GEO_PREFIX)].copy()
    df["fips"] = df["GEO_ID"].str.removeprefix(COUNTY_GEO_PREFIX)
    for c in columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.set_index("fips")[columns]


def read_county_names(geos_path: Path) -> pd.Series:
    g = pd.read_csv(
        geos_path,
        sep="|",
        usecols=["SUMLEVEL", "COMPONENT", "GEO_ID", "NAME"],
        dtype=str,
        encoding="utf-8-sig",
    )
    g = g[(g["SUMLEVEL"] == "050") & (g["COMPONENT"] == "00")]
    fips = g["GEO_ID"].str.removeprefix(COUNTY_GEO_PREFIX)
    return pd.Series(g["NAME"].to_numpy(), index=fips, name="name")


def value_buckets_from(threshold: int) -> list[str]:
    """The B25075 buckets whose lower bound is at or above ``threshold`` dollars."""
    return [f"B25075_E{i:03d}" for i in range(THRESHOLDS[threshold], 28)]


def qualifying_homes(
    value: pd.DataFrame,
    tenure: pd.DataFrame,
    names: pd.Series,
    *,
    threshold: int = DEFAULT_THRESHOLD,
) -> pd.DataFrame:
    """(fips, name, qualifying) for every county in the value table."""
    over = value[value_buckets_from(threshold)].sum(axis=1)
    t = tenure.reindex(value.index)
    share = (t[OWNER_DETACHED] / t[OWNER_TOTAL]).where(t[OWNER_TOTAL] > 0, 0.0)
    out = pd.DataFrame({"qualifying": (over * share).round().astype(int)})
    out.insert(0, "name", names.reindex(out.index))
    out.index.name = "fips"
    return out.sort_index().reset_index()


def penetration_gap(
    acs: pd.DataFrame,
    burden: pd.DataFrame,
    *,
    quantile: float = EXPOSURE_QUANTILE,
    top_n: int = TOP_N,
) -> tuple[pd.DataFrame, float]:
    """Top-``top_n`` counties by qualifying homes among the top exposure quartile."""
    gap = acs.merge(burden, on="fips", how="inner")
    cutoff = float(gap["ch_m"].quantile(quantile))
    top = gap[gap["ch_m"] >= cutoff].sort_values("qualifying", ascending=False).head(top_n)
    top = top.assign(ch_m=top["ch_m"].round(1)).reset_index(drop=True)
    return top[["fips", "name", "qualifying", "ch_m"]], cutoff


def load_acs(raw_dir: Path = RAW, *, threshold: int = DEFAULT_THRESHOLD) -> pd.DataFrame:
    value = read_county_table(SOURCES["acs2023_b25075"].path(raw_dir), VALUE_BUCKETS)
    tenure_path = SOURCES["acs2023_b25032"].path(raw_dir)
    tenure = read_county_table(tenure_path, [OWNER_TOTAL, OWNER_DETACHED])
    names = read_county_names(SOURCES["acs2023_geos"].path(raw_dir))
    return qualifying_homes(value, tenure, names, threshold=threshold)


def run(
    raw_dir: Path = RAW, out_dir: Path = COMPUTED, *, threshold: int = DEFAULT_THRESHOLD
) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    acs = load_acs(raw_dir, threshold=threshold)
    burden = pd.read_csv(out_dir / COUNTY_BURDEN, dtype={"fips": str})
    top, cutoff = penetration_gap(acs, burden)
    out_dir.mkdir(parents=True, exist_ok=True)
    acs.to_csv(out_dir / "acs-qualifying-homes.csv", index=False)
    top.to_csv(out_dir / "penetration-gap-top25.csv", index=False)
    return acs, top, cutoff
