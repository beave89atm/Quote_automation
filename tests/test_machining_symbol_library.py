"""Best Pump and Fort Worth tokens. Unknown glyphs stay unknown. No minutes."""

from __future__ import annotations

from pathlib import Path

from quote_core.machining_quote import quote_machining_features
from quote_core.machining_read import read_machining_requirements, read_stated_stock
from quote_core.machining_symbols import describe_symbol, symbol_library, unknown_symbols_in_text

_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def _write_pdf(path: Path, lines: list[str]) -> None:
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_font(fontname="dejavu", fontfile=_FONT)
    y = 72
    for line in lines:
        page.insert_text((72, y), line, fontname="dejavu", fontsize=12)
        y += 18
    doc.save(path)
    doc.close()


def test_known_tokens_from_the_practice_library():
    library = {row["id"]: row for row in symbol_library()}
    for symbol_id in (
        "diameter",
        "radius",
        "depth",
        "countersink",
        "counterbore",
        "position",
        "parallelism",
        "perpendicularity",
        "flatness",
        "basic",
        "reference",
        "thread",
        "surface_texture",
        "thru",
        "typical",
        "degree",
        "plus_minus",
        "iso_fit",
        "chamfer",
        "near_side",
        "bolt_circle",
    ):
        assert library[symbol_id]["meaning"]
        assert library[symbol_id]["citation"]

    diameter = describe_symbol("Ø.59±.03")
    assert diameter["id"] == "diameter"
    assert diameter["value"] == 0.59
    assert diameter["tolerance"] == 0.03
    assert "upper_limit" not in diameter

    radius = describe_symbol("R.03 MAX")
    assert radius["id"] == "radius"
    assert radius["value"] == 0.03
    assert radius["limit"] == "max"
    assert "count" not in radius

    depth = describe_symbol("↧ 2.50/2.00")
    assert depth["id"] == "depth"
    assert depth["depth_limits"] == [2.5, 2.0]
    assert "value" not in depth

    assert describe_symbol("CSK")["id"] == "countersink"
    sized = describe_symbol("CSK Ø.59±.03 × 90°")
    assert sized["id"] == "countersink"
    assert sized["countersink_diameter_in"] == 0.59
    assert sized["angle_deg"] == 90.0
    assert sized["tolerance"] == 0.03
    assert describe_symbol("⌵ Ø.59 × 90°")["angle_deg"] == 90.0

    assert describe_symbol("CB")["id"] == "counterbore"
    bore = describe_symbol("CB Ø.9853±.0005")
    assert bore["id"] == "counterbore"
    assert bore["diameter_in"] == 0.9853
    assert bore["tolerance"] == 0.0005
    assert "upper_limit" not in bore

    assert describe_symbol("⌖")["id"] == "position"
    assert describe_symbol("⌖.015")["value"] == 0.015
    assert describe_symbol("//")["id"] == "parallelism"
    assert describe_symbol("// .01")["value"] == 0.01
    assert describe_symbol("⊥")["id"] == "perpendicularity"
    assert describe_symbol("FLATNESS")["id"] == "flatness"
    assert describe_symbol(".005 FLATNESS")["value"] == 0.005
    assert describe_symbol("BASIC")["id"] == "basic"
    assert describe_symbol("2.50 BASIC")["value"] == 2.5
    reference = describe_symbol("(9.375)")
    assert reference["id"] == "reference"
    assert reference["value"] == 9.375
    marked = describe_symbol("(Ø.44)")
    assert marked["id"] == "reference"
    assert marked["diameter"] is True
    assert marked["value"] == 0.44

    npt = describe_symbol("1/4 NPT")
    assert npt["id"] == "thread"
    assert npt["series"] == "NPT"
    assert npt["size_in"] == 0.25
    assert "B1.20.1" in npt["citation"]
    assert npt.get("thread_form") is None
    unc = describe_symbol("7/8-9 UNC-2B")
    assert unc["id"] == "thread"
    assert unc["series"] == "UNC"
    assert unc["thread_class"] == "2B"
    assert describe_symbol("1-8 UNC")["series"] == "UNC"
    metric = describe_symbol("M12×1.75-6H")
    assert metric["id"] == "thread"
    assert metric["major_diameter_mm"] == 12.0
    assert metric["pitch_mm"] == 1.75
    assert metric["thread_class"] == "6H"
    assert metric.get("thread_form") is None
    tap = describe_symbol("M6x1 ISO - H TAP")
    assert tap["id"] == "thread"
    assert tap["thread_form"] == "tap"
    assert tap["thread_standard"] == "ISO"

    assert describe_symbol("FINISH (UOS) 125")["roughness"] == 125
    assert describe_symbol("✓125")["id"] == "surface_texture"
    assert describe_symbol("125")["known"] is False
    assert describe_symbol("THRU")["id"] == "thru"
    typical = describe_symbol("TYP")
    assert typical["id"] == "typical"
    assert "count" not in typical
    assert describe_symbol("45 DEG")["angle_deg"] == 45.0
    assert describe_symbol("+0.02/-0.01")["plus_value"] == 0.02
    fit = describe_symbol("15 g6")
    assert fit["id"] == "iso_fit"
    assert fit["applies_to"] == "shaft"
    assert "hole" not in fit["id"]
    chamfer = describe_symbol(".02×45°")
    assert chamfer["id"] == "chamfer"
    assert chamfer["size_in"] == 0.02
    assert chamfer["angle_deg"] == 45.0
    counted = describe_symbol("2X 1.00×45°")
    assert counted["id"] == "chamfer"
    assert counted["count"] == 2
    assert describe_symbol("1.00 X 82°")["known"] is False
    assert describe_symbol("NEAR SIDE")["id"] == "near_side"
    assert describe_symbol("Ø7.00 B.C.")["id"] == "bolt_circle"
    assert describe_symbol("DATUM A")["datum_letter"] == "A"


