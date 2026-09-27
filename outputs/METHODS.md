# Methods

One section per analysis: where the data comes from, under what licence, what the
code does with it, and what it cannot tell you. The articles cite this file. The
commands are in [`../README.md`](../README.md); the source URLs and checksums are
recorded in `src/article_data/fetch.py`.

## Storm multiplier (EIA-861, 2024)

**Source.** US Energy Information Administration, Form EIA-861 Annual Electric
Power Industry Report, 2024 final release: `f8612024.zip`, file
`Reliability_2024.xlsx`, sheet `Reliability_States`. Public domain (US federal
government work). Fetched from `https://www.eia.gov/electricity/data/eia861/zip/f8612024.zip`.

**Method.** Only the IEEE-1366 block is used, so every utility is measured the same
way. The unit is the utility-state row as EIA reports it. For each row:

    multiplier  = SAIDI with major event days / SAIDI without major event days
    storm_hours = (SAIDI with MED - SAIDI without MED) / 60

Rows missing either SAIDI value or the customer count are dropped. A row whose
"without" SAIDI exceeds its "with" SAIDI is impossible by construction and is
excluded and counted (1 in 2024). A row with a zero "without" SAIDI has no
defined multiplier and is excluded and counted (2 in 2024). "Big" utilities are
those at or above 100,000 customers; the storm belt is TX, LA, MS, AL, FL, GA, SC,
NC, VA. Output: `computed/storm-multiplier-2024.csv`, 723 rows.

**Known limits.** SAIDI is self-reported and EIA does not audit it. The
multiplier reflects 2024 storm exposure and restoration performance together, not
utility quality alone: the 2024 table is Beryl, Helene and Milton. A utility that
reports under the IEEE standard in one state and "Other" in another appears only
for the IEEE state. The loader refuses to run if the sheet's column labels move.

## EAGLE-I outage aggregates (2014-2025)

**Source.** Oak Ridge National Laboratory, "The Environment for Analysis of
Geo-Located Energy Information's Recorded Electricity Outages 2014-2025", figshare
article 24237376, version 4 (doi:10.6084/m9.figshare.24237376.v4). One CSV per
year, 11.6 GB in total. Licence CC BY 4.0: cite ORNL/EAGLE-I when publishing.
Fetched from `https://ndownloader.figshare.com/files/<id>` with the per-file ids,
figshare MD5s and our SHA-256s recorded in `fetch.py`.

**Method.** Each row is a 15-minute snapshot of customers without power in one
county, so customer-hours are `sum(customers_out) * 0.25`. Years are read in
2-million-row chunks and reduced to county-month (`fips, county, state, year,
month, customer_hours, snapshots`) and, for 2025, county-ISO-week. Rows with a
missing customer count are ignored. Three committed aggregates carry the
published figures: `eaglei-national-month.csv` (year-month totals),
`eaglei-2025-national-week.csv` (ISO week totals), and
`eaglei-county-burden-2017-2025.csv` (per-county customer-hours over the mature
window, feeding the penetration gap). The full county-month table is regenerated
and not committed.

**Known limits.** Coverage ramps up through 2014-2016; the archive's own
`coverage_history.csv` documents which utilities report when. Claims about
"mature coverage" use 2017 onward. A snapshot records customers out at that
instant, so a gap in a utility's feed reads as zero outage, and customer-hours
undercount rather than overcount. ISO week 1 of 2025 starts on 30 December 2024,
so the 2025 file's first week is partial. County names and FIPS codes are as the
archive reports them.

## Penetration gap (ACS 2023 5-year x EAGLE-I)

**Source.** US Census Bureau, American Community Survey 2023 5-year estimates,
tables B25075 (Value, owner-occupied units) and B25032 (Tenure by units in
structure), from the table-based summary files under
`https://www2.census.gov/programs-surveys/acs/summary_file/2023/table-based-SF/`
(the same estimates the Census Data API serves, without the API key it now
requires). County names from the accompanying `Geos20235YR.txt`. Public domain.
Outage exposure from the EAGLE-I aggregate above.

**Method.** For each county (summary level 050):

    qualifying = sum(B25075 buckets at or above the value threshold)
                 * (B25032_003 owner-occupied 1-detached / B25032_002 owner-occupied total)

rounded to whole homes; a county with no owner-occupied units gets zero. Counties
are matched to EAGLE-I on the 5-digit FIPS; the top quartile of 2017-2025
customer-hours is kept and ranked by qualifying homes; the first 25 are the
published table. Outputs: `computed/acs-qualifying-homes.csv` (3,222 counties)
and `computed/penetration-gap-top25.csv`.

**Threshold.** The published table and the ~33.7M national total use a
**$300,000** threshold (B25075 buckets 021-027). The earlier write-up of this
analysis described the threshold as $175,000 (buckets 018-027); that definition
gives 50.9M homes and a different top 25, and is not what was published. The
threshold is a parameter (`penetration_gap.load_acs(threshold=...)`) so either
can be produced; the default is the published one. Which threshold the articles
should use is an editorial decision, not a code one.

