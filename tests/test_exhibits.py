"""The committed SVGs are fixtures: each regenerates byte-for-byte from the committed CSVs,
carries the published numbers, and bakes in nothing that would change between builds."""

import re
from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd
import pytest

from article_data import exhibits
from article_data.exhibits import figstyle, storm
from article_data.paths import COMPUTED, EXHIBITS, INPUTS

NAMES = sorted(exhibits.EXHIBITS_BY_FILE)
FILES = [figstyle.variant_name(n, t) for n in NAMES for t in figstyle.THEMES]
HEX = re.compile(r"#[0-9a-fA-F]{6}")
TEXT_CONTRAST = 4.5  # WCAG 1.4.3, small text


def theme_of(file: str) -> str:
    return "dark" if file.endswith("-dark.svg") else "light"


@pytest.fixture(scope="module")
def rendered(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("exhibits")
    written = exhibits.render(out_dir=out)
    assert sorted(p.name for p in written) == sorted(FILES)
    return out


@pytest.mark.parametrize("file", FILES)
def test_committed_svg_regenerates_byte_identically(rendered: Path, file: str):
    assert (rendered / file).read_bytes() == (EXHIBITS / file).read_bytes()


def test_rendering_twice_gives_the_same_bytes(tmp_path: Path):
    name = "ex4-saidi-dumbbell.svg"
    exhibits.render([name], out_dir=tmp_path / "a")
    exhibits.render([name], out_dir=tmp_path / "b")
    for theme in figstyle.THEMES:
        file = figstyle.variant_name(name, theme)
        assert (tmp_path / "a" / file).read_bytes() == (tmp_path / "b" / file).read_bytes()


@pytest.mark.parametrize("name", NAMES)
def test_dark_variant_differs_from_light_only_in_its_colours(name: str):
    light = (EXHIBITS / name).read_text()
    dark = (EXHIBITS / figstyle.variant_name(name, "dark")).read_text()
    assert light != dark
    lp, dp = figstyle.palette("light"), figstyle.palette("dark")
    for dark_hex, light_hex in ((dp.ink, lp.ink), (dp.accent, lp.accent), (dp.grey, lp.grey)):
        dark = dark.replace(dark_hex, light_hex)
    # Marker ids are matplotlib's hash of the marker and its style, colour included.
    marker_id = re.compile(r"#?m[0-9a-f]{10}")
    assert marker_id.sub("#m", dark) == marker_id.sub("#m", light)


@pytest.mark.parametrize("file", FILES)
def test_svg_has_no_timestamp_tool_version_or_plate(file: str):
    svg = (EXHIBITS / file).read_text()
    assert "dc:date" not in svg
    assert "Matplotlib v" not in svg
    # Nothing painted behind the plot: the figure and axes patches are dropped,
    # so no path spans the viewBox.
    size = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
    assert size
    assert f"L {size[1]} {size[2]} " not in svg


@pytest.mark.parametrize("file", FILES)
def test_text_is_inter_outlines_not_font_references(file: str):
    svg = (EXHIBITS / file).read_text()
    assert "<text" not in svg
    assert "font-family" not in svg
    assert "DejaVu" not in svg
    faces = {m.group(1) for m in re.finditer(r'<path id="(Inter-[A-Za-z]+)-[0-9a-f]+"', svg)}
    assert faces
    assert faces <= {"Inter-Regular", "Inter-SemiBold", "Inter-Bold"}


def test_vendored_fonts_are_the_three_inter_weights():
    from matplotlib import font_manager, ft2font

    files = figstyle.register_fonts(INPUTS)
    weights = {font_manager.ttfFontProperty(ft2font.FT2Font(str(f))).weight for f in files}
    assert weights == {400, 600, 700}
    assert all(
        f.fname in {str(p) for p in files}
        for f in font_manager.fontManager.ttflist
        if f.name == figstyle.FONT_FAMILY
    )


@pytest.mark.parametrize("file", FILES)
def test_every_colour_is_one_of_the_variants_three(file: str):
    svg = (EXHIBITS / file).read_text()
    pal = figstyle.palette(theme_of(file))
    assert "var(" not in svg  # an <img> cannot resolve page variables
    used = set(HEX.findall(svg))
    assert {pal.ink, pal.accent} <= used <= {pal.ink, pal.accent, pal.grey}


class TestEachVariantReadsOnItsCanvas:
    """The committed colours are what every visitor sees; measured against the brand's
    canvas token for that theme, unfiltered."""

    @pytest.fixture(params=figstyle.THEMES)
    def pal(self, request: pytest.FixtureRequest) -> figstyle.Palette:
        return figstyle.palette(request.param)

    def test_ink_and_accent_are_the_themes_own_tokens(self, pal: figstyle.Palette):
        semantic = figstyle.load_tokens()["semantic"][pal.theme]
        assert pal.ink == figstyle.to_hex(semantic["text"]["secondary"])
        assert pal.accent == figstyle.to_hex(semantic["accent"]["base"])
        assert pal.canvas == figstyle.to_hex(semantic["surface"]["canvas"])

    def test_ink_and_accent_clear_small_text_contrast(self, pal: figstyle.Palette):
        assert figstyle.contrast(pal.ink, pal.canvas) >= TEXT_CONTRAST
        assert figstyle.contrast(pal.accent, pal.canvas) >= TEXT_CONTRAST

    def test_grey_sits_at_the_non_text_floor(self, pal: figstyle.Palette):
        assert figstyle.contrast(pal.grey, pal.canvas) == pytest.approx(
            figstyle.GRAPHICS_CONTRAST, abs=0.02
        )
        assert figstyle.contrast(pal.grey, pal.canvas) >= figstyle.GRAPHICS_CONTRAST

    def test_the_hexes_are_the_ones_documented(self, pal: figstyle.Palette):
        expected = {
            "light": ("#545454", "#386a86", "#888f93"),
            "dark": ("#9baab8", "#7eb3d3", "#5b6165"),
        }
        assert (pal.ink, pal.accent, pal.grey) == expected[pal.theme]

    def test_contrast_is_wcag(self):
        assert figstyle.contrast("#000000", "#ffffff") == pytest.approx(21.0)
        assert figstyle.contrast("#ffffff", "#000000") == pytest.approx(21.0)
        assert figstyle.contrast("#777777", "#ffffff") == pytest.approx(4.48, abs=0.01)


def test_brand_tokens_resolve_to_the_hex_the_brand_documents():
    # The approximations in the brand's own color.ts comments.
    assert figstyle.to_hex("oklch(0.10 0.01 255)") == "#020306"
    assert figstyle.to_hex("oklch(0.50 0.07 235)") == "#386a86"
    assert figstyle.to_hex("oklch(0.97 0.003 100)") == "#f5f5f3"
    assert figstyle.to_hex("#7EB3D3") == "#7eb3d3"
    with pytest.raises(ValueError):
        figstyle.to_hex("rgba(220, 228, 236, 0.14)")


def test_unknown_exhibit_is_refused(tmp_path: Path):
    with pytest.raises(KeyError, match="no exhibit"):
        exhibits.render(["ex99.svg"], out_dir=tmp_path)
    assert not list(tmp_path.iterdir())


@pytest.fixture(scope="module")
def big() -> pd.DataFrame:
    return storm.load(COMPUTED)


def drawn(text: str) -> str:
    """How a drawn label appears in the file: text is exported as outlines, and
    matplotlib writes the string it outlined as a comment beside them."""
    return f"<!-- {escape(text)} -->"


class TestChartsCarryThePublishedNumbers:
    """The labels drawn are the CSV's values, formatted as the article prints them.
    Checked on the light file; the dark one differs only in colour (asserted above)."""

    def test_storm_multiplier_labels_tampa_and_the_median(self, big: pd.DataFrame):
        svg = (EXHIBITS / "ex2-storm-multiplier.svg").read_text()
        tampa = big[big["utility"].str.startswith("Tampa Electric")].iloc[0]
        assert drawn(f"Tampa Electric (FL)  {tampa['multiplier']:.1f}×") in svg
        assert "60.4×" in svg
        assert drawn(f"Median of all {len(big)}: {big['multiplier'].median():.1f}×") in svg
        assert "Median of all 163: 1.9×" in svg

    def test_dumbbell_labels_all_seven_table_multipliers(self, big: pd.DataFrame):
        svg = (EXHIBITS / "ex4-saidi-dumbbell.svg").read_text()
        table = storm.table_rows(big)
        assert len(table) == 7
        for row in table.itertuples():
            assert drawn(f"{row.multiplier:.1f}×") in svg
            assert drawn(str(row.label)) in svg
        assert [f"{m:.1f}" for m in table["multiplier"]] == [
            "60.4", "43.4", "29.9", "28.8", "23.7", "15.4", "11.9"
        ]  # fmt: skip

    def test_state_league_has_the_three_utility_floor_and_labels_the_top(self, big: pd.DataFrame):
        svg = (EXHIBITS / "ex10-state-league.svg").read_text()
        league = storm.state_league(big)
        assert league["n"].min() >= 3
        assert league.iloc[0]["state"] == "FL"
        assert drawn(f"{league.iloc[0]['median']:.1f}×") in svg
        assert drawn("16.1×") in svg
        for state, n in zip(league["state"], league["n"], strict=True):
            assert drawn(f"{state}  ·  {n}") in svg

    def test_decay_chart_shows_day_counts_and_no_multiple(self):
        svg = (EXHIBITS / "ex5-decay-curves.svg").read_text()
        window = pd.read_csv(COMPUTED / "seven-day-window.csv")
        for row in window.itertuples():
            assert drawn(f"Day {row.raw_days_to_baseline}:") in svg
            assert f"landfall {row.landfall} · baseline {row.raw_baseline:.0f} -->" in svg
        assert svg.count(drawn("back to baseline")) == 3
        assert set(window["raw_days_to_baseline"]) == {10, 5, 8}
        assert "×" not in svg

    def test_gap_scatter_labels_harris_and_los_angeles(self):
        svg = (EXHIBITS / "ex13-gap-counties.svg").read_text()
        top = pd.read_csv(COMPUTED / "penetration-gap-top25.csv")
        assert len(top) == 25
        assert drawn("Harris, TX") in svg
        assert drawn("Los Angeles, CA") in svg
        assert drawn("Cook, IL") not in svg  # below both label thresholds
