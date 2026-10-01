"""STEP stock classify: thin plate vs 15911-style flat-bar (not Cad Contours)."""

from __future__ import annotations

from unittest.mock import MagicMock

from secturafab.push import (
    SecturaFabPushService,
    apply_step_stock_category,
    classify_sectura_item,
    explode_kid_part_tokens,
)
from secturafab.step_classify import (
    STOCK_FLAT_BAR,
    STOCK_ROUND_BAR,
    STOCK_STRONG_PLATE,
    all_cartesian_bbox,
    classify_step_text,
    contours_path_allowed,
    looks_like_round_bar_stock,
    robust_step_bbox,
    row_looks_like_round_bar_stock,
    score_step_stock,
)
from secturafab.website import (
    _cad_plate_row_for_finish_gate,
    overlay_classified_row,
    product_type_is_cad,
    step_cad_finish_hard_gate,
)
from tests.fixtures.step_flat_bar_15911 import (
    FLAT_BAR_15911_DIMS,
    H638_LIKE_PLATE_DIMS,
    flat_bar_15911_step_text,
    h638_like_plate_step_text,
    live_15911_bar_vs_plate,
)


def test_score_h638_like_thin_plate_is_strong_plate():
    assert score_step_stock(H638_LIKE_PLATE_DIMS) == STOCK_STRONG_PLATE
    assert contours_path_allowed(STOCK_STRONG_PLATE) is True
    assert classify_sectura_item("H.6.38 PLATE", stock_dims=H638_LIKE_PLATE_DIMS) == "Cad"
    assert classify_sectura_item("H.6.38", stock_dims=H638_LIKE_PLATE_DIMS) == "Cad"


def test_score_15911_flat_bar_is_linear_not_strong_plate():
    dump = live_15911_bar_vs_plate()
    assert dump["invented"] is False
    assert score_step_stock(FLAT_BAR_15911_DIMS) == STOCK_FLAT_BAR
    assert score_step_stock(FLAT_BAR_15911_DIMS) != STOCK_STRONG_PLATE
    assert contours_path_allowed(STOCK_FLAT_BAR) is False
    assert classify_sectura_item("15911-14", stock_dims=FLAT_BAR_15911_DIMS) == "Linear"
    assert classify_sectura_item("15911-7", stock_dims=FLAT_BAR_15911_DIMS) == "Linear"
    assert classify_sectura_item("10289-5", stock_dims=FLAT_BAR_15911_DIMS) == "Linear"
    assert apply_step_stock_category("Cad", STOCK_FLAT_BAR, "15911-14") == "Linear"
    assert apply_step_stock_category("Cad", STOCK_FLAT_BAR, "H.6.38 PLATE") == "Cad"


def test_robust_bbox_ignores_hole_axis_cartesian_points():
    text = flat_bar_15911_step_text()
    parsed = classify_step_text(text)
    box = parsed["box"]
    assert box is not None
    assert abs(box[0] - 42.5) < 0.05
    assert abs(box[1] - 5.0) < 0.05
    assert abs(box[2] - 1.75) < 0.05
    assert parsed["source"] in {"vertex", "plane"}
    assert parsed["kind"] == STOCK_FLAT_BAR
    assert parsed["category"] == "Linear"
    assert parsed["contours_path_allowed"] is False
    inflated = all_cartesian_bbox(text)
    assert inflated is not None
    assert inflated[0] > 50 or inflated[1] > 8 or inflated[2] > 3
    robust = robust_step_bbox(text)
    assert robust["all_cartesian_box"] != robust["box"]
    assert score_step_stock(inflated) != STOCK_STRONG_PLATE or parsed["kind"] == STOCK_FLAT_BAR


def test_h638_like_step_stays_strong_plate():
    parsed = classify_step_text(h638_like_plate_step_text())
    assert parsed["kind"] == STOCK_STRONG_PLATE
    assert parsed["category"] == "Cad"
    assert parsed["contours_path_allowed"] is True
    box = parsed["box"]
    assert box is not None
    assert abs(box[2] - 0.1875) < 0.02