**Known limits.** Home value and structure type are a proxy for standby-generator
eligibility, narrower than any manufacturer's own market definition (no income,
lot, fuel or permitting criteria). ACS 5-year estimates carry margins of error
that are large in small counties. 121 counties in the ACS table have no EAGLE-I
match and drop out of the ranking. Exposure is customer-hours, which scales with
county size; the ranking is therefore of large exposed counties, not of the most
outage-prone ones.

## Seven-day window (Google Trends, 2024 hurricanes)

**Source.** Google Trends, daily search interest for "whole house generator":
Texas (Beryl, landfall 2024-07-08), North Carolina (Helene, 2024-09-26), Florida
(Milton, 2024-10-09), and the United States for 2024-05-15 to 2024-12-15. Pulled
through the unofficial endpoint (trendspy) on 2026-09-26 and pinned in
`inputs/trends-whole-house-generator-2024.csv`. Google's terms allow reporting
Trends data with attribution; the values are Google's relative indices, not ours.

**Method.** Per event, on the state series: baseline is the median of the 21 days
ending 3 days before landfall; peak is the maximum in the 45 days from landfall;
"days to baseline" is the first day, counted from the peak day onward, at or below
125% of baseline. The same measures are computed on a trailing 7-day mean, which
tames the zero-heavy daily state series; the multiple (peak over baseline) is
reported from the smoothed series. National multiples compare each event's peak
in the smoothed US series with that series' June 2024 median. Outputs:
`computed/seven-day-window.csv`, `computed/seven-day-window-national.csv`.

**Known limits.** Trends values are scaled 0-100 within each pull and rounded, so
a pull on another day can differ by a few points and the baselines here are small
integers; a zero baseline (Texas, North Carolina) leaves the multiple undefined
rather than infinite. The numbers are ratios and day counts of search interest,
never search volumes or sales. A refreshed pull is a new baseline, not a
correction, and the article should say when the series was pulled.

## Exhibits (the article charts)

**Source.** The committed aggregates above and the pinned Trends series; no value
is typed into a chart script. Colours are pinned from the site's brand token package in
`inputs/brand-tokens.json` (the version is recorded in the file); the brand's
oklch() tokens are resolved to hex in `exhibits/figstyle.py`. The typeface is
the brand's Inter, vendored in `inputs/fonts/` as static instances (400, 600,
700) of the `@fontsource-variable/inter` latin subset the site serves, under
the SIL Open Font License alongside.

**Method.** `article-data exhibits` draws five SVGs into `exhibits/`:

| File | Reads | Shows |
| --- | --- | --- |
| `ex2-storm-multiplier.svg` | `storm-multiplier-2024.csv` | every utility at 100,000+ customers ranked by multiplier (163), the seven in the article's table highlighted, the top four and the median (1.9×) labelled |
| `ex4-saidi-dumbbell.svg` | `storm-multiplier-2024.csv` | SAIDI without and with major event days for the seven table utilities, each with its multiplier |
| `ex10-state-league.svg` | `storm-multiplier-2024.csv` | median multiplier of big utilities per state, states with three or more; storm-belt states highlighted; the all-big-utility median as a reference line |
| `ex5-decay-curves.svg` | `inputs/trends-…csv`, `seven-day-window.csv` | daily search interest by days from landfall, one panel per storm, with the raw days-to-baseline (Beryl 10, Helene 5, Milton 8) marked |
| `ex13-gap-counties.svg` | `penetration-gap-top25.csv` | qualifying homes against 2017-2025 outage burden for the 25 published counties, the seven largest on either axis labelled |

The site loads the exhibits through `<img>`, which reaches neither the page's
webfonts nor its CSS variables, so each file carries everything itself: text is
exported as Inter glyph outlines and nothing is painted behind the plot. Each
exhibit is written twice, `<name>.svg` for the light canvas and `<name>-dark.svg`
for the dark one, and the site picks the variant by theme, unfiltered. Each
variant's ink and accent are that theme's own brand tokens (`text.secondary`
and `accent.base`, both above 4.5:1 on their canvas); its de-emphasis grey is
solved to sit at the 3:1 non-text floor against that canvas. The two variants
differ only in those colours. `tests/test_exhibits.py` measures the ratios,
asserts the colour-only difference, and regenerates every file and asserts it
is byte-identical to the committed one; output is deterministic (no date, no
tool version, fixed hash salt, glyphs from the vendored fonts only).

**Known limits.** The decay chart draws day counts only: the daily series has a
pre-landfall baseline of zero in all three states, so a peak-over-baseline
multiple is undefined there. The state league table is honest about the storm
belt: FL, NC, SC and LA sit above the all-big-utility median, GA, VA and TX below
it. No county map is drawn, because the EIA-861 Service Territory join is not in
this pipeline. Glyph outlines are not selectable text, so the article's figure
caption carries the words; and a variant only reads on the canvas it was made
for, so a page that shows the light file on the dark theme (or the reverse) has
the wrong file, not a chart that needs a filter.
