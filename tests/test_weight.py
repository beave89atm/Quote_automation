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


_BOM_73476004 = """
WEIGHT:
281.0 lbm
73476004
Item
Part Number
Description
Qty
Weight
1
23403750
KING PIN, 3/8"
1
12.5 lbm
2
73000567
CHANNEL, COUPLER PLATE ASSL'Y
2
7.8 lbm
3
73000571
CHANNEL, OVER KING PIN, COUPLER ASSL'Y
1
3.5 lbm
4
73001366
CHANNEL, COUPLER PLATE 102
1
32.8 lbm
5
73001369
FRONT COVER, COUPLER PLATE, PNEUMATIC
2
12.3 lbm
6
73476504
CHANNEL, COUPLER PLATE 102
1
28.1 lbm
7
73476505
MAIN PLATE, COUPLER ASM, 18-16, 102"
1
139.6 lbm
8
73476506
ANGLE, COUPLER PLATE ASS'LY, 18-16
2
37.9 lbm
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


def test_mac_bom_item_part_qty_layout_eleven_pieces():
    """73476004-style: ITEM / PART / DESCRIPTION / QTY / WEIGHT → 8 PNs / 11 pcs."""
    bom = extract_pdf_bom_weights(text=_BOM_73476004)
    assert bom["method"] == "pdf_bom_qty"
    assert bom["part_number_count"] == 8
    assert bom["piece_count"] == 11
    assert bom["assembly_weight_lb"] == 281.0
    by_part = {r["part_no"]: r for r in bom["bom_rows"]}
    assert by_part["73000567"]["qty"] == 2 and by_part["73000567"]["unit_weight_lb"] == 7.8
    assert by_part["73476506"]["qty"] == 2 and by_part["73476506"]["unit_weight_lb"] == 37.9
    assert by_part["73476505"]["unit_weight_lb"] == 139.6
    expected = [
        12.5,
        7.8,
        7.8,
        3.5,
        32.8,
        12.3,
        12.3,
        28.1,
        139.6,
        37.9,
        37.9,
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


def test_estimate_assembly_weight_quotes_from_lom_xlsx(tmp_path: Path):
    """Quote path reads the written LOM.xlsx — not extract JSON."""
    from tests.test_bom_table import _KYLE_102728_1, _write_lom_pdf

    data_rows = [
        [str(qty), item, pn, desc] for item, qty, pn, desc in _KYLE_102728_1
    ]
    pdf = tmp_path / "Time 102728- Weldment.pdf"
    _write_lom_pdf(
        pdf,
        ["QTY", "ITEM", "PART NO.", "DESCRIPTION"],
        data_rows,
        title="WELDMENT, PLATFORM  102728-1  TIME MANUFACTURING",
    )
    result = estimate_assembly_weight([], notes=[], pdf_path=pdf)
    pdf_bom = result.get("pdf_bom") or result.get("bom") or {}
    assert pdf_bom.get("source") == "lom_xlsx"
    assert pdf_bom.get("lom_xlsx") == f"{pdf.stem}-LOM.xlsx"
    assert int(result.get("piece_count") or 0) == 97
    assert int(result.get("part_number_count") or 0) == 51
    by_item = {str(r.get("item")): r for r in (pdf_bom.get("rows") or [])}
    assert int(by_item["A"]["qty"]) == 1
    assert by_item["A"]["part_no"] == "460200"
    assert int(by_item["BB"]["qty"]) == 2
    assert by_item["BB"]["part_no"] == "102727-4"


def test_weight_unread_qty_stays_zero_not_one(monkeypatch):
    """Unread qty 0 must not become 1 in the quote weight rows."""
    from quote_core.bom import BomResult, BomRow

    def fake_quote(**_kwargs):
        return BomResult(
            rows=[
                BomRow(
                    item="A",
                    qty=0,
                    part_no="460200",
                    description="RAIL",
                    unit_weight_lb=10.0,
                    source="lom_xlsx",
                ),
                BomRow(
                    item="BB",
                    qty=2,
                    part_no="102727-4",
                    description="TUBE, ROUND",
                    unit_weight_lb=5.0,
                    source="lom_xlsx",
                ),
            ],
            method="table_lom_xlsx",
            lom_xlsx="102728-1-LOM.xlsx",
        )

    monkeypatch.setattr("quote_core.bom.quote_bom_from_drawing", fake_quote)
    result = estimate_assembly_weight([], notes=[])
    by_pn = {r.get("part_no"): r for r in result["part_weights"]}
    assert by_pn["460200"]["qty"] == 0
    assert by_pn["102727-4"]["qty"] == 2
    assert result["pdf_bom"]["source"] == "lom_xlsx"
