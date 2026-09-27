"""Storm-multiplier exhibits, drawn from ``computed/storm-multiplier-2024.csv``.

- ``ex2-storm-multiplier.svg``  every big utility ranked by multiplier, the
  seven in the article's table highlighted and the top four labelled.
- ``ex4-saidi-dumbbell.svg``    SAIDI without and with major event days for the
  seven utilities in the article's table.
- ``ex10-state-league.svg``     median multiplier of big utilities per state,
  states with three or more, storm-belt states highlighted.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from matplotlib.ticker import FuncFormatter

from article_data.exhibits import figstyle as fs
from article_data.storm_multiplier import BIG_CUSTOMER_FLOOR, STORM_BELT

CSV = "storm-multiplier-2024.csv"
SOURCE = "EIA-861 (2024) Reliability file, IEEE-1366 block · FlowMatrix Research"

# The seven utilities in the article's table, matched on the EIA-861 utility name
# prefix and state; the display name is the article's short form.
TABLE = [
    ("Tampa Electric", "FL"),
    ("Duke Energy Carolinas", "SC"),
    ("Duke Energy Florida", "FL"),
    ("CenterPoint Energy", "TX"),
    ("Dominion Energy South Carolina", "SC"),
    ("Florida Power & Light", "FL"),
    ("Georgia Power", "GA"),
]


def load(computed: Path) -> pd.DataFrame:
    rows = pd.read_csv(computed / CSV)
    big = rows[rows["customers"] >= BIG_CUSTOMER_FLOOR]
    return big.sort_values(["multiplier", "utility_id"], ascending=[False, True]).reset_index(
        drop=True
    )


def table_rows(big: pd.DataFrame) -> pd.DataFrame:
    """The seven table utilities with a ``label`` column, in multiplier order."""
    picked = []
    for name, state in TABLE:
        hit = big[big["utility"].str.startswith(name) & (big["state"] == state)]
        if len(hit) != 1:
            raise ValueError(f"expected one row for {name} ({state}), found {len(hit)}")
        picked.append(hit.assign(label=f"{name} ({state})"))
    return pd.concat(picked).sort_values("multiplier", ascending=False).reset_index(drop=True)


def times(x: float, _pos: float | None = None) -> str:
    return f"{x:.0f}×"


def ex2_storm_multiplier(computed: Path, out: Path, pal: fs.Palette) -> None:
    big = load(computed)
    table = table_rows(big)
    in_table = big["utility_id"].isin(table["utility_id"]) & big["state"].isin(table["state"])
    n = len(big)
    median = float(big["multiplier"].median())

    fig = fs.figure(4.8)
    fig.subplots_adjust(left=0.10, right=0.98, top=0.87, bottom=0.17)
    ax = fig.add_subplot()
    ax.bar(
        range(n),
        big["multiplier"],
        width=1.0,
        color=[pal.accent if hit else pal.grey for hit in in_table],
        linewidth=0,
    )
    ax.set_xlim(-0.5, n - 0.5)
    ax.set_ylim(0, 65)
    ax.set_yticks([0, 20, 40, 60])
    ax.yaxis.set_major_formatter(FuncFormatter(times))
    ax.set_xticks([])
    ax.spines["bottom"].set_visible(False)
    ax.set_xlabel(
        f"{n} utilities with {BIG_CUSTOMER_FLOOR:,}+ customers, ranked by multiplier", labelpad=8
    )
    ax.set_ylabel("SAIDI with major event days ÷ without")
    fs.title(fig, "The 2024 storm multiplier, every big utility")

    # Top four, labelled with a leader from the bar top.
    label_y = [60.4, 47.0, 35.5, 26.0]
    for i, y_text in enumerate(label_y):
        row = big.iloc[i]
        short = row["utility"].split(",")[0].removesuffix(" Co").removesuffix(" LLC")
        ax.plot([i + 0.5, 6, 8], [row["multiplier"], y_text, y_text], color=pal.ink, lw=1)
        ax.text(9, y_text, f"{short} ({row['state']})  {row['multiplier']:.1f}×", va="center")

    ax.axhline(median, color=pal.ink, lw=1, ls=(0, (3, 3)))
    ax.text(n - 1, median + 1.5, f"Median of all {n}: {median:.1f}×", ha="right", va="bottom")
    fs.swatch_legend(
        ax, [(pal.accent, "In the article's table"), (pal.grey, "Other big utilities")], 0.55, 0.95
    )
    fs.source_line(fig, SOURCE)
    fs.save(fig, out)


def ex4_saidi_dumbbell(computed: Path, out: Path, pal: fs.Palette) -> None:
    table = table_rows(load(computed))
    n = len(table)
    ys = list(range(n - 1, -1, -1))

    fig = fs.figure(4.6)
    fig.subplots_adjust(left=0.46, right=0.96, top=0.85, bottom=0.23)
    ax = fig.add_subplot()
    ax.hlines(ys, table["saidi_without_med"], table["saidi_with_med"], color=pal.grey, lw=2)
    ax.plot(table["saidi_without_med"], ys, "o", color=pal.grey, ms=9, clip_on=False)
    ax.plot(table["saidi_with_med"], ys, "o", color=pal.accent, ms=9)
    for y, with_med, mult in zip(ys, table["saidi_with_med"], table["multiplier"], strict=True):
        ax.text(float(with_med) + 130, y, f"{mult:.1f}×", va="center")
    ax.set_yticks(ys)
    ax.set_yticklabels(table["label"], fontsize=fs.SMALL_SIZE)
    ax.set_ylim(-0.7, n - 0.3)
    ax.set_xlim(0, 8_800)
    ax.set_xticks([0, 2_000, 4_000, 6_000, 8_000])
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.set_xlabel("SAIDI, minutes per customer, 2024", labelpad=8)
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    fs.title(fig, "The year without its storms, and with them")
    fs.swatch_legend(
        ax,
        [(pal.grey, "Without major event days"), (pal.accent, "With major event days")],
        0.42,
        0.22,
    )
    fs.source_line(fig, SOURCE)
    fs.save(fig, out)


def state_league(big: pd.DataFrame, minimum: int = 3) -> pd.DataFrame:
    g = big.groupby("state").agg(n=("multiplier", "size"), median=("multiplier", "median"))
    g = g[g["n"] >= minimum].reset_index()
    return g.sort_values(["median", "state"], ascending=[False, True]).reset_index(drop=True)


def ex10_state_league(computed: Path, out: Path, pal: fs.Palette) -> None:
    big = load(computed)
    league = state_league(big)
    n = len(league)
    national = float(big["multiplier"].median())
    ys = list(range(n - 1, -1, -1))

    fig = fs.figure(8.4)
    fig.subplots_adjust(left=0.14, right=0.97, top=0.895, bottom=0.13)
    ax = fig.add_subplot()
    ax.barh(
        ys,
        league["median"],
        height=0.62,
        color=[pal.accent if s in STORM_BELT else pal.grey for s in league["state"]],
        linewidth=0,
    )
    for y, med in zip(ys, league["median"], strict=True):
        if float(med) >= 5:
            ax.text(float(med) + 0.25, y, f"{med:.1f}×", va="center")
    ax.set_yticks(ys)
    ax.set_yticklabels([f"{s}  ·  {k}" for s, k in zip(league["state"], league["n"], strict=True)])
    ax.tick_params(axis="y", length=0)
    ax.set_ylim(-0.7, n - 0.3)
    ax.set_xlim(0, 18)
    ax.set_xticks([0, 5, 10, 15])
    ax.xaxis.set_major_formatter(FuncFormatter(times))
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.axvline(national, color=pal.ink, lw=1, ls=(0, (3, 3)))
    ax.text(national + 0.3, 1, f"All big utilities: {national:.1f}×", va="center", ha="left")
    ax.set_xlabel("Median storm multiplier of the state's big utilities", labelpad=8)
    fs.title(
        fig,
        "The state league table, 2024",
        "Three or more big utilities per state; the count follows the state code",
    )
    fs.swatch_legend(ax, [(pal.accent, "Storm-belt state"), (pal.grey, "Other states")], 0.56, 0.62)
    fs.source_line(fig, SOURCE)
    fs.save(fig, out)