def test_classify_cadimport_flat_bar_rejects_cad_contours(tmp_path):
    stp = tmp_path / "15911-14.STEP"
    stp.write_text(flat_bar_15911_step_text(), encoding="ascii")
    rows = [
        {
            "SourceDataID": "bar-1",
            "ID": "id-15911-14",
            "Name": "15911-14",
            "ProductType": "Component",
            "Qty": 1,
            "ErrorStatus": 0,
            "InternalData": "",
        }
    ]
    classified, notes = SecturaFabPushService(client=MagicMock()).classify_cadimport_rows(
        rows,
        default_material="A36",
        default_thickness="0.25",
        bom_rows=[],
        library={},
        extra_pdfs=None,
        qty=1,
        part_key="15911-14",
        cad_files=[stp],
    )
    assert len(classified) == 1
    kid = classified[0]
    assert kid["Category"] == "Linear"
    assert kid["FileType"] == "Linear"
    assert kid["PartMode"] == 1
    assert product_type_is_cad(kid.get("ProductType")) is False
    assert kid["ProductType"] != 100
    assert _cad_plate_row_for_finish_gate(kid) is False
    assert step_cad_finish_hard_gate(classified) is None
    blob = " ".join(notes)
    assert "flat_bar" in blob
    assert "Cad: 0" in blob or "Linear: 1" in blob


def test_explode_kid_part_tokens_reads_31454_from_hook_name():
    toks = explode_kid_part_tokens("HOOK BOOM REST-7742_31454-1")
    assert "31454-1" in toks
    assert toks[0] == "31454-1"


def test_rd_bar_lom_string_is_linear_not_cad_contours():
    """Kyle/CoS 2026-09-14: RD BAR CR 1018 / 1/2 DIA → Long/Linear.

    Name-only HOOK stays Cad (Q10368 leftover). Drawing stock string
    and 1/2 DIA geometry must not take Cad Contours. invent=false.
    """
    assert looks_like_round_bar_stock("RD BAR CR 1018 / 1/2 DIA") is True
    assert looks_like_round_bar_stock("ROUND BAR 1/2 DIA") is True
    assert looks_like_round_bar_stock("BAR ROUND 1/2 DIA.(STRIKER)") is True
    assert looks_like_round_bar_stock("1/2 DIA") is True
    assert looks_like_round_bar_stock("HOOK BOOM REST-7742_31454-1") is False
    assert looks_like_round_bar_stock("1/4 PLATE A36 1/2 DIA HOLES") is False
    assert classify_sectura_item("RD BAR CR 1018 / 1/2 DIA") == "Linear"
    assert classify_sectura_item(
        "HOOK BOOM REST-7742_31454-1 RD BAR CR 1018 / 1/2 DIA"
    ) == "Linear"
    assert classify_sectura_item("HOOK BOOM REST-7742_31454-1", 0.5) == "Cad"
    assert classify_sectura_item("34329 BOOM SUPPORT", 0.25) == "Cad"
    assert score_step_stock((12.0, 0.5, 0.5)) == STOCK_ROUND_BAR
    assert contours_path_allowed(STOCK_ROUND_BAR) is False
    assert apply_step_stock_category("Cad", STOCK_ROUND_BAR, "31454-1") == "Linear"
    assert apply_step_stock_category("Cad", STOCK_ROUND_BAR, "34329 PLATE") == "Cad"


