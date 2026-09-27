"""Seven-day window: how fast search interest decays after a hurricane.

Source: Google Trends daily interest for "whole house generator", in the hardest-hit
state for each 2024 hurricane, plus the national series across the season. Values
are relative indices scaled 0-100 within each pull, never volumes, and a fresh pull
can differ slightly from an earlier one. The shipped series is therefore pinned in
``inputs/trends-whole-house-generator-2024.csv`` with the date it was pulled;
``--pull`` refreshes it through the unofficial Trends endpoint (trendspy).

Two decay measures per event, both relative to landfall day:

- raw:      baseline = median of the 21 days ending 3 days before landfall;
            days_to_baseline = first day at or below 125% of baseline, counted from
            the peak day onward.
- smoothed: the same on a trailing 7-day mean, which tames the zero-heavy daily
            state series; the multiple (peak / baseline) is reported on this one.

National multiples compare each event's peak in the smoothed US series with the
June 2024 median of that series.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pandas as pd

from article_data.paths import COMPUTED, INPUTS

TERM = "whole house generator"
SERIES_FILE = "trends-whole-house-generator-2024.csv"
BASELINE_DAYS = 21
BASELINE_GAP_DAYS = 3
POST_DAYS = 45
RETURN_THRESHOLD = 1.25
SMOOTH_DAYS = 7
NATIONAL_WINDOW = ("2024-05-15", "2024-12-15")
JUNE = ("2024-06-01", "2024-06-30")


@dataclass(frozen=True)
class Event:
    name: str
    landfall: str
    geo: str
    window: tuple[str, str]


EVENTS = [
    Event("Hurricane Beryl", "2024-07-08", "US-TX", ("2024-05-15", "2024-09-15")),
    Event("Hurricane Helene", "2024-09-26", "US-NC", ("2024-08-01", "2024-12-01")),
    Event("Hurricane Milton", "2024-10-09", "US-FL", ("2024-08-15", "2024-12-15")),
]


def decay(series: pd.Series, landfall: str) -> dict[str, float | int | None]:
    """Baseline, peak, and days back to baseline for one daily series."""
    land = pd.Timestamp(landfall)
    base_end = land - pd.Timedelta(days=BASELINE_GAP_DAYS)
    base = series.loc[base_end - pd.Timedelta(days=BASELINE_DAYS - 1) : base_end]
    baseline = float(base.median())
    post = series.loc[land : land + pd.Timedelta(days=POST_DAYS)]
    peak_at = pd.Timestamp(cast(datetime, post.idxmax()))
    peak = float(post.max())
    back = post.loc[peak_at:]
    returned = back[back <= baseline * RETURN_THRESHOLD]
    return {
        "baseline": baseline,
        "peak": peak,
        "multiple": round(peak / baseline, 1) if baseline else None,
        "peak_day": int((peak_at - land).days),
        "days_to_baseline": int((returned.index[0] - land).days) if len(returned) else None,
    }


def smooth(series: pd.Series) -> pd.Series:
    return series.rolling(SMOOTH_DAYS).mean()


def event_table(series: pd.DataFrame, events: list[Event] = EVENTS) -> pd.DataFrame:
    """One row per event with raw and smoothed decay measures side by side."""
    rows = []
    for ev in events:
        s = event_series(series, ev.geo, ev.window)
        raw = decay(s, ev.landfall)
        sm = decay(smooth(s), ev.landfall)
        rows.append(
            {
                "event": ev.name,
                "geo": ev.geo,
                "landfall": ev.landfall,
                **{f"raw_{k}": v for k, v in raw.items()},
                **{f"smoothed_{k}": v for k, v in sm.items()},
            }
        )
    return pd.DataFrame(rows)


def national_table(series: pd.DataFrame, events: list[Event] = EVENTS) -> pd.DataFrame:
    """Each event's US peak (smoothed) against the June 2024 median of the same series."""
    us = smooth(event_series(series, "US", NATIONAL_WINDOW))
    june = float(us.loc[JUNE[0] : JUNE[1]].median())
    rows = []
    for ev in events:
        land = pd.Timestamp(ev.landfall)
        post = us.loc[land : land + pd.Timedelta(days=POST_DAYS)]
        rows.append(
            {
                "event": ev.name,
                "june_median": june,
                "peak": float(post.max()),
                "multiple": round(float(post.max()) / june, 1) if june else None,
                "peak_day": int((pd.Timestamp(cast(datetime, post.idxmax())) - land).days),
            }
        )
    return pd.DataFrame(rows)


def event_series(series: pd.DataFrame, geo: str, window: tuple[str, str]) -> pd.Series:
    """The pinned daily series for one geo and pull window, indexed by date."""
    d = series[(series["geo"] == geo) & (series["window_start"] == window[0])]
    if d.empty:
        raise ValueError(f"no pinned series for {geo} starting {window[0]}")
    s = pd.Series(d["value"].to_numpy(dtype=float), index=pd.to_datetime(d["date"]))
    return s.sort_index()


def pull(events: list[Event] = EVENTS, term: str = TERM, *, pause: float = 5.0) -> pd.DataFrame:
    """Fetch every event series and the national series; one long table with pulled_at."""
    from trendspy import Trends  # unofficial endpoint; imported only when pulling

    tr = Trends()
    pulled_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ")
    frames = []
    pulls = [(ev.geo, ev.window) for ev in events] + [("US", NATIONAL_WINDOW)]
    for geo, (start, end) in pulls:
        df = cast(pd.DataFrame, tr.interest_over_time([term], timeframe=f"{start} {end}", geo=geo))
        if df is None or df.empty:
            raise RuntimeError(f"empty Trends pull for {geo} {start}..{end}")
        frames.append(
            pd.DataFrame(
                {
                    "term": term,
                    "geo": geo,
                    "window_start": start,
                    "window_end": end,
                    "date": pd.DatetimeIndex(df.index).strftime("%Y-%m-%d"),
                    "value": df[term].to_numpy(dtype=int),
                    "pulled_at": pulled_at,
                }
            )
        )
        time.sleep(pause)
    return pd.concat(frames, ignore_index=True)


def run(
    inputs_dir: Path = INPUTS, out_dir: Path = COMPUTED, *, refresh: bool = False
) -> tuple[pd.DataFrame, pd.DataFrame]:
    pinned = inputs_dir / SERIES_FILE
    if refresh or not pinned.exists():
        inputs_dir.mkdir(parents=True, exist_ok=True)
        pull().to_csv(pinned, index=False)
    series = pd.read_csv(pinned, dtype={"date": str})
    events = event_table(series)
    national = national_table(series)
    out_dir.mkdir(parents=True, exist_ok=True)
    events.to_csv(out_dir / "seven-day-window.csv", index=False, float_format="%.4f")
    national.to_csv(out_dir / "seven-day-window-national.csv", index=False, float_format="%.4f")
    return events, national