def test_undefined_glyphs_stay_unknown():
    for token in ("\u24b8", "\u24bf", "\u24bd", "\u2b21", "\u223f", "\u25b3", "\u2b21C"):
        described = describe_symbol(token)
        assert described["known"] is False
        assert described["meaning"] is None
        assert "critical" not in (described["note"] or "").lower()
    text = "hex \u2b21C circled \u24b8 detail \u223f"
    unknown = unknown_symbols_in_text(text)
    glyphs = {row["symbol"] for row in unknown}
    assert "\u2b21" in glyphs
    assert "\u24b8" in glyphs
    assert "\u223f" in glyphs
    assert all(row["known"] is False and row["meaning"] is None for row in unknown)
    assert unknown_symbols_in_text("✓125") == []


def test_practice_lines_do_not_invent_minutes_or_a_bar(tmp_path: Path):
    pdf = tmp_path / "practice.pdf"
    lines = [
        "FORGING, 62.38 X 24.00 X 20.25, 15-5 Stainless Steel",
        "1/4 NPT",
        "CSK Ø.59±.03 × 90° NEAR SIDE",
        "CSK",
        "CB",
        "7/8-9 UNC-2B",
        "M12×1.75-6H",
        ".02×45°",
        "R.03 MAX",
        "Ø3.00 THRU",
        "Ø6.90 TYP",
        "15 g6",
        "(9.375)",
        "FLATNESS .005",
        "POSITION",
        "// .01",
        "⊥",
        "FINISH (UOS) 125",
        "125",
        "\u2b21",
    ]
    _write_pdf(pdf, lines)
    reading = read_machining_requirements(pdf)
    kinds = [feature["kind"] for feature in reading["features"]]
    assert kinds.count("thread") == 3
    assert "countersink" in kinds
    assert "chamfer" in kinds
    assert "hole" not in kinds

    by_kind = {}
    for feature in reading["features"]:
        by_kind.setdefault(feature["kind"], []).append(feature)
    npt = next(row for row in by_kind["thread"] if row.get("series") == "NPT")
    assert npt["dimensions"]["diameter_in"] == 0.25
    assert npt.get("thread_form") is None
    unc = next(row for row in by_kind["thread"] if row.get("series") == "UNC")
    assert unc["thread_class"] == "2B"
    metric = next(row for row in by_kind["thread"] if "pitch_mm" in row)
    assert metric["pitch_mm"] == 1.75
    assert metric["thread_class"] == "6H"
    assert metric.get("thread_form") is None

    sink = by_kind["countersink"][0]
    assert sink["dimensions"]["countersink_diameter_in"] == 0.59
    assert sink["dimensions"]["angle_deg"] == 90.0
    assert sink["near_side"] is True
    assert sink["stated_machine"] is False

    chamfer = by_kind["chamfer"][0]
    assert chamfer["dimensions"]["size_in"] == 0.02
    assert chamfer["dimensions"]["angle_deg"] == 45.0
    assert chamfer["stated_machine"] is False

    by_text = {row["text"]: row for row in reading["callouts"]}
    bare_sink = next(row for row in reading["callouts"] if row["text"] == "COUNTERSINK")
    assert bare_sink["feature"] is False
    assert "No countersink operation was added" in bare_sink["note"]
    bare_bore = next(row for row in reading["callouts"] if row["text"] == "COUNTERBORE")
    assert bare_bore["feature"] is False
    assert "No counterbore operation was added" in bare_bore["note"]
    assert by_text["R.03 MAX"]["limit"] == "max"
    assert by_text["R.03 MAX"]["feature"] is False
    thru = by_text["Ø3.00 THRU"]
    assert thru["feature"] is False
    assert thru["thru"] is True
    assert "no hole operation" in thru["note"]
    assert "TYP does not state a count" in by_text["Ø6.90 TYP"]["note"]
    assert by_text["15 g6"]["symbol"] == "iso_fit"
    assert by_text["15 g6"]["feature"] is False
    assert by_text["(9.375)"]["symbol"] == "reference"
    assert by_text["FLATNESS .005"]["symbol"] == "flatness"
    assert by_text["FLATNESS .005"]["value"] == 0.005
    assert by_text["POSITION"]["symbol"] == "position"
    assert by_text["// .01"]["symbol"] == "parallelism"
    assert by_text["⊥"]["symbol"] == "perpendicularity"
    assert by_text["FINISH (UOS) 125"]["symbol"] == "surface_texture"
    assert by_text["FINISH (UOS) 125"]["value"] == 125
    assert all(row.get("symbol") != "surface_texture" or row["text"] != "125" for row in reading["callouts"])
    assert any(row["symbol"] == "\u2b21" and row["known"] is False for row in reading["unknown_symbols"])

    stock = read_stated_stock("\n".join(lines))
    assert stock["form"] == "forging"
    assert stock["blank_in"] == [62.38, 24.0, 20.25]
    assert "diameter_in" not in stock
    assert reading["process_from_stock"]["operation_justified"] is False
    assert reading["process_from_stock"]["stock"]["form"] == "forging"

    result = quote_machining_features(reading["features"], features_source="drawing")
    assert result["setup_time_min"] is None
    assert result["shop_rate_per_hour"] is None
    assert result["posted"] is False
    assert all(op["run_time_min"] is None for op in result["operations"])
    dumped = str(result)
    assert "B80720004" not in dumped
    assert "sprout" not in dumped.lower()
    for code in ("op_lathe", "op_lathe2"):
        assert code not in dumped
