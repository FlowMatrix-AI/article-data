import pandas as pd
import pytest

import reference as ref
from article_data import eaglei
from article_data import penetration_gap as pg
from article_data.paths import COMPUTED
from conftest import require_sources


def test_value_buckets_start_at_the_named_threshold():
    assert pg.value_buckets_from(175_000)[0] == "B25075_E018"
    assert pg.value_buckets_from(300_000)[0] == "B25075_E021"
    assert pg.value_buckets_from(300_000)[-1] == "B25075_E027"
    assert len(pg.value_buckets_from(175_000)) == 10


def test_qualifying_homes_scale_units_over_threshold_by_detached_share():
    value = pd.DataFrame({b: [10.0, 10.0] for b in pg.VALUE_BUCKETS}, index=["1", "2"])
    tenure = pd.DataFrame(
        {pg.OWNER_TOTAL: [100.0, 0.0], pg.OWNER_DETACHED: [75.0, 0.0]}, index=["1", "2"]
    )
    names = pd.Series(["One", "Two"], index=["1", "2"])
    out = pg.qualifying_homes(value, tenure, names, threshold=300_000)
    assert out.to_dict("records") == [
        {"fips": "1", "name": "One", "qualifying": 52},  # 7 buckets x 10 x 0.75 = 52.5 -> 52
        {"fips": "2", "name": "Two", "qualifying": 0},  # no owner-occupied units: share 0
    ]


def test_gap_keeps_counties_at_or_above_the_cutoff_then_ranks_by_qualifying_homes():
    acs = pd.DataFrame({"fips": list("abc"), "name": list("ABC"), "qualifying": [8, 9, 100]})
    burden = pd.DataFrame({"fips": list("abc"), "ch_m": [10.0, 8.0, 1.0]})
    top, cutoff = pg.penetration_gap(acs, burden, quantile=0.5, top_n=5)
    assert cutoff == 8.0
    # b sits exactly on the cutoff and stays; c has the most homes but is below it
    assert top["fips"].tolist() == ["b", "a"]


@pytest.fixture(scope="module")
def burden() -> pd.DataFrame:
    return pd.read_csv(COMPUTED / eaglei.COUNTY_BURDEN, dtype={"fips": str})


@pytest.fixture(scope="module")
def acs() -> pd.DataFrame:
    require_sources("acs")
    return pg.load_acs()


@pytest.mark.fetched
class TestReproducesPublishedFigures:
    def test_county_count_and_national_total(self, acs: pd.DataFrame):
        assert len(acs) == ref.ACS_COUNTIES
        assert round(acs["qualifying"].sum() / 1e6, 1) == ref.ACS_TOTAL_M

    def test_top25_table(self, acs: pd.DataFrame, burden: pd.DataFrame):
        top, cutoff = pg.penetration_gap(acs, burden)
        assert round(cutoff, 1) == ref.GAP_CUTOFF_M
        assert top["fips"].tolist() == ref.GAP_TOP25_FIPS
        la = top.iloc[0]
        assert la["fips"] == ref.GAP_LOS_ANGELES["fips"]
        assert la["qualifying"] == ref.GAP_LOS_ANGELES["qualifying"]
        assert la["ch_m"] == ref.GAP_LOS_ANGELES["ch_m"]

    def test_documented_175k_threshold_does_not_give_the_published_total(self):
        """The earlier write-up said $175k; its numbers are $300k. Keep that visible."""
        require_sources("acs")
        acs = pg.load_acs(threshold=175_000)
        assert round(acs["qualifying"].sum() / 1e6, 1) == 50.9
