"""Cad dropdown vs automation classify — Contours fill stays locked.

In-repo QuoteOrderEdit / CadImport JS has no named XHR that fills
FileList Contours / InternalData when ProductType changes to Cad.

Cited handlers beyond SetPartMode / ProductType=100:
  SetPartMode          POST /CadImport/SetPartMode {ID, PartMode}
  kendo row.set        local grid fields (ProductType 100, FileType Cad)
  UpdateData           editor close ItemList ID/Index/visible/attr/color
  UpdateDataNext       editor-only UpdateDXF_LoadNew
  ConvertTo / SetUnits units on #gridDXF — not Contours
  GetPerimeterAndWeight #gridPDF / Stock_X/Y perimeter
  OnAddDXFClick        copies #gridDXFParts as-is

Live leftovers after Cad-for-plate (ce2514f):
  5e7bfc0b H638-CADPLATE — SetPartMode 0 + ProductType 100 Cad:1,
    InternalData empty, Finish refuse
  e2683a3f Q10334 — kendo Cad/100 + 0.1875 in + Laser-Bay1,
    Contours still empty

Human Kyle on Q10333 / b5f56ac3: real Component→Cad dropdown +
thickness + Finish → Contours=1 PASS. That click's extra XHRs are
not in fixtures. invent=false. Next: DevTools of Kyle's real
dropdown click (method/path/request keys + Contours emptiness).
"""

from __future__ import annotations

from typing import Any

from secturafab.cadimport_js import (
    CLASSIFY_FINISH_INTERNALDATA_FILL,
    SET_PART_MODE_PATH,
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
    "kendo_row_set_fills_contours": False,
    "human_dropdown_fills_contours": True,
    "human_dropdown_reproduced": False,
    "next": "devtools_kyle_component_to_cad_dropdown_xhrs",
    "never_remint": (
        "H638-CADPLATE",
        "Q10334",
        "Q10333",
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
                "Human dropdown on Q10333 filled Contours. Gap is the "
                "uncaptured click XHRs — not a named fill we can fire."
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
                "Finish copies, does not fill."
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
                "Sectura XHR. Chrome leftover already set 0.1875 in + "
                "Laser-Bay1; Contours stayed empty."
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
        and all(h.get("ruled_out") for h in gap["hypotheses"])
    )
