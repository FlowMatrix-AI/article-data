"""Brand styling and deterministic SVG output for the exhibits.

Colours come from ``inputs/brand-tokens.json``, a verbatim copy of the
site's brand tokens (the package version is recorded in the file). The brand
authors its light tokens in oklch(), which matplotlib cannot parse, so
:func:`to_hex` resolves them here with the standard OKLab transform; the
resolved values match the hex approximations the brand's own source comments.

The site loads the exhibits through ``<img>``, so the file gets neither the
page's webfonts nor its CSS variables: what is committed is what every visitor
sees, on both themes, and the engine no longer filters SVG exhibits in dark
mode. Three choices follow from that.

- Text is exported as glyph outlines from the vendored Inter faces in
  ``inputs/fonts/`` (the ``@fontsource-variable/inter`` latin subset the site
  serves, instanced at 400/600/700; OFL, licence alongside), so the type is the
  brand face for everyone and never depends on a font the reader has installed.
- Nothing is painted behind the plot: the figure and axes patches are dropped,
  so the page canvas shows through on either theme.
- Each exhibit is exported twice, once per page canvas, and the site picks the
  variant by theme (the pattern its light/dark logo lockups already use). Each
  variant takes its ink and accent from that theme's own brand tokens
  (``text.secondary`` and ``accent.base``, both above 4.5:1 on their canvas),
  and its de-emphasis grey is solved to sit at the 3:1 non-text floor against
  that canvas rather than picked by hand. :mod:`tests.test_exhibits` measures
  all six.

Determinism: layout uses fixed margins and anchors, the glyph outlines come
from the committed font files, the hash salt is fixed and no date or tool
version is written, so the same CSV yields the same bytes. The two variants
differ only in their colours, which the tests also assert.
"""

from __future__ import annotations

import io
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("svg")

from matplotlib import font_manager  # noqa: E402
from matplotlib import pyplot as plt  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from article_data.paths import INPUTS  # noqa: E402

TOKENS_FILE = "brand-tokens.json"
FONTS_DIR = "fonts"
FONT_FAMILY = "Inter"

# Figure geometry. The SVG viewBox is in points, so at an article column of
# ~680px a 540pt figure scales up by ~1.25 and on a 360px phone down to ~0.65;
# the type sizes below keep tick labels at or above 9px on the phone.
WIDTH_IN = 7.5
FONT_SIZE = 14
SMALL_SIZE = 13
TITLE_SIZE = 16
HASH_SALT = "field-notes"  # matplotlib id salt; changing it changes every committed SVG
GRAPHICS_CONTRAST = 3.0  # WCAG 1.4.11, non-text contrast


THEMES = ("light", "dark")


@dataclass(frozen=True)
class Palette:
    """One variant's three committed colours, as lowercase hex, and the canvas
    they were chosen for."""

    theme: str
    canvas: str
    ink: str
    accent: str
    grey: str


def _oklab_to_hex(L: float, a: float, b: float) -> str:  # noqa: N803
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    lin_l, lin_m, lin_s = l_**3, m_**3, s_**3
    rgb = (
        4.0767416621 * lin_l - 3.3077115913 * lin_m + 0.2309699292 * lin_s,
        -1.2684380046 * lin_l + 2.6097574011 * lin_m - 0.3413193965 * lin_s,
        -0.0041960863 * lin_l - 0.7034186147 * lin_m + 1.7076147010 * lin_s,
    )

    def encode(c: float) -> int:
        c = min(max(c, 0.0), 1.0)
        srgb = 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
        return round(srgb * 255)

    return "#{:02x}{:02x}{:02x}".format(*(encode(c) for c in rgb))


def oklch_to_hex(L: float, C: float, h: float) -> str:  # noqa: N803
    return _oklab_to_hex(L, C * math.cos(math.radians(h)), C * math.sin(math.radians(h)))


_OKLCH = re.compile(r"oklch\(\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\)")


def to_hex(token: str) -> str:
    """A brand colour token as lowercase hex; accepts ``#RRGGBB`` and ``oklch(L C h)``."""
    if token.startswith("#") and len(token) == 7:
        return token.lower()
    m = _OKLCH.fullmatch(token.strip())
    if not m:
        raise ValueError(f"unsupported colour token {token!r}")
    return oklch_to_hex(float(m[1]), float(m[2]), float(m[3]))


def luminance(hex_: str) -> float:
    """WCAG relative luminance of an ``#rrggbb`` colour."""

    def channel(c: int) -> float:
        s = c / 255
        return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(int(hex_[i : i + 2], 16)) for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    """WCAG contrast ratio between two ``#rrggbb`` colours."""
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _neutral(L: float) -> str:  # noqa: N803
    # A hint of the brand's blue-grey (hue 235) rather than a pure grey.
    return oklch_to_hex(L, 0.01, 235)


