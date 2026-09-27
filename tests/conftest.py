from pathlib import Path

import pytest

from article_data import fetch
from article_data.paths import COMPUTED

HERE = Path(__file__).resolve().parent


def require_sources(group: str) -> None:
    """Skip when a raw group has not been fetched; ``article-data fetch <group>`` restores it."""
    missing = [s.name for s in fetch.resolve([group]) if not s.path().exists()]
    if missing:
        pytest.skip(f"raw sources not fetched: {missing} (run `article-data fetch {group}`)")


def require_computed(name: str) -> Path:
    path = COMPUTED / name
    if not path.exists():
        pytest.skip(f"{path.name} not generated (gitignored output; run the pipeline)")
    return path
