# article-data

The data and code behind the articles on [flowmatrixai.com](https://flowmatrixai.com/articles/).

Every published figure is produced from a public source that is fetched by
recorded URL, verified against a recorded SHA-256, and reduced by code in this
repository. The computed outputs and the article exhibits are committed, so a
number can be checked without running anything; the per-analysis source,
licence, method and known limits are in [`outputs/METHODS.md`](outputs/METHODS.md).

**This repository is public.** Nothing in it names a client, a private
repository, internal tooling or a person, and every dataset it uses is public
with its URL recorded. The full rules are in [`AGENTS.md`](AGENTS.md); the test
is whether something would be fine on the front page of the site.

## Licensing

| What | Licence | File |
| --- | --- | --- |
| Code: `src/`, `tests/`, `pyproject.toml`, `justfile`, CI | [MIT](LICENSE) | `LICENSE` |
| Committed outputs: `outputs/computed/`, `outputs/exhibits/`, `outputs/METHODS.md` | [CC BY 4.0](LICENSE-DATA) | `LICENSE-DATA` |
| Fonts: `outputs/inputs/fonts/` (Inter) | SIL Open Font License 1.1 | `outputs/inputs/fonts/OFL.txt` |

The outputs are derived from the sources below. Reuse of the computed data or
the exhibits should credit "FlowMatrix AI, article-data" and the upstream
source of the analysis in question:

| Source | Used for | Licence |
| --- | --- | --- |
| Oak Ridge National Laboratory, EAGLE-I recorded electricity outages 2014-2025 (figshare 24237376 v4, [doi:10.6084/m9.figshare.24237376.v4](https://doi.org/10.6084/m9.figshare.24237376.v4)) | outage aggregates, penetration gap | CC BY 4.0. Derived outputs must carry attribution to ORNL/EAGLE-I, which is why they are released under CC BY 4.0 here. |
| US Energy Information Administration, Form EIA-861 2024 ([eia.gov](https://www.eia.gov/electricity/data/eia861/)) | storm multiplier | Public domain (US federal government work) |
| US Census Bureau, ACS 2023 5-year table-based summary files ([census.gov](https://www2.census.gov/programs-surveys/acs/summary_file/2023/table-based-SF/)) | penetration gap | Public domain (US federal government work) |
| Google Trends, daily relative interest for "whole house generator", pulled 2026-09-26 | five-to-ten-day window | Reported with attribution per Google's terms; the values are Google's relative indices |
| The site's brand tokens, pinned in `outputs/inputs/brand-tokens.json` from the public npm package `@flowmatrix-ai/brand` 3.8.0 | exhibit colours | Pinned values only; see the file |

## Run it end to end

The project is managed by [uv](https://docs.astral.sh/uv/) with a committed
`uv.lock`; the `justfile` wraps the same commands.

```sh
uv sync --frozen                        # create .venv from the lock
uv run article-data fetch eia861 acs    # ~275 MB, verified against recorded checksums
uv run article-data storm-multiplier    # EIA-861: writes outputs/computed/storm-multiplier-2024.csv
uv run article-data eaglei --stream     # EAGLE-I: fetches 11.6 GB one year at a time (~45 min)
uv run article-data penetration-gap     # ACS x EAGLE-I: needs the eaglei step's county burden
uv run article-data trends              # Google Trends: recomputes from the pinned series
uv run article-data exhibits            # the article SVGs, from the committed aggregates
```

`uv run article-data all --stream` runs the four analyses in that order, then
the exhibits. `fetch` with no arguments downloads every source, including the
full EAGLE-I archive, to `outputs/raw/` (gitignored); `--stream` on `eaglei`
deletes each year after it is aggregated so at most one ~1.4 GB file is on disk.

Outputs land in `outputs/computed/`. The small ones are committed and double as
test fixtures; `eaglei-county-month.csv` (16 MB) and `eaglei-2025-county-week.csv`
(5 MB) are regenerated and gitignored.

## Google Trends

Trends is a live, unofficial endpoint whose values are relative indices that can
shift between pulls, so the series the articles use is pinned in
`outputs/inputs/trends-whole-house-generator-2024.csv` with a `pulled_at`
column. `uv run article-data trends --pull` refreshes that file through
[trendspy](https://pypi.org/project/trendspy/) (pytrends has been archived since
April 2025). Re-pulling changes the shipped numbers; treat it as a deliberate
re-baseline and update the tests and the article together.

## Checks and tests

```sh
just check    # ruff format --check, ruff check, pyright
just test     # pytest
```

Tests come in three kinds:

- unit tests on small synthetic inputs, which always run;
- reproduction tests marked `fetched`, which run against the real EIA-861 and
  ACS files and skip with a message if `article-data fetch eia861 acs` has not
  been run;
- fixture tests, which assert the published figures against the committed
  aggregates in `outputs/computed/` and regenerate every exhibit, asserting it
  is byte-identical to the committed SVG.

The published figures they assert are collected in `tests/reference.py`. CI
runs the same gates on every pull request, fetches the small sources so the
reproduction tests run, and scans for secrets; the `ok` check aggregates them.

## Layout

```
pyproject.toml, uv.lock       project + locked environment (Python 3.12)
src/article_data/
  fetch.py                    source registry (URL, SHA-256, licence) and downloader
  storm_multiplier.py         EIA-861 SAIDI with / without major event days
  eaglei.py                   EAGLE-I county-month and 2025 county-week aggregates
  penetration_gap.py          ACS qualifying homes x EAGLE-I exposure
  trends.py                   Google Trends decay after the 2024 hurricanes
  exhibits/                   the article SVGs; figstyle.py holds brand tokens and determinism
  cli.py                      the `article-data` command
tests/                        pytest suite; reference.py holds the published figures
outputs/
  METHODS.md                  per-analysis source, licence, method, known limits
  raw/                        fetched sources (gitignored)
  inputs/                     pinned inputs that cannot be re-fetched byte-for-byte; brand tokens; fonts
  computed/                   outputs; small ones committed as fixtures
  exhibits/                   the article SVGs, committed and regenerated by the tests
```

## Contributing

[`AGENTS.md`](AGENTS.md) carries the rules: what may never appear in a public
repository, and how the pipeline's committed outputs are kept honest. A change
to a published number changes `tests/reference.py` and the article in the same
pull request, with the reason.
