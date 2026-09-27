from pathlib import Path

import pandas as pd
import pytest

import reference as ref
from article_data import eaglei
from article_data.paths import COMPUTED
from conftest import require_computed

SNAPSHOTS = """fips_code,county,state,customers_out,run_start_time
01001,Autauga,Alabama,100,2024-12-30 00:00:00
01001,Autauga,Alabama,100,2024-12-30 00:15:00
01001,Autauga,Alabama,,2024-12-30 00:30:00
01001,Autauga,Alabama,40,2025-01-01 00:00:00
01001,Autauga,Alabama,40,2025-01-06 00:00:00
48201,Harris,Texas,8,2025-02-01 12:00:00
"""


@pytest.fixture
def year_file(tmp_path: Path) -> Path:
    p = tmp_path / "eaglei_outages_2025.csv"
    p.write_text(SNAPSHOTS)
    return p


def test_customer_hours_are_quarter_hours_and_missing_snapshots_are_ignored(year_file: Path):
    cm = eaglei.aggregate_county_month(year_file).set_index(["fips", "year", "month"])
    assert cm.loc[("01001", 2024, 12), "customer_hours"] == 50.0
    assert cm.loc[("01001", 2024, 12), "snapshots"] == 2
    assert cm.loc[("01001", 2025, 1), "customer_hours"] == 20.0
    assert cm.loc[("48201", 2025, 2), "customer_hours"] == 2.0


def test_weeks_are_iso_weeks_so_late_december_joins_week_one(year_file: Path):
    wk = eaglei.aggregate_county_week(year_file).set_index(["fips", "week"])["customer_hours"]
    assert wk.loc[("01001", 1)] == 60.0  # Dec 30 2024 and Jan 1 2025 are both ISO week 1
    assert wk.loc[("01001", 2)] == 10.0  # Jan 6 2025 starts ISO week 2
    assert wk.loc[("48201", 5)] == 2.0


def test_older_archive_column_name_sum_is_accepted(tmp_path: Path):
    p = tmp_path / "eaglei_outages_2015.csv"
    p.write_text(SNAPSHOTS.replace("customers_out", "sum"))
    cm = eaglei.aggregate_county_month(p)
    assert cm["customer_hours"].sum() == 72.0


def test_county_burden_sums_only_the_mature_window():
    cm = pd.DataFrame(
        {
            "fips": ["1", "1", "1"],
            "year": [2016, 2017, 2025],
            "customer_hours": [1e6, 2e6, 3e6],
        }
    )
    burden = eaglei.county_burden(cm)
    assert burden.to_dict("records") == [{"fips": "1", "ch_m": 5.0}]


@pytest.fixture(scope="module")
def month() -> pd.DataFrame:
    return pd.read_csv(COMPUTED / eaglei.NATIONAL_MONTH)


class TestFixturesCarryThePublishedFigures:
    """The committed national aggregates are what the articles quote."""

    def test_yearly_totals(self, month: pd.DataFrame):
        by_year = month.groupby("year")["customer_hours_m"].sum().round(1).to_dict()
        assert by_year == {**ref.EAGLEI_OTHER_YEARS_M, **ref.EAGLEI_YEAR_M}

    def test_second_half_totals(self, month: pd.DataFrame):
        h2 = month[month["month"] >= 7].groupby("year")["customer_hours_m"].sum().round(1)
        assert {y: h2[y] for y in ref.EAGLEI_H2_M} == ref.EAGLEI_H2_M

    def test_2025_worst_weeks(self):
        wk = pd.read_csv(COMPUTED / eaglei.NATIONAL_WEEK_2025).set_index("week")["customer_hours_m"]
        top = wk.sort_values(ascending=False).head(5).round(1)
        assert top.to_dict() == ref.EAGLEI_2025_TOP_WEEKS_M


@pytest.mark.fetched
def test_full_county_month_table_has_the_published_row_count():
    path = require_computed(eaglei.COUNTY_MONTH)
    cm = pd.read_csv(path, dtype={"fips": str})
    assert len(cm) == ref.EAGLEI_COUNTY_MONTH_ROWS
    assert cm["fips"].str.len().eq(5).all()
