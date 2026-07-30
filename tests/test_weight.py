from pathlib import Path

from quote_core.weight import (
    detect_material_key,
    estimate_assembly_weight,
    extract_pdf_bom_weights,
    load_materials,
    unit_weight_lb,
)

_BOM_80341805 = """
WEIGHT:
261.8 lbm
1
1
23403750
KING PIN, 3/8"
12.4 lbm
2
2
73476506
ANGLE, COUPLER PLATE ASS'LY, 18-16
37.9 lbm
3
2
80341690
CHANNEL, COUPLER PLATE ASSL'Y
12.9 lbm
0.187 in
4
1
80341691
CHANNEL, COUPLER PLATE ASSL'Y
8.1 lbm
0.250 in
5
1
80341806
MAIN PLATE, COUPLER ASM
120.4 lbm
0.312 in
6
2
80341807
CHANNEL, COUPLER PLATE
47.9 lbm
0.187 in
7
2
80341808
COVER PLATE
12.7 lbm
0.187 in
8
2
80341812
CHANNEL, COUPLER PLATE ASSL'Y
9.4 lbm
0.250 in
WEIGHT:
261.8 lbm
"""


def test_extract_pdf_bom_expands_qty_to_pieces():
    bom = extract_pdf_bom_weights(text=_BOM_80341805)
    assert bom["assembly_weight_lb"] == 261.8
    assert bom["method"] == "pdf_bom_qty"
    assert bom["part_number_count"] == 8
    assert bom["piece_count"] == 13
    # qty×unit weight for fit-up (individual piece weight)
    expected = [
        12.4,
        37.9,
        37.9,
        12.9,
        12.9,
        8.1,
        120.4,
        47.9,
        47.9,
        12.7,
        12.7,
        9.4,
        9.4,
    ]
    assert sorted(bom["component_weights_lb"]) == sorted(expected)


def test_extract_pdf_bom_fallback_without_qty_rows():
    text = """
    WEIGHT:
    261.8 lbm
    12.4 lbm
    37.9 lbm
    12.9 lbm
    8.1 lbm
    120.4 lbm
    47.9 lbm
    12.7 lbm
    9.4 lbm
    WEIGHT:
    261.8 lbm
    """
    bom = extract_pdf_bom_weights(text=text)
    assert bom["assembly_weight_lb"] == 261.8
    assert len(bom["component_weights_lb"]) == 8


def test_estimate_prefers_pdf_bom_over_stp():
    solids = [{"kind": "plate", "qty": 1, "box": [37.0, 34.0, 3.0]}]
    result = estimate_assembly_weight(solids, notes=["A36"], pdf_text=_BOM_80341805)
    assert result["method"] == "pdf_bom_qty"
    assert result["assembly_weight_lb"] == 261.8
    assert len(result["component_weights_lb"]) == 13
    assert result["piece_count"] == 13


def test_plate_net_area_uses_thickness_and_holes():
    cfg = load_materials()
    mat = cfg["materials"]["a36"]
    detail = unit_weight_lb(
        {"kind": "plate", "qty": 1, "box": [12.0, 12.0, 2.5]},
        density=mat["density_lb_in3"],
        psf_per_inch=mat["psf_per_inch"],
        fill_factors=cfg["bbox_fill_factor"],
        plate_psf={str(k): float(v) for k, v in cfg["plate_psf_carbon_steel"].items()},
        note_thicknesses=[0.25],
        hole_dias=[2.0],  # one 2" hole
    )
    # 1 ft² of 1/4" = 10.2; minus pi*1^2/144 * 10.2 ≈ 0.22 → ~10.0
    assert 9.0 <= detail["weight_lb"] <= 10.5
    assert detail["method"] == "net_area_x_psf"


def test_detect_steel_grades():
    assert detect_material_key(["PLATE A572 GR 50"]) == "a572_gr50"
    assert detect_material_key(["ASTM A36"]) == "a36"


def test_material_from_pdf_text_not_just_weld_notes():
    """BOM/title-block grades must be found even when weld notes omit them."""
    solids = [{"kind": "plate", "qty": 1, "box": [12.0, 12.0, 0.25]}]
    result = estimate_assembly_weight(
        solids,
        notes=["p1: FULL WELD BOTH SIDES"],  # no grade here
        pdf_text="MATERIAL\nA572 GR 50\nWEIGHT:\n10.2 lbm\n10.2 lbm\n",
    )
    assert result["material_key"] == "a572_gr50"
    assert result["material_label"] == "A572 Grade 50"


def test_real_80341805_pdf_bom_qty_if_present():
    pdf = Path(
        r"c:\Users\Kyle\Kannon Manufacturing Inc\Fort Worth - Documents"
        r"\Engineering\Customer Drawings\MAC Manufacturing\80341805\80341805.pdf"
    )
    if not pdf.exists():
        return
    bom = extract_pdf_bom_weights(pdf_path=pdf)
    assert bom["method"] == "pdf_bom_qty"
    assert bom["piece_count"] == 13
    assert bom["part_number_count"] == 8
