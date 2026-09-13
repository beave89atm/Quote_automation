"""Time STEP empty InternalData after explode — separate from H.6.38.

Failed invent=false Finishes:
  28898-1  UpdateItemType Cad OK, InternalData empty, Finish refused
           (ID unknown; description-only)
  28772-1  UpdateItemType Cad OK, InternalData empty, Finish refused
           (ID unknown; description-only)
  14327-18 UpdateItemType Cad OK, InternalData empty, Finish refused
           (ID unknown; description-only)
  15911-9 / ef865b0f-66d2-404e-bff2-9ed1e7bf00ea @ 62f7a92
           UpdateItemType Cad OK, InternalData empty, Finish refused
           invent=false; ZZ-DEL-15911-9. Mid-wizard XHRs vs H.6.38
           not observed: CadImport/Data, PartImage, GetBorderSize.
  21839-1 / 1994392f-54a5-4245-80ee-a947fb07e3a7 @ bb4998a+
           UpdateItemType Cad OK, InternalData empty after explode,
           Finish refused invent=false; ZZ-DEL-21839-1. Full
           CadImport/Data + GetBorderSize + PartImage trail still
           empty (stronger than 15911-9: trail ran, still empty).

Same Sectura-side empty-InternalData class, outside Time pick:
  GSB20570006 / afee7458-6651-447e-ba1b-62c1c9c90ce8 Sprout 1.1
           (CoS hold) — empty InternalData after full Cad+wizard
           mid-wizard (11 parts), invent=false; ZZ-DEL-GSB20570006.
           Not a Time STEP. Do not invent Contours / InternalData.

Not the H.6.38 Contours-good family (Q10333 / Q10336 / Q10339 / Q10344
finished GET NumberOfContours=1). This class never reaches a
NumberOfContours≥1 GET because Finish is refused. Never remint /
PATCH Q10333 / Q10336 / Q10338 / Q10339 / Q10344 / golds.

Existing captures only — no invented InternalData payloads:
  28768-1 / 28708035  PartMode Cad + page Finish, InternalData null,
                      bar_flat, GET 0 Cad
  28769-1 / c146ce6d  t.List InternalData keys present / values empty,
                      CadImport Data+CADData bindable=false, Finish refused
  14327-5 / c5cd8689  /part/create n=1 InternalData empty 1/1,
                      ImageString preview-only, OCC empty/null
  14327-8 / 1cd941c6  same empty-InternalData refuse as 14327-5
  H638-CADPLATE / 5e7bfc0b  UpdateItemType/SetPartMode Cad OK,
                            InternalData empty, Finish refuse

Fail-closed wiring already in-repo (cad_filelist_refuses_additem_dxf /
cad_internaldata_empty_after_explode / step_explode_no_internaldata).
Named Cad→Finish XHR probe does not unlock fill. invent=false.
Never remint / PATCH. Do not invent InternalData.
"""

from __future__ import annotations

from typing import Any

from secturafab.cadimport_js import (
    CAD_FINISH_NAMED_XHR_SEQUENCE,
    GET_BORDER_SIZE_PATH,
    UPDATE_ITEM_TYPE_CAD,
    UPDATE_ITEM_TYPE_PATH,
)
from secturafab.website import (
    CAD_INTERNALDATA_EMPTY_AFTER_EXPLODE,
    STEP_CONTOURS_FILL_UNLOCKED,
    STEP_EXPLODE_NO_INTERNALDATA,
)

TIME_STEP_EMPTY_INTERNALDATA_PNS = (
    "28898-1",
    "28772-1",
    "14327-18",
    "15911-9",
    "21839-1",
)
TIME_STEP_EMPTY_INTERNALDATA_ID_UNKNOWN_PNS = (
    "28898-1",
    "28772-1",
    "14327-18",
)
TIME_STEP_EMPTY_INTERNALDATA_KNOWN_QUOTE_ID = (
    "ef865b0f-66d2-404e-bff2-9ed1e7bf00ea"
)
TIME_STEP_EMPTY_INTERNALDATA_KNOWN_QUOTE_ID_PREFIX = "ef865b0f"
TIME_STEP_EMPTY_INTERNALDATA_ZZ_DEL = "ZZ-DEL-15911-9"
TIME_STEP_EMPTY_INTERNALDATA_21839_QUOTE_ID = (
    "1994392f-54a5-4245-80ee-a947fb07e3a7"
)
TIME_STEP_EMPTY_INTERNALDATA_21839_QUOTE_ID_PREFIX = "1994392f"
TIME_STEP_EMPTY_INTERNALDATA_21839_ZZ_DEL = "ZZ-DEL-21839-1"
TIME_STEP_EMPTY_INTERNALDATA_MISSING_MID_WIZARD_XHRS = (
    "/CadImport/Data",
    "/part/PartImage",
    GET_BORDER_SIZE_PATH,
)
TIME_STEP_EMPTY_INTERNALDATA_FULL_TRAIL_XHRS = (
    "/CadImport/Data",
    GET_BORDER_SIZE_PATH,
    "/part/PartImage",
)

