"""Q10359 / 34328-FFE CoS — blocked-on-Sectura after keep-grid Cad+inches.

Live tip ``ffe210e3edc7d8820c1afb7e09aabddd3c8e1a58`` (PR18 / PR35
fail-close): ``keep_grid_via=live``, Cad×3, inches-on-kids, re-GET
``/CadImport/Data`` ``copied_n=0``, FileList InternalData empty 2/2 →
EXEC_FAIL refuse Finish. invent=false. ZZ-DEL'd. Do not remint Q10359.

Do not forbid 34328-1 (PO may remint the PN). 34328-FFE is a probe
label, not a forever-protect PN.

## Single-plate Contours-good vs multi-kid empty InternalData

Single-plate Safe Cave PASSes Q10344/46/48/49/51 fill Contours after
**Kyle UI** Adjust Properties Cad+inches (page_fn / dropdown). Human
HAR for that fill is unrecorded (Q10333 / Q10344). Named single-plate
automation trail (Q10336) is Upload → Data → ``/part/create`` →
UpdateItemType → PartImage → GetBorderSize → AddItem_DXFFiles.
UpdateItemType is classify (Q10335 Contours still 0 before Finish).
GetBorderSize is a thickness companion. Finish copies #gridDXFParts
as-is. CLASSIFY_FINISH_INTERNALDATA_FILL stays None.

Multi-kid keep-grid (Q10355 wipe class) **skips** that Adjust
Properties page_fn: no ``row.set`` / select / editCell / ``#but_dxf``,
no page SetPartMode/UpdateItemType. Silent field writes + jquery.ajax
classify only. Cad+inches stick on live kids; re-GET Data is
copy-if-nonempty and copied nothing (Q10359).

## Hypothesis discarded: UpdateData / contour editor Done

``POST /CadImport/UpdateData`` is editor close (UpdateDXF) after
``#DXFEdit``. ItemList keys are ID/Index/visible/attr/color — not
InternalData. ``UpdateDataNext`` is editor Previous/Next
(PROVEN_EMPTY_PATHS). Kyle gold Loom is classify→Finish **without**
``#DXFEdit``. Opening editDXFFile / select / editCell / ``#but_dxf``
is the Q10355 ``#gridDXFParts`` wipe. Not a safe multi-kid fill.

## Safe automation fill

None. ``MULTI_KID_SAFE_CONTOURS_FILL`` is None. Blocked on Sectura:
return nonempty InternalData+ImageString on ``POST /part/create``
``t.List`` for weldment explode kids, or name a non-select /
non-editCell / non-``#but_dxf`` XHR that writes FileList InternalData
after Cad+inches. Do not invent Contours/InternalData.
"""

from __future__ import annotations

from typing import Any

from secturafab.website import (
    CAD_INTERNALDATA_EMPTY_AFTER_EXPLODE,
    MULTI_KID_CONTOURS_BLOCKED_ON_SECTURA,
    MULTI_KID_CONTOURS_SUPPORT_ASK,
    MULTI_KID_SAFE_CONTOURS_FILL,
    STEP_CAD_FINISH_HARD_GATE_EXEC_FAIL,
    STEP_CONTOURS_FILL_UNLOCKED,
    STEP_CONTOURS_MISSING_CALL,
    STEP_EXPLODE_NO_INTERNALDATA,
)

