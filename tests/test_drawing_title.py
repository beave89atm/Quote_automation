from quote_core.drawing_title import extract_assembly_description, extract_title_from_pdf_text


def test_extract_title_coupler_asm():
    text = """THIS DRAWING IS THE PROPERTY OF MAC TRAILER
PART NO
WEIGHT:
COUPLER ASM, 18-16, PNEUMATIC TANK
281.0 lbm
73476004
TRAILER MANUFACTURING INC.
"""
    assert extract_title_from_pdf_text(text, part_key="73476004") == (
        "COUPLER ASM, 18-16, PNEUMATIC TANK"
    )


def test_extract_title_stops_at_bom():
    text = """PART # : 73476054
COUPLER ASM, 18-16, TANK, 102\", 5/16\"
ITEM
QTY.
PART No.
KING PIN, 3/8\"
"""
    assert extract_title_from_pdf_text(text, part_key="73476054") == (
        'COUPLER ASM, 18-16, TANK, 102", 5/16"'
    )


def test_extract_assembly_description_job43_style(tmp_path):
    # Use real job library when present; otherwise skip.
    from app.db import SessionLocal, Job
    from pathlib import Path

    j = SessionLocal().get(Job, 43)
    if not j:
        return
    lib = (j.takeoff() or {}).get("library") or {}
    if not lib.get("folder"):
        return
    title = extract_assembly_description(
        part_key="73476004",
        pdf_path=Path(j.pdf_path) if j.pdf_path else None,
        library_folder=lib.get("folder"),
        related_pdf_names=list(lib.get("related_pdfs") or []),
    )
    assert title == "COUPLER ASM, 18-16, PNEUMATIC TANK"