def test_classify_cadimport_rd_bar_kid_is_linear_not_contours(tmp_path):
    from quote_core.part_materials import PartMaterial

    rows = [
        {
            "SourceDataID": "hook-1",
            "ID": "id-31454-1",
            "Name": "HOOK BOOM REST-7742_31454-1",
            "ProductType": "Component",
            "Qty": 1,
            "ErrorStatus": 0,
            "InternalData": "",
        },
        {
            "SourceDataID": "plate-1",
            "ID": "id-34329",
            "Name": "34329 BOOM SUPPORT",
            "ProductType": "Component",
            "Qty": 1,
            "ErrorStatus": 0,
            "InternalData": "",
        },
    ]
    hook_pm = PartMaterial(
        part_key="31454-1",
        material_key="a36",
        material="A36",
        thickness_in=0.5,
        source="RD BAR stock 'RD BAR CR 1018 / 1/2 DIA'",
        raw_grade="CR 1018",
        raw_thickness="1/2 DIA",
    )
    plate_pm = PartMaterial(
        part_key="34329",
        material_key="a36",
        material="A36",
        thickness_in=0.25,
        source="MATERIAL block (1/4 / A36)",
    )
    from unittest.mock import patch

    with patch(
        "quote_core.part_materials.build_part_material_map",
        return_value={"31454-1": hook_pm, "34329": plate_pm},
    ):
        classified, notes = SecturaFabPushService(
            client=MagicMock()
        ).classify_cadimport_rows(
            rows,
            default_material="A36",
            default_thickness="0.25",
            bom_rows=[
                {
                    "part_no": "31454-1",
                    "description": "RD BAR CR 1018 / 1/2 DIA",
                },
                {"part_no": "34329", "description": "BOOM SUPPORT"},
            ],
            library={},
            extra_pdfs=None,
            qty=1,
            part_key="34328-1",
        )
    hook = next(k for k in classified if "31454" in str(k.get("Name") or ""))
    plate = next(k for k in classified if "34329" in str(k.get("Name") or ""))
    assert hook["Category"] == "Linear"
    assert hook["FileType"] == "Linear"
    assert product_type_is_cad(hook.get("ProductType")) is False
    assert _cad_plate_row_for_finish_gate(hook) is False
    assert plate["Category"] == "Cad"
    assert _cad_plate_row_for_finish_gate(plate) is True
    blob = " ".join(notes)
    assert "Linear: 1" in blob
    assert "Cad: 1" in blob


def test_contours_gate_skips_linear_rd_bar_kids():
    """Plate Cad Contours≥1; RD BAR Linear kids must not EXEC_FAIL at 0."""
    from secturafab.website import (
        STEP_CAD_FINISH_HARD_GATE_EXEC_FAIL,
        step_cad_post_finish_contours_gate,
    )

    plate = {
        "ProductType": 100,
        "Category": "Cad",
        "Name": "34329 BOOM SUPPORT",
        "Material": "A36",
        "Thickness": 0.25,
        "Thickness_Units": "inch",
        "NumberOfContours": 1,
    }
    hook = {
        "ProductType": 10,
        "Category": "Linear",
        "FileType": "Linear",
        "Name": "31454-1",
        "Description": "RD BAR CR 1018 / 1/2 DIA",
        "Material": "A36",
        "Thickness": 0.5,
        "Thickness_Units": "inch",
        "NumberOfContours": 0,
    }
    why = step_cad_post_finish_contours_gate(
        {"TreeListData": [hook, plate, {**hook, "Name": "31454-1 B"}]}
    )
    assert why is None
    leftover_cad_hooks = {
        "TreeListData": [
            {
                **plate,
                "Name": "HOOK BOOM REST-7742_31454-1",
                "Thickness": 0.5,
                "NumberOfContours": 0,
            },
            plate,
            {
                **plate,
                "Name": "HOOK BOOM REST-7742_31454-1",
                "Thickness": 0.5,
                "NumberOfContours": 0,
            },
        ]
    }
    leftover = step_cad_post_finish_contours_gate(leftover_cad_hooks)
    assert leftover is not None
    assert STEP_CAD_FINISH_HARD_GATE_EXEC_FAIL in leftover
    assert row_looks_like_round_bar_stock(hook) is True


def test_classify_cadimport_h638_plate_stays_cad():
    rows = [
        {
            "SourceDataID": "h638",
            "ID": "id-h638",
            "Name": "H.6.38 PLATE",
            "ProductType": "Component",
            "Thickness": "0.1875",
            "Thickness_Units": "inch",
            "Qty": 1,
            "ErrorStatus": 0,
            "InternalData": "",
        }
    ]
    classified, notes = SecturaFabPushService(client=MagicMock()).classify_cadimport_rows(
        rows,
        default_material="A36",
        default_thickness="0.1875",
        bom_rows=[],
        library={},
        extra_pdfs=None,
        qty=1,
        part_key="H.6.38",
        stock_dims=H638_LIKE_PLATE_DIMS,
    )
    kid = classified[0]
    assert kid["Category"] == "Cad"
    assert kid["ProductType"] == 100
    overlaid = overlay_classified_row(rows[0], category="Cad", thickness="0.1875")
    assert overlaid["ProductType"] == 100
    assert "Cad: 1" in " ".join(notes)


