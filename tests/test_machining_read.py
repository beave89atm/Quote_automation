"""Known drawing in, machining features out. Unknown symbols stay unknown."""

from __future__ import annotations

from pathlib import Path

from quote_core.machining_quote import attach_machining_times, quote_machining_features
from quote_core.machining_read import apply_drawing_reading, read_machining_requirements
from quote_core.machining_symbols import describe_symbol, symbol_library

_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_STEP = """ISO-10303-21;
DATA;
#5=CONVERSION_BASED_UNIT('INCH',#6);
#10=CYLINDRICAL_SURFACE('',#11,0.1875);
#12=CIRCLE('',#13,0.1875);
#20=PLANE('',#21);
ENDSEC;
END-ISO-10303-21;
"""
_RICH = [
    "4X \u2300.375 DRILL THRU",
    "GROOVE .125 WIDE X .060 DEEP",
    "1/4-20 UNC-2B",
    "PLATE 1.00 THK",
    "Ra 63",
    "R.25",
    "FACE",
    "\u2302",
]


def _write_pdf(path: Path, lines: list[str]) -> None:
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_font(fontname="dejavu", fontfile=_FONT)
    y = 72
    for line in lines:
        page.insert_text((72, y), line, fontname="dejavu", fontsize=14)
        y += 24
    doc.save(path)
    doc.close()


def _kinds(reading: dict) -> list[str]:
    return [feature["kind"] for feature in reading["features"]]


def test_library_cites_standards_and_does_not_guess_typical():
    library = {row["id"]: row for row in symbol_library()}
    for symbol_id in (
        "diameter",
        "counterbore",
        "countersink",
        "depth",
        "radius",
        "surface_texture",
        "thread",
        "typical",
        "degree",
        "plus_minus",
        "chamfer",
    ):
        assert library[symbol_id]["meaning"]
        assert library[symbol_id]["citation"]
    typical = describe_symbol("TYP")
    assert typical["known"] is True
    assert "2.11.1" in typical["citation"]
    assert "similar" not in typical["meaning"].lower()
    assert "blank" in typical["meaning"].lower()
    diameter = describe_symbol("\u2300")
    assert diameter["known"] is True
    assert "2.1" in diameter["citation"]
    assert "diameter" in diameter["meaning"].lower()


def test_symbol_not_in_the_library_is_unknown():
    for token in ("\u2302", "\u00a7"):
        described = describe_symbol(token)
        assert described["known"] is False
        assert described["meaning"] is None
        assert described["citation"] is None
        assert "not guessed" in described["note"].lower()


def test_known_pdf_and_step_list_only_what_is_in_the_file(tmp_path: Path):
    pdf = tmp_path / "known.pdf"
    step = tmp_path / "known.step"
    _write_pdf(pdf, _RICH)
    step.write_text(_STEP)
    import fitz

    doc = fitz.open(pdf)
    extracted = "\n".join(page.get_text("text") for page in doc)
    doc.close()
    assert "\u2300" in extracted
    assert "\u2302" in extracted

    reading = read_machining_requirements(pdf, step)
    assert _kinds(reading) == ["hole", "groove", "thread", "plate", "face"]
    hole, groove, thread, plate, face = reading["features"]

    assert hole["tolerance"] == "drill"
    assert hole["dimensions"]["diameter_in"] == 0.375
    assert hole["dimensions"]["count"] == 4
    assert "depth_in" not in hole["dimensions"]
    assert any(row["field"] == "depth_in" for row in hole["blank_fields"])
    assert hole["step_match"]["diameter_in"] == 0.375
    assert "second feature" in hole["step_match"]["note"]

    assert groove["dimensions"] == {"width_in": 0.125, "depth_in": 0.06}
    assert any(row["field"] == "machine" for row in groove["blank_fields"])

    assert thread["dimensions"]["diameter_in"] == 0.25
    assert thread["threads_per_inch"] == 20
    assert thread["series"] == "UNC"
    assert thread["thread_class"] == "2B"
    assert "thread_form" not in thread
    assert any(row["field"] == "thread_form" for row in thread["blank_fields"])

    assert plate["dimensions"]["thickness_in"] == 1.0
    assert face["kind"] == "face"
    assert "machine" not in face
    assert any(row["field"] == "machine" for row in face["blank_fields"])

    assert all(row["feature"] is False for row in reading["callouts"])
    assert any(row["symbol"] == "surface_texture" and row["value"] == "63" for row in reading["callouts"])
    assert any(row["symbol"] == "radius" for row in reading["callouts"])
    assert reading["unknown_symbols"][0]["symbol"] == "\u2302"
    assert reading["unknown_symbols"][0]["known"] is False
    assert reading["unknown_symbols"][0]["meaning"] is None
    assert reading["geometry"]["plane_count"] == 1
    assert reading["geometry"]["cylinders"][0]["diameter_in"] == 0.375
    assert reading["practiced_on_shared_drive"] is False
    assert any("shared drive" in note for note in reading["notes"])
    assert any("not holes" in note for note in reading["unreadable"])
    assert any("thread left blank" in note for note in reading["unreadable"])
    assert any("groove left blank" in note for note in reading["unreadable"])


