import pandas as pd
import pytest

import reference as ref
from article_data import trends
from article_data.paths import INPUTS


def daily(values: list[float], start: str = "2024-06-01") -> pd.Series:
    return pd.Series(values, index=pd.date_range(start, periods=len(values), freq="D"), dtype=float)


def test_baseline_is_the_median_of_21_days_ending_3_days_before_landfall():
    s = daily([1.0] * 40)
    s.loc["2024-06-07":"2024-06-27"] = 5.0  # exactly the 21-day baseline window for Jun 30
    s.loc["2024-06-28":"2024-06-29"] = 99.0  # the 2-day gap before landfall is excluded
    out = trends.decay(s, "2024-06-30")
    assert out["baseline"] == 5.0


def test_return_is_counted_from_the_peak_and_uses_the_125_percent_threshold():
    s = daily([4.0] * 30 + [10.0, 50.0, 100.0, 40.0, 6.0, 5.0, 4.0, 4.0])
    out = trends.decay(s, "2024-07-01")  # day 0 = 10, day 2 = 100 (peak)
    assert out["peak"] == 100.0
    assert out["peak_day"] == 2
    assert out["multiple"] == 25.0
    assert out["days_to_baseline"] == 5  # first day at or below 5.0


def test_no_return_within_the_window_is_reported_as_none_not_a_number():
    s = daily([2.0] * 30 + [50.0] * 50)
    out = trends.decay(s, "2024-07-01")
    assert out["days_to_baseline"] is None


def test_zero_baseline_leaves_the_multiple_undefined():
    s = daily([0.0] * 30 + [50.0, 0.0, 0.0])
    out = trends.decay(s, "2024-07-01")
    assert out["baseline"] == 0.0
    assert out["multiple"] is None


@pytest.fixture(scope="module")
def series() -> pd.DataFrame:
    return pd.read_csv(INPUTS / trends.SERIES_FILE, dtype={"date": str})


class TestPinnedSeries:
    """The committed series is the one the article ships; these are its numbers."""

    def test_pull_is_dated_and_covers_every_event_and_the_national_window(self, series):
        assert series["pulled_at"].nunique() == 1
        assert series["pulled_at"].iloc[0].startswith("2026-09-26")
        assert set(series["geo"]) == {"US-TX", "US-NC", "US-FL", "US"}
        for ev in trends.EVENTS:
            window = series[(series["geo"] == ev.geo) & (series["window_start"] == ev.window[0])]
            assert window["date"].min() == ev.window[0]
            assert window["date"].max() == ev.window[1]

    def test_event_figures(self, series):
        t = trends.event_table(series).set_index("event")
        assert t["raw_days_to_baseline"].to_dict() == {
            "Hurricane Beryl": 10,
            "Hurricane Helene": 5,
            "Hurricane Milton": 8,
        }
        assert t["smoothed_days_to_baseline"].to_dict() == {
            "Hurricane Beryl": 18,
            "Hurricane Helene": 19,
            "Hurricane Milton": 13,
        }
        assert t.loc["Hurricane Milton", "smoothed_multiple"] == 14.4
        assert pd.isna(t.loc["Hurricane Beryl", "smoothed_multiple"])  # zero baseline in TX

    def test_national_figures(self, series):
        n = trends.national_table(series).set_index("event")
        assert n["multiple"].to_dict() == {
            "Hurricane Beryl": 2.8,
            "Hurricane Helene": 3.5,
            "Hurricane Milton": 3.2,
        }
        assert n["peak_day"].to_dict() == {
            "Hurricane Beryl": 6,
            "Hurricane Helene": 6,
            "Hurricane Milton": 3,
        }

    def test_helene_and_milton_raw_return_days_match_the_reference(self, series):
        t = trends.event_table(series).set_index("event")["raw_days_to_baseline"]
        for event in ("Hurricane Helene", "Hurricane Milton"):
            assert t[event] == ref.TRENDS_RAW_DAYS_TO_BASELINE[event]
