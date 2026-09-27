# AGENTS.md

**THIS REPOSITORY IS PUBLIC.** Every file, commit message, branch name, issue,
pull request and review comment in it is visible to anyone on the internet, and
the methods page on flowmatrixai.com links here. Read this section before doing
anything else.

## Hard rules for a public repo

The test for anything you are about to add: **if it would not be fine on the
front page of the site, it does not belong here.** Concretely:

1. **Never name or link a private repository.** Not in code, comments,
   docstrings, commit messages, issues or PR bodies. "Moved from the internal
   research repo" is fine; the repo's name and URL are not. If a private repo
   is the origin of a figure, describe the public source the figure was
   computed from instead.
2. **Never reference internal tooling, portals, infrastructure or operations.**
   No internal hostnames, dashboards, deploy targets, CRM or ticketing systems,
   session or workflow identifiers, or filesystem paths from a particular
   machine. The only hosts that may appear are the public data sources and
   flowmatrixai.com.
3. **Never name a client, a prospect, or an individual.** Utilities, agencies
   and counties appear here as rows in public datasets and may be named as
   such. A commercial relationship with anyone is never disclosed. No personal
   names paired with a title or employer, no email addresses, no phone numbers,
   no personal profile URLs. The one exception is the maintainer's own GitHub
   handle in `CODEOWNERS`.
4. **Never include commercial terms, pricing, revenue, pipeline, funnel figures
   or internal strategy.** This repo explains how published numbers were
   computed, nothing about how the business runs.
5. **Every dataset comes from a public source with its URL recorded.** A raw
   input is added by registering it in `src/article_data/fetch.py` with its
   URL, SHA-256 and licence; a pinned input under `outputs/inputs/` records
   where and when it was pulled. Nothing arrives by hand-copy from a private
   file. If a source is not public, the analysis that needs it does not go
   here.
6. **No credentials, and no pointers to where a credential is stored.** The
   pipeline needs no API key by design (ACS is read from the keyless summary
   files); keep it that way rather than adding a keyed endpoint.
7. **Commit messages, branch names and issues are public too.** Write them as
   if they were part of the README. No internal ticket references, no client
8. **Commit with the work email, never a personal one.** Author and committer on this repository are `name@flowmatrixai.com`. Git identity is published in every commit and cannot be corrected after the fact without rewriting history that others have already cloned. Set it per-repository (`git config user.email`) rather than relying on a global default, and check `git log --format='%an <%ae>'` before the first push.
   or project codenames, no "per the call with X".

When in doubt, leave it out and ask. A leak here is permanent: history is
public and a force-push does not remove what has already been cloned.

## Project

The data and code behind the articles on flowmatrixai.com. Every published
figure is produced from a public source that is fetched by recorded URL,
verified against a recorded SHA-256, and reduced by code in this repository.
The computed outputs and the article exhibits are committed so a reader can
check a number without running anything.

## Commands

```bash
just setup                    # uv sync --frozen
just check                    # ruff format --check, ruff check, pyright (what CI runs)
just test                     # pytest; reproduction tests skip until sources are fetched
just fetch-sources eia861 acs # verified downloads of the small sources into outputs/raw/
just pipeline --stream        # every analysis; streams the 11.6 GB EAGLE-I archive year by year
just exhibits                 # redraw the article SVGs from the committed CSVs
```

## Layout

```
pyproject.toml, uv.lock       project + locked environment (Python 3.12, uv)
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
  raw/                        fetched sources (gitignored, restored by `article-data fetch`)
  inputs/                     pinned inputs that cannot be re-fetched byte-for-byte; brand tokens; fonts
  computed/                   outputs; small ones committed as fixtures
  exhibits/                   the article SVGs, committed and regenerated by the tests
```

## Rules specific to the pipeline

- **Do not commit anything under `outputs/raw/`.** Raw sources are fetched by
  script and verified by checksum; committed outputs are small aggregates only.
- **Do not hand-edit a committed CSV under `outputs/computed/`.** Regenerate
  it. If a number changes, change `tests/reference.py` and the article in the
  same PR, with the reason in the PR body.
- **Do not hand-edit an SVG under `outputs/exhibits/`.** The tests regenerate
  every exhibit and assert it is byte-identical to the committed file. Change
  the drawing code, run `just exhibits`, commit the result.
- **Do not change `HASH_SALT` in `exhibits/figstyle.py`.** It seeds
  matplotlib's element ids; changing it rewrites every committed SVG for no
  visible gain.
- **Do not re-pull the Google Trends series casually.** The pinned series under
  `outputs/inputs/` is the published one; a re-pull is a re-baseline of the
  shipped numbers, done deliberately with the tests and the article updated
  together.
- **Do not switch the ACS step to the Census API.** The API redirects to an
  HTML page with HTTP 200 when the key is missing, so a naive fetch looks like
  it worked. The pipeline reads the keyless table-based summary files for that
  reason, and it keeps this repo free of any credential.
- **A checksum mismatch is an error, not a warning.** If an upstream file
  changes, record the new SHA-256 in the same PR that re-verifies the figures
  against it; never loosen the check.
- **Licences travel with the data.** EAGLE-I is CC BY 4.0, which is why the
  committed outputs carry attribution and are released under `LICENSE-DATA`.
  A new source's licence is recorded in `fetch.py` and, if it constrains
  redistribution, in `outputs/METHODS.md` and the README.

## Conventions

- Conventional Commits (`type(scope): description`), one logical change per
  commit, no AI attribution trailers.
- `just check && just test` before every commit; CI runs the same gates plus
  a secret scan, and `ok` must be green to merge.
- Squash merge; delete the head branch on merge.