def test_plate_sheet_component_blocks_finish_cad_inch_allowed():
    """Plate/sheet still ProductType Component cannot Finish.

    Kyle 2026-09-12: Adjust Properties defaults Component; laser
    plate/sheet must be Cad before Finish. Cad + inch thickness
    still proceeds. Noun ``part`` and purchased Component do not
    block. invent=false — do not invent Contours or flat L/W.
    """
    from secturafab.chrome_cdp import _APPLY_GRID_PART_MODES_JS, _PAGE_FINISH_JS
    from secturafab.website import (
        cad_finish_notes_refuse_additem_dxf,
        kendo_filelist_for_finish,
        page_dxf_finish_skip_why,
        step_cad_live_product_type_hard_gate,
    )

    component_plate = {
        "Name": "H.6.38 PLATE",
        "ID": "id-h638",
        "FileID": "file-h638",
        "SourceDataID": "src-h638",
        "FileType": "Cad",
        "ItemType": "Cad",
        "Category": "Cad",
        "PartMode": 0,
        "ProductType": "Component",
        "Material": "A36",
        "Thickness": "0.1875",
        "Thickness_Units": "inch",
        "InternalData": "server-stamped",
    }
    cad_inch = {**component_plate, "ProductType": 100}
    why = step_cad_finish_hard_gate([component_plate])
    assert why is not None
    assert "Component" in why
    assert "invent" in why.lower()
    assert "Contours" in why
    assert step_cad_finish_hard_gate([cad_inch]) is None
    assert page_dxf_finish_skip_why([component_plate]) == "producttype_still_component"
    assert page_dxf_finish_skip_why([cad_inch]) is None
    blocked = kendo_filelist_for_finish([component_plate], from_datasource=True)
    assert blocked["should_finish"] is False
    assert blocked["finish_why"] == "producttype_still_component"
    allowed = kendo_filelist_for_finish([cad_inch], from_datasource=True)
    assert allowed["should_finish"] is True
    assert allowed["finish_why"] == ""
    assert step_cad_live_product_type_hard_gate([component_plate], [cad_inch]) == why
    assert step_cad_live_product_type_hard_gate([cad_inch], [cad_inch]) is None
    assert step_cad_live_product_type_hard_gate([], [cad_inch]) is None
    part = {**cad_inch, "ProductType": "part", "ProductTypeName": "part"}
    assert step_cad_live_product_type_hard_gate([part], [cad_inch]) is None
    sheet_live = {
        "Name": "SIDE SHEET",
        "ID": "id-sheet",
        "ProductType": 200,
        "FileType": "Component",
        "Category": "Component",
        "ItemType": "Component",
    }
    sheet_cad = {
        **sheet_live,
        "FileType": "Cad",
        "Category": "Cad",
        "ItemType": "Cad",
        "PartMode": 0,
        "ProductType": 100,
        "Material": "A36",
        "Thickness": "0.25",
        "Thickness_Units": "inch",
    }
    sheet_why = step_cad_live_product_type_hard_gate([sheet_live], [sheet_cad])
    assert sheet_why is not None
    assert "Component" in sheet_why
    assert cad_finish_notes_refuse_additem_dxf([sheet_why]) == sheet_why
    bolt = {
        "Name": "1/2-13 HEX BOLT",
        "FileType": "Component",
        "Category": "Component",
        "ProductType": 200,
    }
    assert step_cad_live_product_type_hard_gate([bolt], [cad_inch]) is None
    assert step_cad_finish_hard_gate([bolt, cad_inch]) is None
    assert "producttype_still_component" in _PAGE_FINISH_JS
    assert "cadPlateStillComponent" in _PAGE_FINISH_JS
    assert "producttype_still_component" in _APPLY_GRID_PART_MODES_JS


