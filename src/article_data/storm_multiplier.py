"""Storm multiplier: SAIDI with major event days over SAIDI without, per utility-state.

Source: EIA-861 2024 Reliability file, ``Reliability_States`` sheet, IEEE-1366 block.
The IEEE block is used alone so the utilities are measured the same way. The unit of
analysis is utility-state because that is how EIA reports it.

Rows missing either SAIDI or the customer count are dropped. A row where SAIDI
without major event days exceeds SAIDI with them is impossible by construction
(the "without" series is a subset) and is excluded and counted. A row whose
"without" SAIDI is zero has no defined multiplier and is excluded and counted too.
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from article_data.fetch import SOURCES
from article_data.paths import COMPUTED, RAW

SHEET = "Reliability_States"
MEMBER = "Reliability_2024.xlsx"
HEADER_ROWS = 3  # two band rows plus the column-label row
EXPECTED_COLUMNS = 28

# Column positions in the IEEE block, checked against the label row on load.
COLUMNS = {
    "utility_id": (1, "Utility Number"),
    "utility": (2, "Utility Name"),
    "state": (3, "State"),
    "ownership": (4, "Ownership"),
    "saidi_with_med": (5, "SAIDI (minutes per year)"),
    "saidi_without_med": (8, "SAIDI (minutes per year)"),
    "customers": (14, "Number of Customers"),
}
BAND_LABELS = {5: "All Events (With Major Event Days)", 8: "Without Major Event Days"}

STORM_BELT = frozenset({"TX", "LA", "MS", "AL", "FL", "GA", "SC", "NC", "VA"})
BIG_CUSTOMER_FLOOR = 100_000


@dataclass(frozen=True)
class StormResult:
    rows: pd.DataFrame
    impossible: int  # without-MED SAIDI > with-MED SAIDI
    zero_baseline: int  # without-MED SAIDI == 0


def load_ieee_block(xlsx: Path | io.BytesIO) -> pd.DataFrame:
    """Read the IEEE-1366 block of the Reliability sheet with the layout verified."""
    raw = pd.read_excel(xlsx, sheet_name=SHEET, header=None)
    if raw.shape[1] != EXPECTED_COLUMNS:
        raise ValueError(f"layout changed: {raw.shape[1]} columns, expected {EXPECTED_COLUMNS}")
    bands, labels = raw.iloc[1], raw.iloc[2]
    for col, label in BAND_LABELS.items():
        if bands[col] != label:
            raise ValueError(f"layout changed: column {col} band is {bands[col]!r}, not {label!r}")
    for col, label in COLUMNS.values():
        if labels[col] != label:
            raise ValueError(f"layout changed: column {col} is {labels[col]!r}, not {label!r}")
    if raw.iloc[1, 17] != "All Events (With Major Event Days)":
        raise ValueError("layout changed: the Other Standard block moved")

    body = raw.iloc[HEADER_ROWS:]
    out = pd.DataFrame({name: body[col].to_numpy() for name, (col, _) in COLUMNS.items()})
    for name in ("saidi_with_med", "saidi_without_med", "customers"):
        out[name] = pd.to_numeric(out[name], errors="coerce")
    out["utility_id"] = pd.to_numeric(out["utility_id"], errors="coerce").astype("Int64")
    return out


def compute(block: pd.DataFrame) -> StormResult:
    d = block.dropna(subset=["saidi_with_med", "saidi_without_med", "customers"])
    d = d[d["customers"] > 0]
    zero = d["saidi_without_med"] == 0
    impossible = d["saidi_without_med"] > d["saidi_with_med"]
    keep = d[~zero & ~impossible].copy()
    keep["multiplier"] = keep["saidi_with_med"] / keep["saidi_without_med"]
    keep["storm_hours"] = (keep["saidi_with_med"] - keep["saidi_without_med"]) / 60.0
    keep = keep.sort_values(["multiplier", "utility_id"], ascending=[False, True])
    keep = keep.reset_index(drop=True)
    return StormResult(rows=keep, impossible=int(impossible.sum()), zero_baseline=int(zero.sum()))


def summarize(rows: pd.DataFrame) -> dict[str, float | int]:
    big = rows[rows["customers"] >= BIG_CUSTOMER_FLOOR]
    belt = big[big["state"].isin(STORM_BELT)]
    return {
        "rows": len(rows),
        "median_multiplier": float(rows["multiplier"].median()),
        "big_utilities": len(big),
        "big_median_multiplier": float(big["multiplier"].median()),
        "storm_belt_big_utilities": len(belt),
        "storm_belt_big_median_multiplier": float(belt["multiplier"].median()),
    }


def run(raw_dir: Path = RAW, out_dir: Path = COMPUTED) -> StormResult:
    archive = SOURCES["eia861_2024"].path(raw_dir)
    with zipfile.ZipFile(archive) as z:
        result = compute(load_ieee_block(io.BytesIO(z.read(MEMBER))))
    out_dir.mkdir(parents=True, exist_ok=True)
    result.rows.to_csv(out_dir / "storm-multiplier-2024.csv", index=False)
    return result
