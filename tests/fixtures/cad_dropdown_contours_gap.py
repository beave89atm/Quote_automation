"""Cad dropdown vs automation classify — Contours fill stays locked.

Live Q10335 mouse capture named the dropdown classify XHR:
  POST /Part/UpdateItemType — Component→Cad click, status 200
  Also /part/PartImage, /Quote/GetBorderSize on thickness
  Contours still 0 before Finish

UpdateItemType is dropdown classify. Contours fill may still need
Finish or further calls. invent=false.

Cited handlers beyond SetPartMode / ProductType=100:
  SetPartMode          POST /CadImport/SetPartMode {ID, PartMode}
  UpdateItemType       POST /Part/UpdateItemType {ID, ItemType}
  kendo row.set        local grid fields (ProductType 100, FileType Cad)
  UpdateData           editor close ItemList ID/Index/visible/attr/color
  UpdateDataNext       editor-only UpdateDXF_LoadNew
  ConvertTo / SetUnits units on #gridDXF — not Contours
  GetPerimeterAndWeight #gridPDF / Stock_X/Y perimeter
  GetBorderSize        thickness companion (Q10335) — not Contours
  OnAddDXFClick        copies #gridDXFParts as-is

Live leftovers after Cad-for-plate:
  5e7bfc0b H638-CADPLATE — SetPartMode 0 + ProductType 100 Cad:1,
    InternalData empty, Finish refuse
  e2683a3f Q10334 — kendo Cad/100 + 0.1875 in + Laser-Bay1,
    Contours still empty
  bcff1a24 Q10335 — mouse UpdateItemType 200, Contours 0 before Finish;
    QuoteItem_Read Data:[] lost CAD row; ZZ-DEL.
  f73dd116 Q10336 — mouse UpdateItemType then Finish; Cad+Laser
    leftover. Finished NumberOfContours=1 matches Q10333; OCC=0
    expected; bends=8. Soft-pass labels were stage notes.
  76cecc73 Q10339 — EOD STP Cad→Finish leftover. Finished
    NumberOfContours=1 matches Q10333; OCC=0 expected; Laser Bay1 /
    UC 64.25 / unit price 176.96.

Human Kyle on Q10333 / b5f56ac3: real Component→Cad dropdown +
thickness + Finish → NumberOfContours=1 PASS. Finished Q10336 /
Q10339 match that Contours signal. Classify XHR is named
(UpdateItemType). Invent Contours fill stays locked. Do not gate
unlock on OCC≥1.
"""

from __future__ import annotations

from typing import Any

from secturafab.cadimport_js import (
    CLASSIFY_FINISH_INTERNALDATA_FILL,
    GET_BORDER_SIZE_PATH,
    SET_PART_MODE_PATH,
    UPDATE_ITEM_TYPE_BODY_KEYS,
    UPDATE_ITEM_TYPE_PATH,
)
from secturafab.website import STEP_CONTOURS_FILL_UNLOCKED

CAD_DROPDOWN_CONTOURS_FILL = None

CAD_CLASSIFY_NEQ_CONTOURS_FILL = True