Q10359_34328_FFE_COS: dict[str, Any] = {
    "quote_number": "Q10359",
    "part_number": "34328-1",
    "probe_label": "34328-FFE",
    "customer": "Time Manufacturing Waco",
    "id_unknown": True,
    "quote_id": None,
    "live_probe_tip": "ffe210e3edc7d8820c1afb7e09aabddd3c8e1a58",
    "live_probe_tip_short": "ffe210e",
    "keep_grid_via": "live",
    "cad_after_setpartmode": 3,
    "cad_inches_on_kids": True,
    "cadimport_get_after_cad_inches": True,
    "cadimport_get_copied_n": 0,
    "internaldata_empty": "2/2",
    "internaldata_empty_after_explode": True,
    "finish_refused": True,
    "finish_why": CAD_INTERNALDATA_EMPTY_AFTER_EXPLODE,
    "step_explode_no_internaldata": STEP_EXPLODE_NO_INTERNALDATA,
    "exec_fail": STEP_CAD_FINISH_HARD_GATE_EXEC_FAIL,
    "missing_call": STEP_CONTOURS_MISSING_CALL,
    "invent": False,
    "invent_contours": False,
    "invent_internaldata": False,
    "fill_unlocked": STEP_CONTOURS_FILL_UNLOCKED,
    "safe_fill": MULTI_KID_SAFE_CONTOURS_FILL,
    "blocked_on_sectura": MULTI_KID_CONTOURS_BLOCKED_ON_SECTURA,
    "support_ask": MULTI_KID_CONTOURS_SUPPORT_ASK,
    "unlocks_automation_contours_fill": False,
    "hypothesis_updatedata_editor_done_is_safe_fill": False,
    "hypothesis_discarded": True,
    "classify_finish_internaldata_fill": None,
    "single_plate_pass_contrast": (
        "Q10344",
        "Q10346",
        "Q10348",
        "Q10349",
        "Q10351",
    ),
    "single_plate_fill_via": "kyle_ui_adjust_properties_page_fn_cad_inches",
    "single_plate_fill_har": None,
    "keep_grid_skips_page_fn": True,
    "not_grid_loss": True,
    "not_q10355_wipe": True,
    "destructive_row_set_select_editcell_but_dxf": False,
    "zz_del": True,
    "zz_del_number": "ZZ-DEL-Q10359",
    "do_not_remint_quote_number": True,
    "do_not_forbid_part_number": True,
    "do_not_patch": True,
}


def q10359_34328_ffe_cos() -> dict[str, Any]:
    """Read-only Q10359 CoS. No invented InternalData. No safe fill."""
    out = dict(Q10359_34328_FFE_COS)
    out["single_plate_pass_contrast"] = tuple(
        Q10359_34328_FFE_COS["single_plate_pass_contrast"]
    )
    return out


def q10359_single_vs_multi_xhr_diff() -> dict[str, Any]:
    """Named XHR/UI split. invent=false — no payloads."""
    return {
        "invent": False,
        "single_plate_kyle_ui_pass": {
            "quotes": list(Q10359_34328_FFE_COS["single_plate_pass_contrast"]),
            "after_cad_inches": "Contours fill observed in Adjust Properties",
            "via": "kyle_ui_adjust_properties_page_fn",
            "har": None,
            "named_automation_trail": (
                "/CadImport/UploadItem_DXFFiles",
                "/CadImport/Data",
                "/part/create",
                "/Part/UpdateItemType",
                "/part/PartImage",
                "/Quote/GetBorderSize",
                "/Quote/AddItem_DXFFiles",
            ),
            "updateitemtype_fills_contours": False,
            "getbordersize_fills_contours": False,
            "apply_grid_page_fn": True,
        },
        "multi_kid_keep_grid": {
            "quotes": ("Q10358", "Q10359"),
            "after_cad_inches": "InternalData still empty; copied_n=0",
            "via": "silent_fields_plus_jquery_ajax",
            "apply_grid_page_fn": False,
            "skips": (
                "page_fn SetPartMode",
                "page_fn UpdateItemType",
                "row.set",
                "select",
                "editCell",
                "#but_dxf",
                "POST /CadImport/UpdateData",
                "POST /CadImport/UpdateDataNext",
            ),
            "reget_data": "copy-if-nonempty",
            "safe_fill": None,
        },
        "updatedata_editor_done": {
            "path": "/CadImport/UpdateData",
            "fn": "UpdateDXF",
            "requires": ("#DXFEdit", "WebGLCADDisp.dataGroup"),
            "itemlist_keys": ("ID", "Index", "visible", "attr", "color"),
            "writes_internaldata": False,
            "kyle_gold_opens_dxfedit": False,
            "safe_on_multi_kid": False,
            "wipe_class": "Q10355",
        },
    }
