"""Table-driven regression for locked Time drawings.

Adding a 12th weldment: one ``LomGold`` / classify / desc row in
``tests/fixtures/time_gold.py``, then rebuild ``tests/fixtures/lom/``.
No live Sectura writes.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from quote_core.bom import normalize_part_no
from quote_core.bom_config import resolve_bom_config
from quote_core.customer_org import detect_organization
from quote_core.drawing_title import title_from_library_folder
from quote_core.lom_xlsx import extract_bom_from_lom_xlsx, normalize_opc_part
from quote_core.weld.takeoff import estimate_fitup_drivers
from secturafab.item_desc import (
    format_assembly_description,
    format_cad_description,
    format_component_description,
    format_linear_description,
    looks_like_drawing_sheet,
)
from secturafab.linear_ops import bind_linear_product_ids
from secturafab.pdf_assembly_ops import plan_weldment_lines
from secturafab.push import SecturaFabPushService, classify_sectura_item

from tests.fixtures.time_gold import (
    CLASSIFY_CASES,
    DESC_CASES,
    FIXTURE_DIR,
    LOM_GOLD,
    DASH_1001898,
    write_empty_l2_workbook,
    write_gold_workbook,
)


@pytest.fixture(scope="module", autouse=True)
def _gold_workbooks():
    for gold in LOM_GOLD:
        dest = FIXTURE_DIR / f"{gold.part_key}-LOM.xlsx"
        if not dest.is_file():
            write_gold_workbook(gold, dest)
    empty = FIXTURE_DIR / "empty-l2-LOM.xlsx"
    if not empty.is_file():
        write_empty_l2_workbook(empty)


@pytest.mark.parametrize("gold", LOM_GOLD, ids=[g.part_key for g in LOM_GOLD])
def test_locked_lom_counts(gold):
    path = FIXTURE_DIR / f"{gold.part_key}-LOM.xlsx"
    if not path.is_file():
        path = write_gold_workbook(gold)
    assert path.is_file()
    bom = extract_bom_from_lom_xlsx(path, bom_config="1")
    assert bom.method == "lom_xlsx", bom.notes
    got = {(r.part_no, r.qty) for r in bom.rows}
    want = set(gold.identity)
    assert got == want, sorted(got.symmetric_difference(want))
    assert bom.part_number_count == gold.pn, [f"{r.part_no}×{r.qty}" for r in bom.rows]
    assert bom.piece_count == gold.pcs, [f"{r.part_no}×{r.qty}" for r in bom.rows]
    by_pn = {r.part_no for r in bom.rows}
    for pn in gold.require_pn:
        assert pn in by_pn, f"missing locked PN {pn} in {gold.part_key}"
    for pn in gold.forbid_pn:
        assert pn not in by_pn, f"child table leaked {pn} into {gold.part_key}"
    for child in gold.empty_l2:
        assert any(f"empty L2 shell: {child}" in n for n in bom.notes), bom.notes
    assert not any("xl/xl/" in n for n in bom.notes)


def test_prefer_existing_lom_over_clip(tmp_path: Path):
    gold = next(g for g in LOM_GOLD if g.part_key == "1001898-1")
    lib = tmp_path / "Time" / "Pedestal Weldment - 1001898-1"
    lib.mkdir(parents=True)
    write_gold_workbook(gold, lib / "1001898-1-LOM.xlsx")
    from quote_core.bom import extract_bom

    pdf = tmp_path / "1001898.pdf"
    import fitz

    doc = fitz.open()
    doc.new_page()
    doc.save(pdf)
    doc.close()
    with patch("quote_core.bom.extract_bom_from_ocr_time_style") as ocr:
        bom = extract_bom(pdf, library_folder=lib, bom_config="1")
        ocr.assert_not_called()
    assert bom.part_number_count == 17
    assert bom.piece_count == 27


def test_1004747_dash_trap_title_not_folder():
    assert (
        resolve_bom_config(
            title="1004747",
            pdf_filename="1004747.pdf",
            library_folder=r"C:\drawings\Time\Weldment - 1004747-2",
            part_key="1004747-2",
        )
        == "1"
    )
    assert (
        resolve_bom_config(
            title="1004747-1",
            pdf_filename="1004747.pdf",
            library_folder=r"C:\drawings\Time\Weldment - 1004747-2",
        )
        == "1"
    )
    gold = next(g for g in LOM_GOLD if g.part_key == "1004747-1")
    path = FIXTURE_DIR / f"{gold.part_key}-LOM.xlsx"
    if not path.is_file():
        path = write_gold_workbook(gold)
    dash1 = extract_bom_from_lom_xlsx(path, bom_config="1")
    dash2 = extract_bom_from_lom_xlsx(path, bom_config="2")
    assert dash1.part_number_count == 14 and dash1.piece_count == 18
    assert dash2.piece_count != 18


def test_empty_clip_never_one_pc(tmp_path: Path):
    from quote_core.bom import extract_bom

    pdf = tmp_path / "empty-grid.pdf"
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((360, 40), "LIST OF MATERIAL", fontsize=12)
    page.insert_text((360, 70), "ITEM PART NO QTY", fontsize=10)
    doc.save(pdf)
    doc.close()
    with patch(
        "quote_core.lom_clip.clip_lom_grid_from_pdf",
        return_value=(
            [],
            [
                "LIST OF MATERIAL grid found on the drawing but clip produced "
                "0 rows — piece count unknown (needs_info); "
                "refusing whole-page OCR as takeoff truth"
            ],
            True,
        ),
    ), patch("quote_core.ocr.ocr_available", return_value=False):
        bom = extract_bom(pdf, library_folder=tmp_path, bom_config="1")
        drivers = estimate_fitup_drivers(
            {},
            [],
            pdf_path=pdf,
            library_folder=tmp_path,
            bom_config="1",
        )
    assert bom.method == "lom_clip_empty"
    assert bom.piece_count == 0
    assert drivers["needs_info"] is True
    assert drivers["part_count"] == 0
    assert drivers["part_count"] != 1


def test_empty_l2_shell_is_flagged():
    path = FIXTURE_DIR / "empty-l2-LOM.xlsx"
    if not path.is_file():
        path = write_empty_l2_workbook()
    bom = extract_bom_from_lom_xlsx(path, bom_config="1")
    assert any("empty L2 shell" in n for n in bom.notes)
    assert "99999-1" in {r.part_no for r in bom.rows}


def test_job91_opc_path_still_normalized():
    assert normalize_opc_part("/xl/worksheets/sheet1.xml") == "xl/worksheets/sheet1.xml"
    assert "xl/xl/" not in normalize_opc_part("/xl/worksheets/sheet1.xml")


def test_letter_prefix_and_ocr_item_letter():
    assert normalize_part_no("P904225-1") == "P904225-1"
    assert normalize_part_no("S 80054-1") == "S80054-1"
    assert normalize_part_no("A35121-1") == "35121-1"
    assert normalize_part_no("1004611-DWG") == "1004611-DWG"
    assert normalize_part_no("460200") == "460200"
    assert normalize_part_no("94560") == "94560"
    assert normalize_part_no("351211") == "35121-1"


@pytest.mark.parametrize("pn,desc,want", CLASSIFY_CASES, ids=[c[0] for c in CLASSIFY_CASES])
def test_classify_locked_rows(pn, desc, want):
    assert classify_sectura_item(f"{pn} {desc}") == want


def test_1001898_classify_counts():
    got = {pn: classify_sectura_item(f"{pn} {desc}") for _i, _q, pn, desc in DASH_1001898}
    assert sum(1 for c in got.values() if c == "Cad") == 5
    assert sum(1 for c in got.values() if c == "Linear") == 5
    assert sum(1 for c in got.values() if c == "Component") == 7


@pytest.mark.parametrize("case", DESC_CASES, ids=[c["part_no"] + ":" + c["kind"] for c in DESC_CASES])
def test_kyle_description_formats(case):
    kind = case["kind"]
    if kind == "cad" or kind == "cad_sheet":
        got = format_cad_description(case["part_no"], **case["kwargs"])
    elif kind == "linear":
        got = format_linear_description(case["part_no"], **case["kwargs"])
    elif kind == "component":
        got = format_component_description(case["kwargs"]["name"], part_no=case["part_no"])
    elif kind == "assembly":
        got = format_assembly_description(case["part_no"], case["kwargs"]["title"])
    else:
        raise AssertionError(kind)
    if "want" in case:
        assert got == case["want"]
    for token in case.get("forbid") or ():
        assert token not in got
    if case.get("contains"):
        assert case["contains"] in got
    assert got != case["part_no"]


def test_pdf_sheet_outline_rejected():
    assert looks_like_drawing_sheet(22.0, 28.5) is True
    assert looks_like_drawing_sheet(22.0, 29.3) is True
    assert looks_like_drawing_sheet(10.0, 9.0) is False
    assert looks_like_drawing_sheet(7.5, 10.0) is False


def test_time_org_and_pedestal_title():
    folder = (
        r"C:\Users\Kyle\Kannon Manufacturing Inc\Fort Worth - Documents"
        r"\Engineering\Customer Drawings\Time\Pedestal Weldment - 1001898-1"
    )
    assert detect_organization(library_folder=folder) == "Time Manufacturing Waco"
    assert title_from_library_folder(folder, part_key="1001898-1") == "PEDESTAL WELDMENT"
    assert (
        format_assembly_description("1001898-1", "PEDESTAL WELDMENT")
        == "1001898-1 - PEDESTAL WELDMENT"
    )


def test_plan_1001898_lines_are_not_bare_pn():
    rows = [
        {"part_no": pn, "qty": qty, "description": desc} for _i, qty, pn, desc in DASH_1001898
    ]
    planned = plan_weldment_lines(rows)
    assert len(planned) == 17
    counts = {"Cad": 0, "Linear": 0, "Component": 0}
    for line in planned:
        counts[line["category"]] += 1
        assert line["Description"] != line["part_no"]
        assert "22" not in line["Description"]
        if line["category"] == "Linear":
            assert line["ProductType"] == 10
        elif line["category"] == "Component":
            assert line["ProductType"] == 200
        else:
            assert line["ProductType"] == 100
    assert counts == {"Cad": 5, "Linear": 5, "Component": 7}


def test_new_line_item_laser_pack_is_not_grafted():
    """21667-1 class: Kyle New Line Item pack is Laser/Drafting/Deburr/Setup/Load."""
    from secturafab.profile_ops import _PROFILE_OP_TEMPLATES

    calcs = [o.get("CalculatorName") for o in _PROFILE_OP_TEMPLATES]
    assert calcs == ["Laser", "Drafting", "Laser-Setup", "Sheet Loading", "Deburr"]


def test_linear_bind_sets_product_type_10_and_product_id():
    catalog = [
        {
            "ID": "pid-rct",
            "ProductName": "RCT2 12X1 12X.065-A513",
            "ShapeName": "Mechanical Tube",
            "MaterialGrade": "A513",
            "Dim1": 1.5,
            "Active": True,
        }
    ]
    client = MagicMock()
    client.get_json.return_value = {
        "ItemList": [
            {
                "ID": "L1",
                "Description": "12689-1 TUBE",
                "Category": "Linear",
                "ProductType": 100,
                "ProductName": "should-clear",
                "Length": 44.375,
            },
            {
                "ID": "L2",
                "Description": "12368-2 TUBE",
                "ItemType": "Linear",
                "ProductType": 100,
                "Length": 12.25,
            },
        ]
    }
    save = MagicMock()
    save.status_code = 200
    client.request.return_value = save
    bind_linear_product_ids(client, "qid", material="A513", catalog=catalog)
    payload = client.request.call_args.kwargs["json"]
    for item in payload["ItemList"]:
        assert item["ProductType"] == 10
        assert item["IsLinear"] is True
        assert item["Machine"] == "Saw"
        assert item.get("ProductID") == "pid-rct"
        assert item.get("ProductName") in {None, ""}
        assert item["Description"] != item["ID"]
        assert not any(
            str(o.get("OperationName") or "") == "Saw"
            for o in (item.get("OperationCostList") or [])
        )


def test_pdf_plate_21667_flat_is_drawing_math_not_sheet():
    desc = format_cad_description(
        "21667-1", thickness=0.375, grade="100K", width_in=10, length_in=9
    )
    assert desc == '21667-1 - 3/8" 100K 10 in x 9 in'
    assert looks_like_drawing_sheet(10, 9) is False


@pytest.mark.parametrize("part_key", ["21678-1", "21676-1"])
@pytest.mark.parametrize(
    "cookie,expect_finish",
    [
        ("", False),
        ("ASP.NET_SessionId=test", True),
    ],
    ids=["cookie_missing", "cookie_present"],
)
def test_step_weldment_finish_or_no_graft(
    tmp_path: Path, part_key: str, cookie: str, expect_finish: bool
):
    pdf = tmp_path / f"{part_key}.pdf"
    stp = tmp_path / f"{part_key}.STEP"
    pdf.write_bytes(b"%PDF")
    stp.write_bytes(b"ISO")
    client = MagicMock()
    client.config.website_cookie = cookie
    client.request.return_value.status_code = 200
    client.get_json.return_value = {
        "QuoteNumber": part_key,
        "ItemCount": 2,
        "ItemList": [
            {"Description": "21680 HOSE GUARD", "ProductType": 10, "IsLinear": True},
            {"Description": "21679 PLATE", "ProductType": 100},
        ],
    }
    service = SecturaFabPushService(client=client)
    finish = MagicMock(return_value=["Finish CAD"])
    with patch.object(service, "finish_cad_files", finish), patch.object(
        service, "nest_after_finish", return_value=["Nest"]
    ), patch.object(service, "upload_drawings_quote_request", return_value="qr"), patch.object(
        service, "create_quote", return_value="qid"
    ), patch.object(
        service, "allocate_quote_number", return_value=part_key
    ), patch.object(
        service, "quick_add_cad", return_value={"ok": True}
    ), patch.object(
        service, "apply_item_categories", return_value=[]
    ), patch(
        "secturafab.push.ensure_assembly_root", return_value=[]
    ), patch(
        "secturafab.push.relink_assembly_children", return_value=[]
    ), patch(
        "secturafab.push.ensure_purchased_components", return_value=[]
    ), patch(
        "secturafab.push.find_purchased_part_keys", return_value={}
    ), patch(
        "secturafab.push.refresh_bom_rows_for_push", return_value=([], [])
    ), patch(
        "secturafab.push.apply_bom_quantities", return_value=[]
    ), patch(
        "secturafab.push.ensure_laser_profile_ops"
    ) as graft, patch(
        "secturafab.push.ensure_weld_ops", return_value=[]
    ), patch(
        "secturafab.push.finalize_quote_ops", return_value=[]
    ) as finalize, patch(
        "secturafab.push.ensure_imperial_item_units", return_value=[]
    ), patch(
        "secturafab.push.extract_assembly_description", return_value="KNUCKLE WELDMENT"
    ):
        result = service.push_job(
            title=part_key,
            pdf_filename=f"{part_key}.pdf",
            pdf_path=pdf,
            stp_path=stp,
            takeoff={"library": {"part_key": part_key}},
            times={"weld_minutes": 10, "total_inches": 20},
            job_id=41,
        )
    assert result.ok is True
    graft.assert_not_called()
    if expect_finish:
        finish.assert_called_once()
    else:
        finish.assert_not_called()
        assert any("cookie not set" in n for n in (result.notes or []))
    if finalize.called:
        assert finalize.call_args.kwargs.get("attach_profile") in {None, False}


def test_cookie_less_1001898_attach_profile_false(tmp_path: Path):
    pdf = tmp_path / "1001898.pdf"
    pdf.write_bytes(b"%PDF")
    lib = tmp_path / "Time" / "Pedestal Weldment - 1001898-1"
    lib.mkdir(parents=True)
    client = MagicMock()
    client.config.website_cookie = ""
    client.get_json.return_value = {
        "QuoteNumber": "1001898-1",
        "ItemCount": 18,
        "ItemList": [{"Description": "1001898-1 - PEDESTAL WELDMENT", "ProductType": 300}],
    }
    service = SecturaFabPushService(client=client)
    with patch.object(service, "upload_drawings_quote_request", return_value="qr"), patch.object(
        service, "create_quote", return_value="qid"
    ) as create_q, patch.object(
        service, "allocate_quote_number", return_value="1001898-1"
    ), patch(
        "secturafab.push.refresh_bom_rows_for_push",
        return_value=(
            [{"part_no": pn, "qty": qty, "description": desc} for _i, qty, pn, desc in DASH_1001898],
            [],
        ),
    ), patch(
        "secturafab.push.ensure_weld_ops", return_value=[]
    ), patch(
        "secturafab.push.finalize_quote_ops", return_value=[]
    ) as finalize, patch(
        "secturafab.pdf_assembly_ops.build_pdf_only_assembly",
        return_value=["Skipped grafted Profile"],
    ), patch(
        "secturafab.push.apply_quote_organization",
        return_value=["Set Organization: Time Manufacturing Waco"],
    ), patch(
        "secturafab.push.ensure_laser_profile_ops"
    ) as graft:
        result = service.push_job(
            title="1001898",
            pdf_filename="1001898.pdf",
            pdf_path=pdf,
            stp_path=None,
            takeoff={"library": {"part_key": "1001898-1", "folder": str(lib)}},
            times={"weld_minutes": 0, "total_inches": 0},
            job_id=91,
        )
    assert result.ok is True
    graft.assert_not_called()
    assert finalize.call_args.kwargs.get("attach_profile") in {None, False}
    assert create_q.call_args.kwargs.get("description") == "1001898-1 - PEDESTAL WELDMENT"


def test_fixture_dir_has_checked_in_workbooks():
    missing = [g.part_key for g in LOM_GOLD if not (FIXTURE_DIR / f"{g.part_key}-LOM.xlsx").is_file()]
    assert not missing, f"rebuild fixtures for {missing}"