CAD_DROPDOWN_GAP: dict[str, Any] = {
    "fill_unlocked": STEP_CONTOURS_FILL_UNLOCKED,
    "cad_dropdown_contours_fill": CAD_DROPDOWN_CONTOURS_FILL,
    "classify_finish_internaldata_fill": CLASSIFY_FINISH_INTERNALDATA_FILL,
    "cad_classify_neq_contours_fill": CAD_CLASSIFY_NEQ_CONTOURS_FILL,
    "unlocks_automation_contours_fill": False,
    "invent": False,
    "fail_close": True,
    "set_part_mode_path": SET_PART_MODE_PATH,
    "set_part_mode_keys": ("ID", "PartMode"),
    "update_item_type_path": UPDATE_ITEM_TYPE_PATH,
    "update_item_type_keys": UPDATE_ITEM_TYPE_BODY_KEYS,
    "update_item_type_is_classify_xhr": True,
    "update_item_type_fills_contours": False,
    "get_border_size_path": GET_BORDER_SIZE_PATH,
    "kendo_row_set_fills_contours": False,
    "human_dropdown_fills_contours": True,
    "human_dropdown_reproduced": False,
    "human_dropdown_classify_xhr": UPDATE_ITEM_TYPE_PATH,
    "next": "finish_or_further_calls_after_updateitemtype",
    "never_remint": (
        "H638-CADPLATE",
        "Q10334",
        "Q10333",
        "Q10335",
        "Q10336",
        "Q10339",
    ),
    "hypotheses": (
        {
            "id": "native_select_vs_kendo_set",
            "call": None,
            "ruled_out": True,
            "why": (
                "In-repo QuoteOrderEdit snippets have no native <select> "
                "ProductType change handler. Chrome kendo row.set + "
                "SetPartMode 0 live-failed on Q10334 / e2683a3f "
                "(Cad/100 + 0.1875 in + Laser-Bay1, Contours empty). "
                "Human dropdown classify XHR is POST /Part/UpdateItemType "
                "(Q10335 status 200). Contours still 0 before Finish."
            ),
        },
        {
            "id": "update_item_type_classify",
            "call": "POST /Part/UpdateItemType",
            "fn": "UpdateItemType",
            "ruled_out": True,
            "why": (
                "Live Q10335 mouse Component→Cad fires POST "
                "/Part/UpdateItemType 200. QuoteOrderEdit ItemType field "
                "(GetPDFData / onInternalDataChange). Wired keys ID + "
                "ItemType=Cad only — capture did not restate keys. "
                "Contours still 0 before Finish. Classify XHR, not fill."
            ),
        },
        {
            "id": "price_list_manual_entry_cad",
            "call": None,
            "fn": "GetPDFData PriceListID",
            "ruled_out": True,
            "why": (
                "PriceListID / PriceListItemID are #gridPDF Image Files "
                "GetPDFData keys. No CadImport/UI XHR named Manual "
                "Entry→Cad writes FileList InternalData."
            ),
        },
        {
            "id": "details_form_save",
            "call": None,
            "ruled_out": True,
            "why": (
                "No Details-save XHR in QuoteOrderEdit snippets writes "
                "FileList InternalData. UpdateData editor close is "
                "ID/Index/visible/attr/color — not Contours."
            ),
        },
        {
            "id": "finish_fills_contours",
            "call": "POST /Quote/AddItem_DXFFiles",
            "fn": "OnAddDXFClick",
            "ruled_out": True,
            "why": (
                "OnAddDXFClick copies #gridDXFParts as-is. Leftovers "
                "that Finished with empty InternalData stayed empty. "
                "Q10333 Contours=1 was after human dropdown+thickness; "
                "Finish copies, does not fill. Q10335 Contours 0 before "
                "Finish — fill may still need Finish or further calls."
            ),
        },
        {
            "id": "thickness_unit_conversion",
            "call": "POST /CadImport/ConvertTo",
            "fn": "ConvertTo / SetUnits / sanitize_bind_thickness_inches",
            "ruled_out": True,
            "why": (
                "ConvertTo is units on #gridDXF (PROVEN_EMPTY_PATHS). "
                "SetUnits is query-only. Local inch sanitize is not a "
                "Sectura XHR. Q10335 thickness also fired /part/PartImage "
                "+ /Quote/GetBorderSize; Contours stayed 0 before Finish."
            ),
        },
        {
            "id": "quote_item_edit_post_finish",
            "call": "/quote/ItemEdit",
            "fn": None,
            "ruled_out": True,
            "why": (
                "Live Q10336 named /quote/ItemEdit after "
                "AddItem_DXFFiles. Post-Finish navigation. "
                "Not Contours fill. No request keys restated. "
                "Do not invent an ItemEdit body."
            ),
        },
    ),
}


def cad_dropdown_contours_gap() -> dict[str, Any]:
    """Read-only gap. Does not unlock Contours fill. Never invents payloads."""
    out = dict(CAD_DROPDOWN_GAP)
    out["hypotheses"] = [dict(h) for h in CAD_DROPDOWN_GAP["hypotheses"]]
    return out


def cad_dropdown_contours_gap_exhausted() -> bool:
    """True when every dropdown hypothesis is ruled out and fill stays locked."""
    gap = cad_dropdown_contours_gap()
    return (
        gap["fill_unlocked"] is False
        and gap["cad_dropdown_contours_fill"] is None
        and gap["cad_classify_neq_contours_fill"] is True
        and gap["unlocks_automation_contours_fill"] is False
        and gap["invent"] is False
        and gap["update_item_type_fills_contours"] is False
        and all(h.get("ruled_out") for h in gap["hypotheses"])
    )
