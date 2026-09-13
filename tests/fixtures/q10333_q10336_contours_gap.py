"""Finished H.6.38 Contours semantics — live GET closed the field gap.

Same Safe Cave H.6.38 STEP family. invent=false. Forever-protect leftovers.
Does not unlock invent Contours fill.

Live GET after Finish (Q10333 / Q10336 / Q10339) is semantically identical:
  NumberOfContours=1 (v1 ItemList) — Contours PASS signal
  CadImport OpenContourCount=0 (including human PASS Q10333)
  bends=8 / OCL Profile×5 + Bend×2
  InternalData absent post-Finish

Soft-pass Contours=0 / OpenContourCount labels were stage notes, not a
finished-field gap. Do not gate Contours≥1 unlock on OCC≥1 (false-fails
H.6.38 including Q10333).

Q10333 / b5f56ac3 — human Component→Cad + thickness + Finish
  Cad / Profile / Laser Bay1 / UC 176.96. Human XHR sequence unrecorded.

Q10336 / f73dd116 — mouse UpdateItemType Cad then AddItem_DXFFiles
  Cad ProductType 100 / Laser Bay1 / UC 64.25
  Named XHRs: Upload → Data → /part/create → UpdateItemType →
  PartImage → GetBorderSize Thickness_Units=inch → AddItem_DXFFiles →
  /quote/ItemEdit.

Q10339 / 76cecc73 — EOD STP Cad→Finish
  Laser Bay1 / UC 64.25 / unit price 176.96.

Unused Time STEPs explode with empty InternalData; Finish refused
(separate gate). Mid-wizard XHR probe still useful to see when
NumberOfContours flips 0→1.
"""

from __future__ import annotations

from typing import Any

from secturafab.cadimport_js import CAD_FINISH_NAMED_XHR_SEQUENCE
from tests.fixtures.live_q10333_h638 import q10333_h638_pass_dump
from tests.fixtures.live_q10336_h638 import q10336_h638_cad_finish_dump
from tests.fixtures.live_q10339_h638 import q10339_h638_cad_finish_dump