TIME_STEP_EMPTY_INTERNALDATA_PRIOR_CAPTURES = (
    "28768-1",
    "28769-1",
    "14327-5",
    "14327-8",
    "H638-CADPLATE",
)

TIME_STEP_EMPTY_INTERNALDATA: dict[str, Any] = {
    "invent": False,
    "unlocks_automation_contours_fill": False,
    "fill_unlocked": STEP_CONTOURS_FILL_UNLOCKED,
    "separate_from_h638_family": True,
    "h638_contours_good": ("Q10333", "Q10336", "Q10339", "Q10344"),
    "part_numbers": TIME_STEP_EMPTY_INTERNALDATA_PNS,
    "ids_restated": ("15911-9", "21839-1"),
    "id_unknown": True,
    "id_unknown_pns": TIME_STEP_EMPTY_INTERNALDATA_ID_UNKNOWN_PNS,
    "known_quote_id": TIME_STEP_EMPTY_INTERNALDATA_KNOWN_QUOTE_ID,
    "known_quote_id_prefix": TIME_STEP_EMPTY_INTERNALDATA_KNOWN_QUOTE_ID_PREFIX,
    "zz_del_number": TIME_STEP_EMPTY_INTERNALDATA_ZZ_DEL,
    "known_quote_id_21839": TIME_STEP_EMPTY_INTERNALDATA_21839_QUOTE_ID,
    "known_quote_id_prefix_21839": TIME_STEP_EMPTY_INTERNALDATA_21839_QUOTE_ID_PREFIX,
    "zz_del_number_21839": TIME_STEP_EMPTY_INTERNALDATA_21839_ZZ_DEL,
    "live_probe_tip": "62f7a92",
    "live_probe_tip_21839": "bb4998a",
    "missing_mid_wizard_xhrs_vs_h638": TIME_STEP_EMPTY_INTERNALDATA_MISSING_MID_WIZARD_XHRS,
    "missing_mid_wizard_xhrs_observed": False,
    "full_trail_xhrs": TIME_STEP_EMPTY_INTERNALDATA_FULL_TRAIL_XHRS,
    "full_trail_observed_still_empty": True,
    "update_item_type_path": UPDATE_ITEM_TYPE_PATH,
    "update_item_type_itemtype": UPDATE_ITEM_TYPE_CAD,
    "update_item_type_ok": True,
    "internaldata_empty_after_explode": True,
    "finish_refused": True,
    "finish_why": CAD_INTERNALDATA_EMPTY_AFTER_EXPLODE,
    "step_explode_no_internaldata": STEP_EXPLODE_NO_INTERNALDATA,
    "prior_captures": TIME_STEP_EMPTY_INTERNALDATA_PRIOR_CAPTURES,
    "named_cad_finish_xhr_sequence": CAD_FINISH_NAMED_XHR_SEQUENCE,
    "named_sequence_unlocks_fill": False,
    "do_not_remint": True,
    "do_not_patch": True,
    "hypotheses": (
        {
            "id": "server_explode_empty_tlist",
            "ruled_out": False,
            "from_captures": ("28769-1", "14327-5", "14327-8", "35136-1"),
            "why": (
                "POST /part/create t.List arrived with InternalData keys "
                "present and values empty (ImageString preview-only on "
                "28769-1 / 14327-5). QuoteOrderEdit createAllParts has no "
                "intervening fill XHR. Server explode returning empty "
                "InternalData is the miss. Do not invent a payload."
            ),
        },
        {
            "id": "update_item_type_does_not_fill_internaldata",
            "ruled_out": True,
            "from_captures": (
                "H638-CADPLATE",
                "Q10335",
                "28898-1",
                "15911-9",
                "21839-1",
            ),
            "why": (
                "UpdateItemType Cad is dropdown classify (Q10335 status "
                "200; H638-CADPLATE SetPartMode Cad:1). Live Time STEPs "
                "28898-1 / 28772-1 / 14327-18 / 15911-9 / 21839-1: "
                "classify OK, InternalData still empty, Finish refused. "
                "Classify ≠ fill."
            ),
        },
        {
            "id": "cadimport_get_copy_if_nonempty",
            "ruled_out": True,
            "from_captures": ("28769-1", "14327-5", "35136-1"),
            "why": (
                "GET /CadImport/Data and CADData copy-if-nonempty only. "
                "Leftover GETs were bindable=false (OCC 0 / empty/null). "
                "Empty GET is documentary — not a fill XHR."
            ),
        },
        {
            "id": "imagestring_preview_is_not_internaldata",
            "ruled_out": True,
            "from_captures": ("28768-1", "28769-1", "14327-5", "21785-2"),
            "why": (
                "Preview ImageString without nonempty InternalData "
                "refuses Finish (cad_filelist_refuses_additem_dxf). "
                "28768-1 page-Finished with InternalData null and GET "
                "0 Cad — confirms the skip."
            ),
        },
        {
            "id": "named_cad_finish_sequence_not_a_fill",
            "ruled_out": True,
            "from_captures": ("Q10336", "21839-1"),
            "why": (
                "Named Upload→Data→/part/create→UpdateItemType→"
                "PartImage→GetBorderSize→AddItem_DXFFiles→ItemEdit is "
                "probed fail-closed. Observing those paths does not "
                "write InternalData. Time STEPs that explode empty "
                "never reach AddItem_DXFFiles."
            ),
        },
        {
            "id": "not_h638_finished_get_contours_good",
            "ruled_out": True,
            "from_captures": ("Q10333", "Q10336", "Q10339", "Q10344"),
            "why": (
                "H.6.38 leftovers Finished with NumberOfContours=1 on "
                "v1 ItemList. Time STEPs 28898-1 / 28772-1 / 14327-18 "
                "/ 15911-9 / 21839-1 refused before Finish. Separate "
                "gate. Never remint / PATCH Q10333 / Q10336 / Q10338 "
                "/ Q10339 / Q10344."
            ),
        },
        {
            "id": "15911_9_missing_mid_wizard_xhrs",
            "ruled_out": True,
            "from_captures": ("15911-9",),
            "why": (
                "Live 15911-9 / ef865b0f @ 62f7a92: UpdateItemType Cad "
                "OK, InternalData empty, Finish refused invent=false. "
                "Mid-wizard XHRs vs H.6.38 not observed: "
                "/CadImport/Data, /part/PartImage, /Quote/GetBorderSize. "
                "Do not invent those calls. Never remint / PATCH "
                "Q10333 / Q10336 / Q10338 / Q10339 / Q10344 / golds."
            ),
        },
        {
            "id": "21839_1_full_trail_still_empty",
            "ruled_out": True,
            "from_captures": ("21839-1",),
            "why": (
                "Live 21839-1 / 1994392f @ bb4998a+: UpdateItemType "
                "Cad OK, InternalData empty after explode, Finish "
                "refused invent=false; ZZ-DEL-21839-1. Full "
                "CadImport/Data + GetBorderSize + PartImage trail "
                "still empty — stronger than 15911-9 (trail ran, "
                "still empty). Named mid-wizard XHRs do not fill "
                "explode-empty InternalData. Never remint / PATCH "
                "Q10333 / Q10336 / Q10338 / Q10339 / Q10344 / golds."
            ),
        },
        {
            "id": "sprout_gsb20570006_outside_time_pick",
            "ruled_out": True,
            "from_captures": ("GSB20570006",),
            "why": (
                "Live Sprout GSB20570006 / afee7458 CoS hold: empty "
                "InternalData after full Cad+wizard mid-wizard (11 "
                "parts), Finish refused invent=false; "
                "ZZ-DEL-GSB20570006. Same Sectura-side "
                "empty-InternalData class outside H.6.38 / Time pick. "
                "Do not invent Contours / InternalData. Never remint "
                "/ PATCH Q10333 / Q10336 / Q10338 / Q10339 / Q10344 / golds."
            ),
        },
    ),
}