def test_step_alone_does_not_invent_a_hole(tmp_path: Path):
    step = tmp_path / "only.step"
    step.write_text(_STEP)
    reading = read_machining_requirements(stp_path=step)
    assert reading["features"] == []
    assert reading["geometry"]["cylinders"]
    assert any("not holes" in note for note in reading["unreadable"])
    assert any("PDF was not supplied" in note for note in reading["unreadable"])


def test_diameter_without_a_process_is_not_a_hole(tmp_path: Path):
    pdf = tmp_path / "od.pdf"
    _write_pdf(pdf, ["\u23002.50", "1/2 DIA"])
    reading = read_machining_requirements(pdf)
    assert reading["features"] == []
    assert len(reading["callouts"]) == 2
    assert all(row["feature"] is False for row in reading["callouts"])


def test_read_hole_wires_into_the_machining_result(tmp_path: Path):
    pdf = tmp_path / "drill.pdf"
    step = tmp_path / "drill.step"
    _write_pdf(pdf, ["4X \u2300.375 DRILL THRU"])
    step.write_text(_STEP)
    takeoff = apply_drawing_reading({}, pdf, step)
    assert takeoff["machining_features_source"] == "drawing"
    assert len(takeoff["machining_features"]) == 1
    times = attach_machining_times({"weld_minutes": 2.0}, takeoff)
    machining = times["machining"]
    assert times["weld_minutes"] == 2.0
    assert machining["reads_drawings"] is True
    assert machining["posted"] is False
    assert machining["operation_count"] == 1
    assert machining["operations"][0]["operation_code"] == "op_mill"
    assert machining["operations"][0]["name"] == "drill"
    assert machining["operations"][0]["run_time_min"] is None
    assert machining["setup_time_min"] is None
    assert machining["quote_done"] is False
    assert machining["missing"] == ["run_time", "setup_time"]
    assert any("shared drive" in note for note in machining["notes"])

    overridden = quote_machining_features(
        takeoff["machining_features"],
        operation_cycle_times={"mill:drill:0.375": 6.5},
        features_source="drawing",
    )
    assert overridden["operations"][0]["run_time_min"] == 6.5
    assert overridden["operations"][0]["run_time_source"] == "cycle_override"
    assert overridden["setup_time_min"] is None
    assert overridden["quote_done"] is False


def test_unresolved_callout_leaves_operation_count_blank(tmp_path: Path):
    pdf = tmp_path / "thread.pdf"
    _write_pdf(pdf, ["1/4-20 UNC-2B"])
    reading = read_machining_requirements(pdf)
    result = quote_machining_features(reading["features"], features_source="drawing")
    assert result["operation_count"] is None
    assert result["quote_done"] is False
    assert "operation_count" in result["missing"]
    assert result["operations"] == []


