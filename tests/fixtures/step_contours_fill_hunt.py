"""STEP Contours fill hunt — repo + fixtures only. Fill stays locked.

Live STEP Contours mints are PAUSED. Do not remint / PATCH leftovers
(14327-5 / c5cd8689, 14327-8 / 1cd941c6, Q10329 / 14327-3 / 75f07c2b,
Q10330 / 21841-1 / aed89628, Q10331 / 14327-1 / 5e72fe39,
Q10333 / H.6.38 / b5f56ac3, Q10332 / ZZ-DEL-wrong-org-Time,
35136-1 / 8973f890, …).
Never invent Contours / InternalData.

createAllParts still has no intervening CadImport/UI XHR. This follow-up
exhausted the alternate-path hypotheses below. Unlock remains a Kyle
manual Finish that shows Contours≥1 (DevTools emptiness capture) or
Sectura support naming the fill. ``LIVE_PART_CREATE_TLIST_BIND`` is None.
"""

from __future__ import annotations

from typing import Any

from secturafab.cadimport_js import (
    CLASSIFY_FINISH_INTERNALDATA_FILL,
    EXPLODE_DOCREATE_INTERNALDATA_FILL,
    PROVEN_EMPTY_PATHS,
    STEP_CONTOURS_MISSING_CALL,
    STEP_CONTOURS_NO_EXTRA_XHR,
)
from secturafab.website import (
    STEP_CONTOURS_FILL_UNLOCKED,
    STEP_CONTOURS_NOT_FILL_PATHS,
    STEP_CONTOURS_UNLOCK_REQUIRES,
)

# Hypotheses checked in QuoteOrderEdit fixtures + leftover HAR notes.
# ruled_out: no evidence the call writes FileList InternalData+ImageString
# before AddItem_DXFFiles. Do not POST these as a Finish substitute.
STEP_CONTOURS_FILL_HUNT: dict[str, Any] = {
    "fill_unlocked": STEP_CONTOURS_FILL_UNLOCKED,
    "invent": False,
    "fail_close": True,
    "missing_call": STEP_CONTOURS_MISSING_CALL,
    "no_extra_cadimport_xhr": STEP_CONTOURS_NO_EXTRA_XHR,
    "classify_finish_internaldata_fill": CLASSIFY_FINISH_INTERNALDATA_FILL,
    "explode_docreate_internaldata_fill": EXPLODE_DOCREATE_INTERNALDATA_FILL,
    "unlock_requires": STEP_CONTOURS_UNLOCK_REQUIRES,
    "never_remint": (
        "14327-5",
        "14327-8",
        "35136-1",
        "Q10329",
        "14327-3",
        "Q10330",
        "21841-1",
        "Q10331",
        "14327-1",
        "Q10332",
        "Q10333",
    ),
    "angles": (
        {
            "id": "cadimport_update_data",
            "call": "POST /CadImport/UpdateData",
            "fn": "UpdateDXF (editor close)",
            "ruled_out": True,
            "why": (
                "Editor close after #DXFEdit. ItemList is ID/Index/visible/"
                "attr/color — not InternalData. Not classify→Finish. "
                "cad_updatedxf_loadnew.json close path."
            ),
        },
        {
            "id": "cadimport_update_data_next",
            "call": "POST /CadImport/UpdateDataNext",
            "fn": "UpdateDXF_LoadNew",
            "ruled_out": True,
            "why": (
                "Editor-only (#DXFEdit + CADType===DXF + WebGLCADDisp). "
                "Not called from createAllParts / DoCreateDXFParts / "
                "OnAddDXFClick. Live 34887-1 FileList 0. PROVEN_EMPTY_PATHS."
            ),
        },
        {
            "id": "cadimport_data",
            "call": "GET /CadImport/Data",
            "fn": None,
            "ruled_out": True,
            "why": (
                "Copy-if-nonempty by SID/ID/FileID only. Leftover 35136-1 "
                "OpenContourCount=0; 14327-5 / 28769-1 bindable=false. "
                "Empty GET is documentary — not a fill XHR."
            ),
        },
        {
            "id": "cadimport_caddata",
            "call": "GET /CadImport/CADData",
            "fn": None,
            "ruled_out": True,
            "why": (
                "Same copy-if-nonempty. Length/Width/WebGL is editor preview. "
                "14327-5 / 28769-1 bindable=false. Do not invent Contours."
            ),
        },
        {
            "id": "convert_to",
            "call": "POST /CadImport/ConvertTo",
            "fn": "ConvertTo(n)",
            "ruled_out": True,
            "why": (
                "Units on selected #gridDXF rows (IDList + Units). "
                "Live 34887-1 JSON List 200 FileList 0. PROVEN_EMPTY_PATHS. "
                "Not flatten / DXF convert / explode."
            ),
        },
        {
            "id": "flatten_unfold",
            "call": None,
            "fn": "Unfold / HasUnfold / Unfolded / DetectBendLines / RemoveTitleBlock",
            "ruled_out": True,
            "why": (
                "QuoteOrderEdit create_parts.js + leftover 21785-2: Unfold "
                "hits=0. Detect*/Remove* POST IDList but do not create child "
                "rows or write InternalData. No flatten/ToDXF path cited."
            ),
        },
        {
            "id": "part_star",
            "call": "GET /part/PartImage",
            "fn": None,
            "ruled_out": True,
            "why": (
                "QuoteOrderEdit explode is only POST /part/create "
                "(DoCreateDXFParts). /part/PartImage is preview. "
                "GetDXFData is not in the bundle (404). No other /part/* "
                "helper writes FileList InternalData."
            ),
        },
        {
            "id": "quote_helpers",
            "call": "GET /Quote/DXFInternal",
            "fn": None,
            "ruled_out": True,
            "why": (
                "Freestyle only. OnAddDXFClick copies #gridDXFParts as-is "
                "and does not fill InternalData."
            ),
        },
        {
            "id": "pdf_image_files_parallel",
            "call": "GET /Quote/PDFInternal + PDFGetData / onInternalDataChange",
            "fn": "AddNewPDFFeature / UpdatePerimeterWeight",
            "ruled_out": True,
            "why": (
                "Image Files Contours are #gridPDF hole features "
                "(PDFInternal HTML → PDFGetData JSON). GetPerimeterAndWeight "
                "is #gridPDF / Stock_X/Y perimeter — not CAD FileList "
                "InternalData. Do not copy PDFGetData onto STEP FileList."
            ),
        },
    ),
}


def step_contours_fill_hunt() -> dict[str, Any]:
    """Read-only hunt. Does not unlock Contours fill. Never invents payloads."""
    out = dict(STEP_CONTOURS_FILL_HUNT)
    out["angles"] = [dict(a) for a in STEP_CONTOURS_FILL_HUNT["angles"]]
    out["not_fill_paths"] = sorted(STEP_CONTOURS_NOT_FILL_PATHS)
    out["proven_empty_paths"] = sorted(PROVEN_EMPTY_PATHS)
    return out


def step_contours_fill_hunt_exhausted() -> bool:
    """True when every hunt angle is ruled out and fill stays locked."""
    hunt = step_contours_fill_hunt()
    return (
        hunt["fill_unlocked"] is False
        and hunt["invent"] is False
        and all(a.get("ruled_out") for a in hunt["angles"])
    )