def _neutral_at(target: float, canvas: str) -> str:
    """The neutral nearest the canvas whose contrast against it is still ``target``,
    by bisection on oklch lightness."""
    towards_canvas = luminance(canvas) > 0.5  # lighter neutrals approach a light canvas
    lo, hi = 0.0, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if (contrast(_neutral(mid), canvas) >= target) == towards_canvas:
            lo = mid
        else:
            hi = mid
    return _neutral(lo if towards_canvas else hi)


def load_tokens(inputs_dir: Path = INPUTS) -> dict:
    return json.loads((inputs_dir / TOKENS_FILE).read_text())


def variant_name(name: str, theme: str) -> str:
    """``ex2.svg`` for the light canvas, ``ex2-dark.svg`` for the dark one."""
    return name if theme == "light" else name.replace(".svg", f"-{theme}.svg")


def palette(theme: str = "light", inputs_dir: Path = INPUTS) -> Palette:
    tokens = load_tokens(inputs_dir)
    semantic = tokens["semantic"][theme]
    canvas = to_hex(tokens["colors"]["canvas"][theme])
    return Palette(
        theme=theme,
        canvas=canvas,
        ink=to_hex(semantic["text"]["secondary"]),
        accent=to_hex(semantic["accent"]["base"]),
        grey=_neutral_at(GRAPHICS_CONTRAST, canvas),
    )


def register_fonts(inputs_dir: Path = INPUTS) -> list[Path]:
    """Make the vendored Inter faces the only ``Inter`` matplotlib can find, so the
    glyph outlines never come from whatever the build machine has installed."""
    files = sorted((inputs_dir / FONTS_DIR).glob("*.ttf"))
    if not files:
        raise FileNotFoundError(f"no font files under {inputs_dir / FONTS_DIR}")
    manager = font_manager.fontManager
    manager.ttflist = [f for f in manager.ttflist if f.name != FONT_FAMILY]
    for file in files:
        manager.addfont(str(file))
    return files


def apply(pal: Palette, inputs_dir: Path = INPUTS) -> None:
    register_fonts(inputs_dir)
    plt.rcParams.update(
        {
            "svg.fonttype": "path",
            "svg.hashsalt": HASH_SALT,
            "font.family": FONT_FAMILY,
            "font.size": FONT_SIZE,
            "text.color": pal.ink,
            "axes.edgecolor": pal.ink,
            "axes.labelcolor": pal.ink,
            "axes.labelsize": SMALL_SIZE,
            "axes.titlesize": TITLE_SIZE,
            "axes.linewidth": 1,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "xtick.color": pal.ink,
            "ytick.color": pal.ink,
            "xtick.labelsize": FONT_SIZE,
            "ytick.labelsize": FONT_SIZE,
            "xtick.major.width": 1,
            "ytick.major.width": 1,
            "xtick.major.size": 4,
            "ytick.major.size": 0,
            "grid.color": pal.ink,
            "grid.alpha": 0.25,
            "grid.linewidth": 1,
            "lines.solid_capstyle": "round",
        }
    )


def figure(height_in: float) -> Figure:
    fig = plt.figure(figsize=(WIDTH_IN, height_in))
    fig.patch.set_visible(False)  # no plate: the page canvas shows through
    return fig


def title(fig: Figure, text: str, subtitle: str | None = None) -> None:
    """Title (and optional one-line subtitle) at the figure's top-left edge."""
    fig.text(0.02, 0.975, text, fontsize=TITLE_SIZE, fontweight="bold", va="top")
    if subtitle:
        fig.text(0.02, 0.925, subtitle, fontsize=SMALL_SIZE, va="top")


def source_line(fig: Figure, text: str) -> None:
    """One muted line along the bottom edge; the article carries the full source."""
    fig.text(0.02, 0.012, text, fontsize=SMALL_SIZE, ha="left", va="bottom", alpha=0.85)


def swatch_legend(ax: Axes, entries: list[tuple[str, str]], x: float, y: float) -> None:
    """A manual legend (square swatch + label) in axes fractions; matplotlib's own
    legend positions itself from text metrics, which would tie the bytes to the
    font on the build machine."""
    for i, (colour, label) in enumerate(entries):
        yy = y - i * 0.075
        ax.plot(
            [x], [yy], marker="s", markersize=9, color=colour, transform=ax.transAxes, clip_on=False
        )
        ax.text(x + 0.025, yy, label, transform=ax.transAxes, va="center", fontsize=SMALL_SIZE)


def save(fig: Figure, path: Path) -> None:
    for ax in fig.axes:
        ax.patch.set_visible(False)
    buf = io.StringIO()
    fig.savefig(buf, format="svg", metadata={"Date": None, "Creator": None})
    plt.close(fig)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(buf.getvalue(), encoding="utf-8", newline="\n")