def test_plate_sheet_left_component_refuses_finish_before_page_native():
    """A plate/sheet kid left as Component cannot Finish.

    The old lock only fired when the row was already Cad and
    ProductType was still Component. A page-native STEP/PDF kid
    whose ItemType stayed Component slipped through. Bar/tube
    stays Linear. Purchased hardware and plate over 3/4 in may
    stay Component. invent=false — no Contours, thickness, or price.
    """
    import json
    import shutil
    import subprocess
    import textwrap

    from secturafab.chrome_cdp import _PAGE_FINISH_JS, _PAGE_PDF_FINISH_JS
    from secturafab.website import (
        kendo_filelist_for_finish,
        page_dxf_finish_skip_why,
        plate_sheet_left_component_blocks_finish,
        step_cad_finish_hard_gate,
    )

    sheet = {
        "Name": "SIDE SHEET",
        "PartName": "SIDE SHEET",
        "ID": "id-sheet",
        "FileID": "file-sheet",
        "SourceDataID": "src-sheet",
        "FileType": "Component",
        "ItemType": "Component",
        "Category": "Component",
        "PartMode": 2,
        "ProductType": 200,
        "Material": "A36",
        "Thickness": "0.25",
        "Thickness_Units": "inch",
        "Qty": 1,
        "ErrorStatus": 0,
        "InternalData": "server-stamped",
    }
    why = plate_sheet_left_component_blocks_finish([sheet])
    assert why is not None
    assert "producttype_still_component" in why
    assert "Contours" in why
    assert "invent" in why.lower()
    assert page_dxf_finish_skip_why([sheet]) == "producttype_still_component"
    blocked = kendo_filelist_for_finish([sheet], from_datasource=True)
    assert blocked["should_finish"] is False
    assert blocked["finish_why"] == "producttype_still_component"
    hard = step_cad_finish_hard_gate([sheet])
    assert hard is not None
    assert "producttype_still_component" in hard

    cad = {
        **sheet,
        "FileType": "Cad",
        "ItemType": "Cad",
        "Category": "Cad",
        "PartMode": 0,
        "ProductType": 100,
    }
    assert plate_sheet_left_component_blocks_finish([cad]) is None
    assert page_dxf_finish_skip_why([cad]) is None

    gusset = {**sheet, "Name": "TRIANGLE GUSSET", "PartName": "TRIANGLE GUSSET"}
    assert plate_sheet_left_component_blocks_finish([gusset]) is not None

    tube = {
        **sheet,
        "Name": "BOOM TUBE",
        "PartName": "2X2X1/4 HSS TUBE",
        "ItemType": "Linear",
        "Category": "Linear",
        "FileType": "Linear",
        "PartMode": 1,
        "ProductType": 30,
    }
    assert plate_sheet_left_component_blocks_finish([tube]) is None
    assert page_dxf_finish_skip_why([tube]) is None
    tube_left = {
        **sheet,
        "Name": "BOOM TUBE",
        "PartName": "2X2X1/4 HSS",
        "ItemType": "Component",
        "Category": "Component",
        "FileType": "Component",
    }
    assert plate_sheet_left_component_blocks_finish([tube_left]) is None

    bolt = {**sheet, "Name": "1/2-13 HEX BOLT", "PartName": "HEX BOLT"}
    assert plate_sheet_left_component_blocks_finish([bolt]) is None
    assert page_dxf_finish_skip_why([bolt]) is None

    thick = {**sheet, "Name": "PEDESTAL BASE PLATE", "Thickness": "1.25"}
    assert plate_sheet_left_component_blocks_finish([thick]) is None

    flat_bar = {
        **sheet,
        "Name": "FLAT BAR",
        "PartName": "FLAT BAR 1/4 X 2",
        "ItemType": "Component",
        "Category": "Component",
        "FileType": "Component",
        "PartMode": 2,
        "ProductType": 200,
    }
    assert plate_sheet_left_component_blocks_finish([flat_bar]) is None

    pdf_plate = {
        "FileName": "cover-plate.pdf",
        "PartName": "COVER PLATE",
        "ItemType": "component",
        "ProductType": "prt_pdf",
        "ProductSubType": "prt_pdf",
        "Thickness": "0.25",
        "Thickness_Units": "inch",
    }
    assert plate_sheet_left_component_blocks_finish([pdf_plate]) is not None
    pdf_cad = {**pdf_plate, "ItemType": "cad", "ProductType": "prt_pdf"}
    assert plate_sheet_left_component_blocks_finish([pdf_cad]) is None

    def extract(js: str) -> str:
        start = js.index("function cadPlateStillComponent")
        brace = js.index("{", start)
        depth = 0
        for idx in range(brace, len(js)):
            if js[idx] == "{":
                depth += 1
            elif js[idx] == "}":
                depth -= 1
                if depth == 0:
                    return js[start : idx + 1]
        raise AssertionError("cadPlateStillComponent unclosed")

    step_fn = extract(_PAGE_FINISH_JS)
    pdf_fn = extract(_PAGE_PDF_FINISH_JS)
    assert step_fn == pdf_fn
    pre = _PAGE_PDF_FINISH_JS.index("var preGet = ensureGetPdfDataReady()")
    call = _PAGE_PDF_FINISH_JS.index(
        "cadPlateStillComponent(classifyRows)", pre
    )
    finish = _PAGE_PDF_FINISH_JS.index("var finishName = findFinishName()", pre)
    assert call < finish
    assert "producttype_still_component" in _PAGE_PDF_FINISH_JS[pre:finish]

    node = shutil.which("node")
    if not node:
        return
    script = textwrap.dedent(
        """
        const fs = require("fs");
        const fnSrc = fs.readFileSync(process.argv[2], "utf8");
        const cadPlateStillComponent = new Function(fnSrc + "; return cadPlateStillComponent;")();
        const sheet = {
          Name: "SIDE SHEET", ItemType: "Component", Category: "Component",
          FileType: "Component", PartMode: 2, ProductType: 200,
          Thickness: "0.25", Thickness_Units: "inch"
        };
        const cad = Object.assign({}, sheet, {
          ItemType: "Cad", Category: "Cad", FileType: "Cad",
          PartMode: 0, ProductType: 100
        });
        const gusset = Object.assign({}, sheet, {Name: "TRIANGLE GUSSET", PartName: "TRIANGLE GUSSET"});
        const tube = {
          Name: "BOOM TUBE", PartName: "2X2X1/4 HSS TUBE",
          ItemType: "Linear", PartMode: 1, ProductType: 30
        };
        const bolt = Object.assign({}, sheet, {Name: "1/2-13 HEX BOLT", PartName: "HEX BOLT"});
        const thick = Object.assign({}, sheet, {Name: "PEDESTAL BASE PLATE", Thickness: "1.25"});
        const flat = {
          Name: "FLAT BAR", PartName: "FLAT BAR 1/4 X 2",
          ItemType: "Component", Category: "Component", FileType: "Component",
          PartMode: 2, ProductType: 200
        };
        const pdf = {
          FileName: "cover-plate.pdf", PartName: "COVER PLATE",
          ItemType: "component", ProductType: "prt_pdf", Thickness: "0.25"
        };
        const out = {
          sheet: cadPlateStillComponent([sheet]),
          cad: cadPlateStillComponent([cad]),
          gusset: cadPlateStillComponent([gusset]),
          tube: cadPlateStillComponent([tube]),
          bolt: cadPlateStillComponent([bolt]),
          thick: cadPlateStillComponent([thick]),
          flat: cadPlateStillComponent([flat]),
          pdf: cadPlateStillComponent([pdf])
        };
        process.stdout.write(JSON.stringify(out));
        """
    )
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        fn_path = Path(tmp) / "cad_lock.js"
        run_path = Path(tmp) / "run.js"
        fn_path.write_text(step_fn, encoding="utf-8")
        run_path.write_text(script, encoding="utf-8")
        proc = subprocess.run(
            [node, str(run_path), str(fn_path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    assert proc.returncode == 0, proc.stderr
    got = json.loads(proc.stdout)
    assert got == {
        "sheet": True,
        "cad": False,
        "gusset": True,
        "tube": False,
        "bolt": False,
        "thick": False,
        "flat": False,
        "pdf": True,
    }