Q10333_Q10336_CONTOURS_GAP: dict[str, Any] = {
    "invent": False,
    "unlocks_automation_contours_fill": False,
    "finished_field_gap_closed": True,
    "contours_pass_signal": "v1_itemlist_number_of_contours_ge_1",
    "open_contour_count_unlocks_contours": False,
    "soft_pass_labels_were_stage_notes": True,
    "same_step_family": "H.6.38",
    "customer": "Safe Cave",
    "q10333_contours": 1,
    "q10333_bends": 8,
    "q10333_open_contour_count": 0,
    "q10333_via": "human_dropdown_thickness_finish",
    "q10333_pass": True,
    "q10333_contours_pass": True,
    "q10336_open_contour_count": 0,
    "q10336_number_of_contours": 1,
    "q10336_bends": 8,
    "q10336_via": "mouse_updateitemtype_cad_then_finish",
    "q10336_contours_pass": True,
    "q10336_cad_laser_finish_soft_pass": True,
    "q10336_finished_semantics_match_q10333": True,
    "q10339_open_contour_count": 0,
    "q10339_contours": 1,
    "q10339_number_of_contours": 1,
    "q10339_via": "eod_stp_cad_then_finish",
    "q10339_contours_pass": True,
    "q10339_cad_laser_finish_soft_pass": True,
    "q10339_finished_semantics_match_q10333": True,
    "q10339_id_unknown": False,
    "named_cad_finish_xhr_sequence": CAD_FINISH_NAMED_XHR_SEQUENCE,
    "forever_protect": ("Q10333", "Q10336", "Q10339"),
    "mid_wizard_xhr_probe_useful": True,
    "explode_empty_internaldata_fail_close": True,
    "hypotheses": (
        {
            "id": "number_of_contours_vs_open_contour_count",
            "ruled_out": True,
            "why": (
                "Live GET: Q10333 / Q10336 / Q10339 all have "
                "NumberOfContours=1 and CadImport OpenContourCount=0, "
                "including human PASS Q10333. Different fields. OCC≥1 "
                "is not the Contours PASS signal and would false-fail "
                "H.6.38."
            ),
        },
        {
            "id": "bend_vs_outer_contour",
            "ruled_out": True,
            "why": (
                "Live GET: Q10333 / Q10336 / Q10339 all have bends=8 "
                "and NumberOfContours=1. Soft-pass bends=1 was a stage "
                "note, not a finished-field gap."
            ),
        },
        {
            "id": "thickness_material",
            "ruled_out": False,
            "why": (
                "Both are H.6.38 Safe Cave. Q10336 GetBorderSize used "
                "Thickness_Units=inch. Q10333 thickness inches was named "
                "only as a UI step. Material / exact thickness values "
                "were not restated — invent=false."
            ),
        },
        {
            "id": "post_finish_internaldata_absent",
            "ruled_out": True,
            "why": (
                "InternalData is absent on finished v1 ItemList for "
                "Q10333 / Q10336 / Q10339 including the human PASS. "
                "That absence is not a Contours fail. Empty explode "
                "InternalData before Finish is a separate refuse."
            ),
        },
        {
            "id": "human_q10333_xhr_unrecorded",
            "ruled_out": False,
            "why": (
                "Q10333 Contours=1 has no HAR. Extra human XHRs between "
                "Component→Cad / thickness / Finish are unknown. Do not "
                "invent a missing call from the human path."
            ),
        },
        {
            "id": "cad_finish_soft_pass_class",
            "ruled_out": True,
            "why": (
                "Soft-pass Contours=0 / OpenContourCount labels were "
                "stage notes. Finished Q10336 / Q10339 match Q10333 "
                "Contours semantics (NumberOfContours=1)."
            ),
        },
        {
            "id": "get_border_size_other_keys_unrecorded",
            "ruled_out": False,
            "why": (
                "Q10336 named Thickness_Units=inch on GetBorderSize. "
                "Method and other keys were not restated. Do not invent "
                "Thickness / ID / a POST body. Proven-keys probe only."
            ),
        },
        {
            "id": "unused_time_step_explode_empty",
            "ruled_out": False,
            "why": (
                "Unused Time STEPs still explode with empty InternalData. "
                "Live 28898-1 / 28772-1 / 14327-18 / 15911-9 / "
                "21839-1: UpdateItemType Cad OK, InternalData empty, "
                "Finish refused. 15911-9 / ef865b0f restated @ 62f7a92 "
                "(ZZ-DEL-15911-9); CadImport/Data + PartImage + "
                "GetBorderSize not observed vs H.6.38. 21839-1 / "
                "1994392f restated @ bb4998a+ (ZZ-DEL-21839-1); full "
                "CadImport/Data+GetBorderSize+PartImage trail still "
                "empty. Other IDs unknown. Sprout GSB20570006 / "
                "afee7458 (CoS hold) is the same empty-InternalData "
                "class outside H.6.38 / Time pick (11 parts, full "
                "Cad+wizard, invent=false; ZZ-DEL-GSB20570006). "
                "Separate gate from finished ItemList "
                "NumberOfContours PASS. invent=false. Never remint / "
                "PATCH Q10333 / Q10336 / Q10338 / Q10339."
            ),
        },
        {
            "id": "mid_wizard_number_of_contours_flip",
            "ruled_out": False,
            "why": (
                "Named Cad→Finish XHR probe is still useful to see when "
                "NumberOfContours flips 0→1 mid-wizard. Does not unlock "
                "invent fill. invent=false."
            ),
        },
        {
            "id": "cadimport_data_and_updateitemtype_not_contours_flip",
            "ruled_out": True,
            "why": (
                "Mid-wizard notes: GET /CadImport/Data, POST "
                "/Part/UpdateItemType, and /Quote/GetBorderSize are not "
                "the finished Contours flip carrier. CadImport/Data has "
                "no NumberOfContours; OpenContourCount=0 even on PASS."
            ),
        },
        {
            "id": "quote_item_read_omits_number_of_contours",
            "ruled_out": False,
            "why": (
                "QuoteItem_Read list items omit NumberOfContours. Persist "
                "must use finished GET v1 ItemList or "
                "QuoteItem_ReadTreeListData. invent=false."
            ),
        },
        {
            "id": "open_url_only_additem_dxf_itemedit_v1_tree",
            "ruled_out": False,
            "why": (
                "Still open URL-only (no invented body): AddItem_DXFFiles, "
                "/quote/ItemEdit, post-Finish v1 GET, GET "
                "/Quote/QuoteItem_ReadTreeListData."
            ),
        },
    ),
}


def q10333_q10336_contours_gap() -> dict[str, Any]:
    """Read-only finished-field notes. Does not unlock invent Contours fill."""
    out = dict(Q10333_Q10336_CONTOURS_GAP)
    out["hypotheses"] = [dict(h) for h in Q10333_Q10336_CONTOURS_GAP["hypotheses"]]
    out["q10333"] = q10333_h638_pass_dump()
    out["q10336"] = q10336_h638_cad_finish_dump()
    out["q10339"] = q10339_h638_cad_finish_dump()
    out["named_cad_finish_xhr_sequence"] = tuple(CAD_FINISH_NAMED_XHR_SEQUENCE)
    return out