def test_plate_over_three_quarters_stays_purchased(tmp_path: Path):
    pdf = tmp_path / "plate.pdf"
    _write_pdf(pdf, ["PLATE 1.00 THK"])
    reading = read_machining_requirements(pdf)
    result = quote_machining_features(reading["features"], features_source="drawing")
    assert result["operation_count"] == 0
    assert result["needs_machining"] is False
    assert result["purchased_components"][0]["thickness_in"] == 1.0
    assert result["item_operations"] == []


def test_typed_features_are_not_replaced_by_the_drawing(tmp_path: Path):
    pdf = tmp_path / "drill.pdf"
    _write_pdf(pdf, ["4X \u2300.375 DRILL THRU"])
    typed = {
        "kind": "hole",
        "machine": "mill",
        "tolerance": "loose",
        "dimensions": {"diameter_in": 0.5},
    }
    takeoff = apply_drawing_reading(
        {"machining_features": [typed], "machining_features_source": "typed"},
        pdf,
        None,
    )
    assert takeoff["machining_features"][0]["dimensions"]["diameter_in"] == 0.5
    assert takeoff["machining_reading"]["features"][0]["dimensions"]["diameter_in"] == 0.375


def _no_operation_codes(result: dict) -> None:
    assert result["quote_done"] is False
    assert result["posted"] is False
    assert result["shop_rate_per_hour"] is None
    assert result["setup_time_min"] is None
    assert result["item_operations"] == []
    assert result["operations"] == []
    assert result["missing"] == ["operation_count", "run_time", "setup_time"]
    dumped = str(result)
    for code in ("op_mill", "op_lathe", "op_lathe2"):
        assert code not in dumped


def test_chamfer_note_is_a_feature_without_an_operation_code(tmp_path: Path):
    named = describe_symbol("CHAMFER")
    assert named["known"] is True
    assert named["id"] == "chamfer"
    assert "4-41" in named["citation"]
    assert "6.1" in named["citation"]
    noted = describe_symbol("45° CHAMFER")
    assert noted["known"] is True
    assert noted["angle_deg"] == 45.0
    sized = describe_symbol(".06 X 45° CHAMFER")
    assert sized["angle_deg"] == 45.0
    assert sized["size_in"] == 0.06
    bare_angle = describe_symbol("45°")
    assert bare_angle["id"] != "chamfer"

    pdf = tmp_path / "chamfer.pdf"
    _write_pdf(pdf, ["45° CHAMFER", "CHAMFER"])
    reading = read_machining_requirements(pdf)
    assert _kinds(reading) == ["chamfer", "chamfer"]
    angled, plain = reading["features"]
    assert angled["callout"] == "45° CHAMFER"
    assert angled["dimensions"]["angle_deg"] == 45.0
    assert "size_in" not in angled["dimensions"]
    assert angled["stated_machine"] is False
    assert "4-41" in angled["citation"]
    assert "6.1" in angled["citation"]
    assert "4-41" in angled["angle_citation"]
    assert any(row["field"] == "machine" for row in angled["blank_fields"])
    assert any(row["field"] == "size_in" for row in angled["blank_fields"])
    assert plain["dimensions"] == {}
    assert any(row["field"] == "angle_deg" for row in plain["blank_fields"])
    result = quote_machining_features(reading["features"], features_source="drawing")
    assert result["needs_machining"] is True
    _no_operation_codes(result)


