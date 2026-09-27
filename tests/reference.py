"""The figures the articles publish, used as reproduction targets.

Each is dated to the working note it was first recorded in. Where a figure below
was derived from a committed CSV rather than quoted directly, the derivation is
noted. These are what the articles say; the tests check that this pipeline says
the same, or the PR explains why not.
"""

# Storm multiplier (EIA-861 2024). Recorded 2026-09-10.
STORM_ROWS = 723
STORM_IMPOSSIBLE = 1
STORM_MEDIAN = 1.72
STORM_BIG_N = 163
STORM_BIG_MEDIAN = 1.89
STORM_BELT_BIG_N = 48
STORM_BELT_BIG_MEDIAN = 2.01
TAMPA = {
    "utility_id": 18454,
    "state": "FL",
    "customers": 869_995,
    "saidi_without_med": 70.14,
    "saidi_with_med": 4239.69,
    "multiplier": 60.45,
}

# EAGLE-I decade aggregate. Recorded 2026-09-10.
EAGLEI_COUNTY_MONTH_ROWS = 365_352
EAGLEI_YEAR_M = {2024: 1891.7, 2025: 892.7}
EAGLEI_H2_M = {2024: 1317.8, 2025: 325.2}
EAGLEI_2025_TOP_WEEKS_M = {2: 56.7, 14: 47.3, 51: 41.9, 18: 41.3, 20: 41.1}
# Derived from computed/eaglei-county-month.csv: 2014-2023 yearly totals, millions.
EAGLEI_OTHER_YEARS_M = {
    2014: 61.3,
    2015: 391.3,
    2016: 516.1,
    2017: 1094.6,
    2018: 824.0,
    2019: 706.1,
    2020: 1304.8,
    2021: 1331.3,
    2022: 1243.0,
    2023: 1059.2,
}

# Penetration gap. Recorded 2026-09-15, plus computed/penetration-gap-top25.csv.
ACS_COUNTIES = 3222
ACS_TOTAL_M = 33.7
GAP_CUTOFF_M = 2.6  # derived: top-quartile cutoff of ch_m over the 3,101 matched counties
GAP_TOP25_FIPS = [  # from computed/penetration-gap-top25.csv, in order
    "06037", "04013", "06073", "06059", "17031", "53033", "06065", "36103", "48201", "32003",
    "36059", "06071", "25017", "06085", "06067", "12086", "06001", "06013", "48439", "48453",
    "48085", "49035", "48113", "12011", "27053",
]  # fmt: skip
GAP_LOS_ANGELES = {"fips": "06037", "qualifying": 1_180_328, "ch_m": 155.8}

# Seven-day window. Recorded 2026-09-10, plus computed/seven-day-window.csv.
TRENDS_RAW_DAYS_TO_BASELINE = {"Hurricane Helene": 5, "Hurricane Milton": 8, "Hurricane Beryl": 13}
TRENDS_SMOOTHED = {  # baseline7, peak7, multiple, peak_day, days_back
    "Hurricane Beryl": (1.714, 63.571, 37.1, 6, 19),
    "Hurricane Helene": (0.0, 42.714, None, 6, 20),
    "Hurricane Milton": (4.214, 69.571, 16.5, 4, 12),
}
TRENDS_NATIONAL_MULTIPLE_RANGE = (3.1, 3.7)
TRENDS_NATIONAL_PEAK_DAY_RANGE = (1, 6)
