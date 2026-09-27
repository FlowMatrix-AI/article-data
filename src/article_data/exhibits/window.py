"""Search-interest decay after landfall, ``ex5-decay-curves.svg``.

Daily Google Trends interest for "whole house generator" in the hardest-hit state,
from the pinned series in ``inputs/``, one panel per 2024 hurricane, with the day
the index returned to its pre-landfall baseline from ``computed/seven-day-window.csv``.

Only day counts are drawn. The pre-landfall baseline of the daily series is zero
in all three states, so a peak-over-baseline multiple is undefined there and none
is shown; the smoothed multiple that exists for Florida lives in the CSV and the
article's table, not in this chart.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from article_data import trends
from article_data.exhibits import figstyle as fs

CSV = "seven-day-window.csv"
SOURCE = "FlowMatrix Research"
DAYS_BEFORE = 14
DAYS_AFTER = 21


def ex5_decay_curves(inputs: Path, computed: Path, out: Path, pal: fs.Palette) -> None:
    series = pd.read_csv(inputs / trends.SERIES_FILE, dtype={"date": str})
    window = pd.read_csv(computed / CSV).set_index("event").to_dict("index")
    pulled = series["pulled_at"].iloc[0][:10]

    fig = fs.figure(7.2)
    fig.subplots_adjust(left=0.10, right=0.97, top=0.885, bottom=0.15, hspace=0.55)
    axes = fig.subplots(len(trends.EVENTS), 1, sharex=True)
    for ax, ev in zip(axes, trends.EVENTS, strict=True):
        s = trends.event_series(series, ev.geo, ev.window)
        land = pd.Timestamp(ev.landfall)
        days = np.asarray((pd.DatetimeIndex(s.index) - land).days)
        keep = (days >= -DAYS_BEFORE) & (days <= DAYS_AFTER)
        row = window[ev.name]
        back = int(row["raw_days_to_baseline"])
        baseline = float(row["raw_baseline"])

        ax.bar(days[keep], s[keep], width=0.8, color=pal.accent, linewidth=0)
        ax.axvline(0, color=pal.ink, lw=1, ls=(0, (3, 3)))
        ax.plot([back, back], [0, 60], color=pal.ink, lw=1.5)
        ax.text(back + 0.8, 74, f"Day {back}:\nback to baseline", va="center", ha="left")
        ax.set_ylim(0, 105)
        ax.set_yticks([0, 50, 100])
        ax.set_xlim(-DAYS_BEFORE - 0.6, DAYS_AFTER + 0.6)
        ax.grid(axis="y")
        ax.set_axisbelow(True)
        ax.spines["left"].set_visible(False)
        ax.tick_params(axis="y", length=0)
        state = ev.geo.removeprefix("US-")
        ax.set_title(
            f"{ev.name.removeprefix('Hurricane ')} · {state} · landfall {ev.landfall}"
            f" · baseline {baseline:.0f}",
            fontsize=fs.FONT_SIZE,
            fontweight="600",
            pad=8,
        )
    axes[0].text(-0.6, 100, "Landfall", ha="right", va="top")
    axes[-1].set_xticks([-14, -7, 0, 7, 14, 21])
    axes[-1].set_xlabel("Days from landfall", labelpad=8)
    fig.supylabel("Search interest, Google's 0–100 index", fontsize=fs.SMALL_SIZE, x=0.02)
    fs.title(fig, '"whole house generator" searches, hardest-hit state per storm')
    fs.source_line(fig, f"Google Trends daily relative interest, pulled {pulled} · {SOURCE}")
    fs.save(fig, out)
