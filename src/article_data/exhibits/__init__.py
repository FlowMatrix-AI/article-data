"""The article exhibits: brand-styled SVGs drawn from the committed CSVs.

Every value on a chart is read from a file under ``outputs/computed/`` (or
the pinned series under ``inputs/``); nothing is typed into a script. Output is
deterministic, so the committed SVGs are fixtures the tests regenerate and compare.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from article_data.exhibits import figstyle, gap, storm, window
from article_data.paths import COMPUTED, EXHIBITS, INPUTS

Renderer = Callable[[Path, Path, Path, figstyle.Palette], None]

EXHIBITS_BY_FILE: dict[str, Renderer] = {
    "ex2-storm-multiplier.svg": lambda i, c, o, p: storm.ex2_storm_multiplier(c, o, p),
    "ex4-saidi-dumbbell.svg": lambda i, c, o, p: storm.ex4_saidi_dumbbell(c, o, p),
    "ex10-state-league.svg": lambda i, c, o, p: storm.ex10_state_league(c, o, p),
    "ex5-decay-curves.svg": window.ex5_decay_curves,
    "ex13-gap-counties.svg": lambda i, c, o, p: gap.ex13_gap_counties(c, o, p),
}


def render(
    names: list[str] | None = None,
    *,
    inputs_dir: Path = INPUTS,
    computed_dir: Path = COMPUTED,
    out_dir: Path = EXHIBITS,
) -> list[Path]:
    """Draw the named exhibits (default: all), one file per page theme, and return
    the files written."""
    for name in names or ():
        if name not in EXHIBITS_BY_FILE:
            raise KeyError(f"no exhibit {name!r}; known: {sorted(EXHIBITS_BY_FILE)}")
    written = []
    for theme in figstyle.THEMES:
        pal = figstyle.palette(theme, inputs_dir)
        figstyle.apply(pal, inputs_dir)
        for name in names or list(EXHIBITS_BY_FILE):
            out = out_dir / figstyle.variant_name(name, theme)
            EXHIBITS_BY_FILE[name](inputs_dir, computed_dir, out, pal)
            written.append(out)
    return written
