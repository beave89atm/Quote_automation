"""Unit tests for component-PDF material title-block parsing."""

from __future__ import annotations

from pathlib import Path

from quote_core.part_materials import (
    _sectura_material_string,
    build_part_material_map,
    extract_part_material_from_pdf,
    lookup_part_material,
    parse_material_block,
    part_key_from_pdf_name,
)

_MC07_UPLOAD = Path(
    "/home/ubuntu/.cursor/projects/workspace/uploads/MC07-1620LR.idw_a49f.pdf"
)


def test_parse_material_block_gauge_pando_12ga():
    text = '''
ITEM
DESCRIPTION
STOCKCODE
1
GAUGE/P&O 12GA /SQ IN [8 17/32" X 2 7/32"]
1510-9422
GUARD LEVEL TRAILER CHASSIS SMALL
STEEL MATERIALS - 70,000 PSI
ALUMINUM MATERIALS - 38,000 PSI
'''
    thk, key, src = parse_material_block(text)
    assert thk == 0.1046
    assert key == "a36"
    assert "12" in src or "GAUGE" in src.upper() or "gauge" in src


def test_parse_material_block_gr50():
    text = "Main Plate\n1\n5/16\nGR50\n1\nCreate Drawing\n"
    thk, key, src = parse_material_block(text)
    assert thk == 0.3125
    assert key == "a572_gr50"


def test_parse_material_block_thickness_only_defaults_a36():
    text = "Channel\nSIZE: A\n3/16\nDESCRIPTION\n"
    thk, key, _src = parse_material_block(text)
    assert thk == 0.1875
    assert key == "a36"


def test_parse_skips_material_no_without_pair():
    text = "KINGPIN\nMATERIAL No.\n12345\nANGLES ±2°\nFRACTIONS ±1/16\n"
    thk, key, src = parse_material_block(text)
    assert thk is None
    assert key is None
    assert src == "no_material_block"

def test_part_key_from_pdf_name():
    assert part_key_from_pdf_name("73000567.pdf") == "73000567"
    assert part_key_from_pdf_name("73476004 WELDMENT DRAWING.pdf") == "73476004"


def test_lookup_part_material_from_description():
    from quote_core.part_materials import PartMaterial

    pm = PartMaterial(
        part_key="73476505",
        material_key="a572_gr50",
        material="A572 Grade 50",
        thickness_in=0.3125,
        source="test",
    )
    found = lookup_part_material(
        {"73476505": pm},
        '73476505  - 3/16" A36 43.875 in X 36.2467 in',
    )
    assert found is not None
    assert found.material == "A572 Grade 50"
    assert found.thickness_param() == "0.3125"


def test_parse_mc07_aluminum_5052_stock_sheet():
    text = '11 GA (0.091") 60" x 120" SHEET, ALUMINUM 5052-H32\n'
    thk, key, src = parse_material_block(text)
    assert key == "aluminum_5052"
    assert thk == 0.091
    assert "aluminum" in src
    assert _sectura_material_string(key) == "5052"


def test_parse_aluminum_5052_without_paren_uses_gauge():
    text = '11 GA 60" x 120" SHEET, ALUMINUM 5052-H32\n'
    thk, key, _src = parse_material_block(text)
    assert key == "aluminum_5052"
    assert thk == 0.1196  # carbon gauge table fallback when no (0.091")
    assert _sectura_material_string(key) == "5052"


def test_parse_md23_style_5052_stock_plate():
    text = "1/8 x 60 x 120, 5052-H32 ALUMINUM\nMU02-1004-001\n"
    thk, key, _src = parse_material_block(text)
    assert key == "aluminum_5052"
    assert thk == 0.125
    assert _sectura_material_string("aluminum_6061") == "6061"


def test_parse_aluminum_material_note_uses_thickness_note():
    text = (
        '4) MATERIAL: MU02-1004 - 1/8" PLATE, ALUMINUM 5052-H32 OR EQUIVALENT\n'
        "THICKNESS: .091 IN (11 GA)\n"
    )
    thk, key, src = parse_material_block(text)
    assert key == "aluminum_5052"
    assert thk == 0.091
    assert "thickness note" in src


def test_aluminum_materials_boilerplate_does_not_override_steel_gauge():
    text = '''
ITEM
GAUGE/P&O 12GA /SQ IN [8 17/32" X 2 7/32"]
STEEL MATERIALS - 70,000 PSI
ALUMINUM MATERIALS - 38,000 PSI
'''
    thk, key, _src = parse_material_block(text)
    assert key == "a36"
    assert thk == 0.1046


def test_mc07_pdf_if_present():
    if not _MC07_UPLOAD.is_file():
        return
    pm = extract_part_material_from_pdf(_MC07_UPLOAD)
    assert pm is not None
    assert pm.material_key == "aluminum_5052"
    assert pm.material == "5052"
    assert pm.thickness_in == 0.091
