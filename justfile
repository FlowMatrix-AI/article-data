# `just --list` shows recipes. The Python project is managed by uv (uv.lock is committed).

# install dependencies from the lock
setup:
    uv sync --frozen

# format (write)
fmt:
    uv run ruff format .
    uv run ruff check --fix .

# lint
lint:
    uv run ruff check .

# fmt-check + lint + typecheck (CI equivalent)
check:
    uv run ruff format --check .
    uv run ruff check .
    uv run pyright

# run tests
test:
    uv run pytest

# download and verify the raw sources into outputs/raw/ (all groups, or e.g. `just fetch-sources eia861 acs`)
fetch-sources *groups:
    uv run article-data fetch {{groups}}

# run every analysis from fetched sources, then redraw the exhibits
pipeline *args:
    uv run article-data all {{args}}

# redraw the article SVGs from the committed CSVs
exhibits:
    uv run article-data exhibits
