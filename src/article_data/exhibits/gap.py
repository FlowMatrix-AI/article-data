"""Penetration-gap exhibit, ``ex13-gap-counties.svg``, from ``computed/penetration-gap-top25.csv``.

Qualifying homes against nine-year outage burden for the 25 published counties.
Counties beyond 60 M customer-hours or 600,000 homes are labelled; the article's
table carries every value.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from matplotlib.ticker import FuncFormatter

from article_data.exhibits import figstyle as fs

CSV = "penetration-gap-top25.csv"
SOURCE = "ACS 2023 5-year (B25075, B25032) × EAGLE-I 2017–2025 · FlowMatrix Research"
LABEL_BURDEN_M = 60
LABEL_HOMES = 600_000
STATE_ABBR = {
    "Arizona": "AZ",
    "California": "CA",
    "Florida": "FL",
    "Illinois": "IL",
    "Massachusetts": "MA",
    "Minnesota": "MN",
    "Nevada": "NV",
    "New York": "NY",
    "Texas": "TX",
    "Utah": "UT",
    "Washington": "WA",
}
# Label anchor per county (text offset in points, alignment) to keep labels clear
# of neighbouring dots; Dallas and Broward sit on top of each other.
OFFSETS = {
    "Harris": (10, 0, "left", "center"),
    "Los Angeles": (-12, 0, "right", "center"),
    "Miami-Dade": (10, 0, "left", "center"),
    "King": (10, 0, "left", "center"),
    "Dallas": (-10, -6, "right", "center"),
    "Broward": (10, 8, "left", "center"),
    "Maricopa": (0, 12, "center", "bottom"),
}


def short_name(name: str) -> tuple[str, str]:
    county, state = name.split(", ")
    return county.removesuffix(" County"), STATE_ABBR[state]


def ex13_gap_counties(computed: Path, out: Path, pal: fs.Palette) -> None:
    top = pd.read_csv(computed / CSV, dtype={"fips": str})
    fig = fs.figure(5.6)
    fig.subplots_adjust(left=0.11, right=0.97, top=0.88, bottom=0.19)
    ax = fig.add_subplot()
    ax.plot(top["qualifying"], top["ch_m"], "o", color=pal.accent, ms=10, mew=0)
    for row in top.to_dict("records"):
        homes, burden = int(row["qualifying"]), float(row["ch_m"])
        if burden < LABEL_BURDEN_M and homes < LABEL_HOMES:
            continue
        county, state = short_name(str(row["name"]))
        dx, dy, ha, va = OFFSETS[county]
        ax.annotate(
            f"{county}, {state}",
            (homes, burden),
            xytext=(dx, dy),
            textcoords="offset points",
            ha=ha,
            va=va,
        )
    ax.set_xlim(0, 1_300_000)
    ax.set_ylim(0, 260)
    ax.set_xticks([0, 250_000, 500_000, 750_000, 1_000_000, 1_250_000])
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x / 1000:,.0f}k"))
    ax.set_yticks([0, 50, 100, 150, 200, 250])
    ax.grid(axis="y")
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("Qualifying homes (owner-occupied, detached, $300,000+)", labelpad=8)
    ax.set_ylabel("Outage burden 2017–2025, million customer-hours")
    fs.title(fig, f"The {len(top)} gap counties: homes that qualify, hours in the dark")
    fs.source_line(fig, SOURCE)
    fs.save(fig, out)