def test_countersink_text_callout_is_a_feature_without_an_operation_code(tmp_path: Path):
    word = describe_symbol("COUNTERSINK")
    assert word["known"] is True
    assert word["id"] == "countersink"
    assert "2.3" in word["citation"]
    pattern = describe_symbol("COUNTERSINK \u23001.00 X 82°")
    assert pattern["known"] is True
    assert pattern["countersink_diameter_in"] == 1.0
    assert pattern["angle_deg"] == 82.0
    assert "2.11.1" in pattern["citation"]
    glyph = describe_symbol("\u2335 \u2300.50 X 90°")
    assert glyph["id"] == "countersink"
    assert glyph["countersink_diameter_in"] == 0.5
    assert glyph["angle_deg"] == 90.0
    by_only = describe_symbol("1.00 X 82°")
    assert by_only["known"] is False

    pdf = tmp_path / "csk.pdf"
    _write_pdf(
        pdf,
        [
            "COUNTERSINK \u23001.00 X 82°",
            "COUNTERSINK",
            "SLEEVE PLATE COUNTERBORE",
        ],
    )
    reading = read_machining_requirements(pdf)
    assert _kinds(reading) == ["countersink"]
    feature = reading["features"][0]
    assert feature["dimensions"]["countersink_diameter_in"] == 1.0
    assert feature["dimensions"]["angle_deg"] == 82.0
    assert feature["stated_machine"] is False
    assert "2.3" in feature["citation"]
    assert "4-41" in feature["angle_citation"]
    assert "BY" in feature["note"]
    assert any(row["field"] == "machine" for row in feature["blank_fields"])
    texts = [callout["text"] for callout in reading["callouts"]]
    assert "COUNTERSINK" in texts
    assert "COUNTERBORE" in texts
    assert all(callout["feature"] is False for callout in reading["callouts"])
    sink = next(callout for callout in reading["callouts"] if callout["text"] == "COUNTERSINK")
    assert "No countersink operation was added" in sink["note"]
    bore = next(callout for callout in reading["callouts"] if callout["text"] == "COUNTERBORE")
    assert "No counterbore operation was added" in bore["note"]
    result = quote_machining_features(reading["features"], features_source="drawing")
    assert result["needs_machining"] is True
    _no_operation_codes(result)


def test_named_machine_on_chamfer_or_countersink_uses_only_that_code(tmp_path: Path):
    pdf = tmp_path / "mill.pdf"
    _write_pdf(pdf, ["MILL 45° CHAMFER"])
    reading = read_machining_requirements(pdf)
    result = quote_machining_features(reading["features"], features_source="drawing")
    assert result["operations"][0]["name"] == "chamfer"
    assert result["operations"][0]["operation_code"] == "op_mill"
    assert result["operations"][0]["run_time_min"] is None
    assert result["setup_time_min"] is None
    assert result["shop_rate_per_hour"] is None
    assert result["quote_done"] is False
    assert result["posted"] is False
    assert "op_lathe" not in str(result["operations"])

    lathe = tmp_path / "lathe.pdf"
    _write_pdf(lathe, ["LATHE 2 COUNTERSINK \u2300.50 X 82°"])
    lathe_reading = read_machining_requirements(lathe)
    lathe_result = quote_machining_features(lathe_reading["features"], features_source="drawing")
    assert lathe_result["operations"][0]["operation_code"] == "op_lathe2"
    assert lathe_result["operations"][0]["run_time_min"] is None
    assert lathe_result["setup_time_min"] is None
    assert lathe_result["quote_done"] is False

    drill = tmp_path / "drill-word.pdf"
    _write_pdf(drill, ["DRILL 45° CHAMFER"])
    drill_reading = read_machining_requirements(drill)
    drill_result = quote_machining_features(drill_reading["features"], features_source="drawing")
    _no_operation_codes(drill_result)


def test_reader_source_does_not_invent_codes_or_call_sectura():
    for module in ("quote_core.machining_read", "quote_core.machining_symbols"):
        src = Path(__import__(module, fromlist=["x"]).__file__).read_text()
        lowered = src.lower()
        assert "secturafab" not in lowered
        assert "1020249" not in src
        assert "116633" not in src
        for code in ("op_mill", "op_lathe", "op_lathe2", "op_lathe3"):
            assert code not in src
