"""Unit tests for component-PDF material title-block parsing."""

from __future__ import annotations

from quote_core.part_materials import (
    build_part_material_map,
    lookup_part_material,
    parse_material_block,
    part_key_from_pdf_name,
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
