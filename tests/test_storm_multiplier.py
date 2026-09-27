import io
import zipfile

import pandas as pd
import pytest

import reference as ref
from article_data import storm_multiplier as sm
from article_data.fetch import SOURCES
from conftest import require_sources


def block(rows: list[dict[str, object]]) -> pd.DataFrame:
    base = {"utility_id": 1, "utility": "U", "state": "TX", "ownership": "Cooperative"}
    return pd.DataFrame([{**base, **r} for r in rows])


def test_multiplier_is_with_over_without_and_storm_hours_in_hours():
    result = sm.compute(
        block([{"saidi_with_med": 300.0, "saidi_without_med": 60.0, "customers": 10}])
    )
    row = result.rows.iloc[0]
    assert row["multiplier"] == 5.0
    assert row["storm_hours"] == 4.0


def test_impossible_and_zero_baseline_rows_are_excluded_and_counted_separately():
    result = sm.compute(
        block(
            [
                {
                    "utility_id": 1,
                    "saidi_with_med": 100.0,
                    "saidi_without_med": 50.0,
                    "customers": 1,
                },
                {
                    "utility_id": 2,
                    "saidi_with_med": 40.0,
                    "saidi_without_med": 50.0,
                    "customers": 1,
                },
                {"utility_id": 3, "saidi_with_med": 40.0, "saidi_without_med": 0.0, "customers": 1},
            ]
        )
    )
    assert result.rows["utility_id"].tolist() == [1]
    assert result.impossible == 1
    assert result.zero_baseline == 1


def test_rows_missing_saidi_or_customers_are_dropped_not_counted_as_impossible():
    result = sm.compute(
        block(
            [
                {"saidi_with_med": None, "saidi_without_med": 50.0, "customers": 1},
                {"saidi_with_med": 100.0, "saidi_without_med": None, "customers": 1},
                {"saidi_with_med": 100.0, "saidi_without_med": 50.0, "customers": None},
                {"saidi_with_med": 100.0, "saidi_without_med": 50.0, "customers": 0},
            ]
        )
    )
    assert result.rows.empty
    assert result.impossible == 0


def test_big_utility_summary_uses_the_100k_floor_inclusively():
    rows = sm.compute(
        block(
            [
                {
                    "utility_id": 1,
                    "saidi_with_med": 100.0,
                    "saidi_without_med": 50.0,
                    "customers": 99_999,
                },
                {
                    "utility_id": 2,
                    "saidi_with_med": 300.0,
                    "saidi_without_med": 100.0,
                    "customers": 100_000,
                },
                {
                    "utility_id": 3,
                    "saidi_with_med": 100.0,
                    "saidi_without_med": 100.0,
                    "customers": 5e6,
                },
            ]
        )
    ).rows
    s = sm.summarize(rows)
    assert s["big_utilities"] == 2
    assert s["big_median_multiplier"] == 2.0
    assert s["median_multiplier"] == 2.0


def _sheet_bytes(labels_override: dict[int, str] | None = None) -> io.BytesIO:
    """A minimal Reliability workbook with the real band and label rows."""
    width = sm.EXPECTED_COLUMNS
    band: list[object] = [None] * width
    band[5], band[8] = "All Events (With Major Event Days)", "Without Major Event Days"
    band[17] = "All Events (With Major Event Days)"
    band[width - 1] = "keep the sheet at full width"
    labels: list[object] = [None] * width
    for col, label in sm.COLUMNS.values():
        labels[col] = label
    for col, label in (labels_override or {}).items():
        labels[col] = label
    data: list[object] = [None] * width
    data[1], data[2], data[3], data[4] = 7, "Test Electric", "FL", "Investor Owned"
    data[5], data[8], data[14] = 200.0, 100.0, 12_345
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        pd.DataFrame([[None] * width, band, labels, data]).to_excel(
            w, sheet_name=sm.SHEET, header=False, index=False
        )
    buf.seek(0)
    return buf


def test_ieee_block_columns_are_taken_from_the_verified_positions():
    d = sm.load_ieee_block(_sheet_bytes())
    assert d.iloc[0].to_dict() == {
        "utility_id": 7,
        "utility": "Test Electric",
        "state": "FL",
        "ownership": "Investor Owned",
        "saidi_with_med": 200.0,
        "saidi_without_med": 100.0,
        "customers": 12_345,
    }


def test_a_moved_column_label_is_refused_rather_than_silently_read():
    with pytest.raises(ValueError, match="layout changed"):
        sm.load_ieee_block(_sheet_bytes({14: "Highest Dist. Voltage"}))


@pytest.fixture(scope="module")
def result() -> sm.StormResult:
    require_sources("eia861")
    with zipfile.ZipFile(SOURCES["eia861_2024"].path()) as z:
        return sm.compute(sm.load_ieee_block(io.BytesIO(z.read(sm.MEMBER))))


@pytest.mark.fetched
class TestReproducesPublishedFigures:
    def test_usable_row_count_and_exclusions(self, result: sm.StormResult):
        assert len(result.rows) == ref.STORM_ROWS
        assert result.impossible == ref.STORM_IMPOSSIBLE

    def test_tampa_electric_row(self, result: sm.StormResult):
        tampa = result.rows[result.rows["utility_id"] == ref.TAMPA["utility_id"]]
        assert len(tampa) == 1
        row = tampa.iloc[0]
        assert row["state"] == ref.TAMPA["state"]
        assert row["customers"] == ref.TAMPA["customers"]
        assert row["saidi_without_med"] == ref.TAMPA["saidi_without_med"]
        assert row["saidi_with_med"] == ref.TAMPA["saidi_with_med"]
        assert round(row["multiplier"], 2) == ref.TAMPA["multiplier"]

    def test_medians_and_big_utility_counts(self, result: sm.StormResult):
        s = sm.summarize(result.rows)
        assert round(s["median_multiplier"], 2) == ref.STORM_MEDIAN
        assert s["big_utilities"] == ref.STORM_BIG_N
        assert round(s["big_median_multiplier"], 2) == ref.STORM_BIG_MEDIAN
        assert s["storm_belt_big_utilities"] == ref.STORM_BELT_BIG_N
        assert round(s["storm_belt_big_median_multiplier"], 2) == ref.STORM_BELT_BIG_MEDIAN