def time_step_empty_internaldata_dig() -> dict[str, Any]:
    """Read-only dig. No invented InternalData. Does not unlock fill."""
    out = dict(TIME_STEP_EMPTY_INTERNALDATA)
    out["part_numbers"] = tuple(TIME_STEP_EMPTY_INTERNALDATA_PNS)
    out["ids_restated"] = tuple(TIME_STEP_EMPTY_INTERNALDATA["ids_restated"])
    out["id_unknown_pns"] = tuple(TIME_STEP_EMPTY_INTERNALDATA_ID_UNKNOWN_PNS)
    out["missing_mid_wizard_xhrs_vs_h638"] = tuple(
        TIME_STEP_EMPTY_INTERNALDATA_MISSING_MID_WIZARD_XHRS
    )
    out["full_trail_xhrs"] = tuple(TIME_STEP_EMPTY_INTERNALDATA_FULL_TRAIL_XHRS)
    out["prior_captures"] = tuple(TIME_STEP_EMPTY_INTERNALDATA_PRIOR_CAPTURES)
    out["hypotheses"] = [dict(h) for h in TIME_STEP_EMPTY_INTERNALDATA["hypotheses"]]
    out["named_cad_finish_xhr_sequence"] = tuple(CAD_FINISH_NAMED_XHR_SEQUENCE)
    return out


def time_step_empty_internaldata_pns() -> tuple[str, ...]:
    return TIME_STEP_EMPTY_INTERNALDATA_PNS
