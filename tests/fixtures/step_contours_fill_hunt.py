"""STEP Contours fill hunt — repo + fixtures only. Fill stays locked.

Live STEP Contours mints are PAUSED. Do not remint / PATCH leftovers
(14327-5 / c5cd8689, 14327-8 / 1cd941c6, Q10329 / 14327-3 / 75f07c2b,
Q10330 / 21841-1 / aed89628, Q10331 / 14327-1 / 5e72fe39,
Q10332 / ZZ-DEL-wrong-org-Time, 35136-1 / 8973f890,
28898-1 / 28772-1 / 14327-18 / 15911-9 / 21839-1 empty-InternalData Time STEPs,
GSB20570006 / afee7458 Sprout 1.1 empty-InternalData outside Time pick, …).
Q10333 / H.6.38 / b5f56ac3 is a Contours PASS protect — never remint /
PATCH / ZZ-DEL. Q10336 / f73dd116 and Q10339 / 76cecc73 Cad→Finish
leftovers match Q10333 finished Contours (NumberOfContours=1 / OCC=0
expected / bends=8) — protect; soft-pass labels were stage notes.
Q10344 / 55f12530 Kyle UI control PASS leftover (Cad + 0.1875 inch
→ Contours fill → Finish) — never remint / PATCH / ZZ-DEL. invent=false.
Q10346 / d859a239 / B80510901 Sprout main plate Contours PASS
(outside H.6.38; Cad + 0.0598 inch → Contours fill → Finish) —
never remint / PATCH. invent=false.
Q10348 / 1defeed8 / H.16.70 Safe Cave Contours PASS
(outside H.6.38; Cad + 0.1875 inch → Contours fill → Finish) —
never remint / PATCH. invent=false.
Q10349 / c4394006 / D.H.30.96 Safe Cave Contours PASS
(outside H.6.38; Cad + 0.1875 inch → Contours fill → Finish) —
never remint / PATCH. invent=false.
Q10351 / 0c62fce9 / H.8.38 Safe Cave Contours PASS
(outside H.6.38; Cad + inches → Contours fill → Finish) —
never remint / PATCH. invent=false.
Q10354 / 7881d4b3 / D.H.38.96 Safe Cave Contours FAIL leftover
(Cad selector + 0.1875 in set, finished ProductType part;
NumberOfContours unavailable / Contours PASS not proven) —
same empty-InternalData Contours-FAIL class as Q10334 / Q10335.
Never remint / PATCH. invent=false. Not Q10349 / D.H.30.96 PASS.
Q10356 / 05bee105 / V.20.78 Safe Cave Contours FAIL leftover
(Cad selector + 0.1875 in set, finished ProductType part;
NumberOfContours missing / Contours PASS not proven) —
same Contours-FAIL class as Q10354 / D.H.38.96.
Never remint / PATCH. invent=false.
Q10358 / 34328-1 Time keep-grid prove leftover (tip 4cc4481):
keep_grid_via=live, Cad×3, inches on kids, FileList InternalData
empty after explode — Finish refused. Not grid-loss. Hypothesis
that Data/GetBorderSize fill Contours is discarded. Never remint
Q10358. Do not forbid 34328-1 (PO may remint the PN). invent=false.
Q10359 / 34328-FFE CoS leftover (tip ffe210e): keep_grid_via=live,
Cad×3, inches-on-kids, re-GET CadImport/Data copied_n=0,
InternalData empty 2/2 → EXEC_FAIL. UpdateData / contour editor
Done is not a safe multi-kid fill (#DXFEdit + Q10355 wipe).
Blocked on Sectura /part/create t.List. Never remint Q10359.
Do not forbid 34328-1. invent=false.
Do not gate unlock on OCC≥1. Never invent Contours / InternalData.

createAllParts still has no intervening CadImport/UI XHR. This follow-up
exhausted the alternate-path hypotheses below. Kyle Loom (original):
Adjust Properties defaults ProductType to Component; plate STEP Contours
fill after Component→Cad (live PASS Q10333 / b5f56ac3 / H.6.38 Safe
Cave — Cad / Contours=1 / 8 bends + Profile / Laser Bay1 / UC 176.96).
Protect that quote forever; never remint /
PATCH / ZZ-DEL (0759273 ZZ-DEL-fail narrative is reversed). Automation
writes API/kendo ProductType=100 + SetPartMode 0 plus POST
/Part/UpdateItemType ItemType=Cad (live Q10335 mouse dropdown
classify XHR, status 200). Cad classify ≠ Contours fill
(H638-CADPLATE / 5e7bfc0b, Q10334 / e2683a3f, Q10335 / bcff1a24
Contours 0; QuoteItem_Read Data:[] lost CAD row before Finish —
ZZ-DEL). Still refuse Finish if Contours/InternalData stay empty
after UpdateItemType. UpdateItemType is classify; Contours fill
may still need Finish or further calls.
``LIVE_PART_CREATE_TLIST_BIND`` is None.
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
    MULTI_KID_CONTOURS_BLOCKED_ON_SECTURA,
    MULTI_KID_CONTOURS_SUPPORT_ASK,
    MULTI_KID_SAFE_CONTOURS_FILL,
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
    "kyle_loom_component_to_cad": True,
    "kyle_loom_cad_set_via": "api_kendo_producttype_100_setpartmode_0_updateitemtype_cad",
    "q10333_component_to_cad_proof": True,
    "multi_kid_safe_fill": MULTI_KID_SAFE_CONTOURS_FILL,
    "multi_kid_blocked_on_sectura": MULTI_KID_CONTOURS_BLOCKED_ON_SECTURA,
    "multi_kid_support_ask": MULTI_KID_CONTOURS_SUPPORT_ASK,
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
        "Q10336",
        "Q10339",
        "Q10344",
        "Q10346",
        "B80510901",
        "Q10348",
        "H.16.70",
        "Q10349",
        "D.H.30.96",
        "Q10351",
        "H.8.38",
        "Q10354",
        "D.H.38.96",
        "Q10356",
        "V.20.78",
        "Q10358",
        "Q10359",
        "H638-CADPLATE",
        "Q10334",
        "Q10335",
        "28898-1",
        "28772-1",
        "14327-18",
        "15911-9",
        "21839-1",
        "GSB20570006",
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
                "GetDXFData is not in the bundle (404). POST "
                "/Part/UpdateItemType is dropdown classify (Q10335), "
                "not FileList InternalData fill. No other /part/* "
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
        {
            "id": "quote_item_edit",
            "call": "/quote/ItemEdit",
            "fn": None,
            "ruled_out": True,
            "why": (
                "Named on live Q10336 after AddItem_DXFFiles. Post-Finish "
                "navigation. No body keys restated — probe path only, "
                "no invented payload. Not Contours fill. Mid-wizard "
                "probe still useful for NumberOfContours 0→1."
            ),
        },
        {
            "id": "get_border_size",
            "call": "/Quote/GetBorderSize",
            "fn": None,
            "ruled_out": True,
            "why": (
                "Q10335/Q10336 thickness companion. Q10336 named "
                "Thickness_Units=inch only. Method / other keys not "
                "restated. Proven-keys probe; do not invent Thickness/ID. "
                "Not invent fill."
            ),
        },
        {
            "id": "multi_kid_keep_grid_data_getbordersize_not_fill",
            "call": "GET /CadImport/Data + /Quote/GetBorderSize after keep-grid Cad+inches",
            "fn": None,
            "ruled_out": True,
            "why": (
                "Q10358 / 34328-1 keep-grid prove (tip 4cc4481): "
                "keep_grid_via=live, live_grid_n=3, Cad×3 after "
                "SetPartMode/UpdateItemType, inches on kids. FileList "
                "InternalData empty after explode — Finish refused. "
                "Hypothesis that single-plate fires Data/GetBorderSize "
                "as Contours fill is discarded: automation apply_grid "
                "never POSTs those (single or multi); overlay GET Data "
                "is copy-if-nonempty before and after Cad+inches; "
                "GetBorderSize is thickness companion (Q10335 Contours 0; "
                "21839-1 full trail still empty). Single-plate PASSes "
                "Q10344/46/48/49/51 fill after Kyle UI Cad+inches in "
                "Adjust Properties — keep-grid skips that page_fn to "
                "avoid the Q10355 wipe. invent=false."
            ),
        },
        {
            "id": "multi_kid_updatedata_editor_done_not_safe_fill",
            "call": "POST /CadImport/UpdateData (editor Done / UpdateDXF)",
            "fn": "UpdateDXF",
            "ruled_out": True,
            "why": (
                "Q10359 / 34328-FFE CoS (tip ffe210e): keep_grid_via=live, "
                "Cad×3, inches-on-kids, re-GET CadImport/Data copied_n=0, "
                "InternalData empty 2/2 → EXEC_FAIL. invent=false. ZZ-DEL. "
                "Hypothesis that Kyle Contours fill is a non-destructive "
                "CadImport/UpdateData or contour editor Done is discarded: "
                "UpdateDXF requires #DXFEdit + WebGLCADDisp.dataGroup; "
                "ItemList is ID/Index/visible/attr/color — not InternalData; "
                "Kyle gold Loom classify→Finish never opens #DXFEdit; "
                "opening editDXFFile / select / editCell / #but_dxf is the "
                "Q10355 wipe. Named box HARs (mouse-cad-click/finish, "
                "mid-wizard, kyle-har, h638 control, 34328 ffe210e prove) "
                "are not on this VM/Dropbox; in-repo restatements mined — "
                "still no InternalData fill XHR. Single-plate PASSes "
                "Q10344/46/48/49/51 fill "
                "after Kyle UI Adjust Properties page_fn (HAR unrecorded); "
                "keep-grid skips that page_fn. CLASSIFY_FINISH_INTERNALDATA_FILL "
                "stays None. No safe multi-kid fill. Blocked on Sectura "
                "POST /part/create t.List InternalData+ImageString."
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
