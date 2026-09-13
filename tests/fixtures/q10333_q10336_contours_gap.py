"""Contours gap: Q10333 human PASS vs Cad→Finish soft PASSes.

Same Safe Cave H.6.38 STEP family for Q10333 / Q10336. invent=false —
hypotheses only. Does not unlock Contours fill. Forever-protect leftovers.

Q10333 / b5f56ac3 — human Component→Cad + thickness + Finish:
  Contours=1 / 8 bends PASS (Cad / Profile / Laser Bay1 / UC 176.96)
  Human XHR sequence was never captured.

Q10336 / f73dd116 — mouse UpdateItemType Cad then AddItem_DXFFiles:
  OpenContourCount=0 / bends=1 Cad+Laser Finish soft PASS
  (Cad ProductType 100 / Laser Bay1 / UC 64.25)
  Named XHRs: Upload → Data → /part/create → UpdateItemType →
  PartImage → GetBorderSize Thickness_Units=inch → AddItem_DXFFiles →
  /quote/ItemEdit.

Q10339 — automation Cad→Finish soft PASS class (Contours=0 /
  OpenContourCount=0 after UpdateItemType+Finish). ID not restated.

Unused Time STEPs explode with empty InternalData; Finish refused.

NumberOfContours on Q10336 was not restated. InternalData on Finish
was not restated. Do not invent either. ItemEdit is post-Finish
navigation, not a fill. GetBorderSize other keys were not restated.
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
    "same_step_family": "H.6.38",
    "customer": "Safe Cave",
    "q10333_contours": 1,
    "q10333_bends": 8,
    "q10333_via": "human_dropdown_thickness_finish",
    "q10333_pass": True,
    "q10336_open_contour_count": 0,
    "q10336_bends": 1,
    "q10336_via": "mouse_updateitemtype_cad_then_finish",
    "q10336_contours_pass": False,
    "q10336_cad_laser_finish_soft_pass": True,
    "q10339_open_contour_count": 0,
    "q10339_contours": 0,
    "q10339_via": "automation_updateitemtype_cad_then_finish",
    "q10339_contours_pass": False,
    "q10339_cad_laser_finish_soft_pass": True,
    "q10339_id_unknown": True,
    "named_cad_finish_xhr_sequence": CAD_FINISH_NAMED_XHR_SEQUENCE,
    "forever_protect": ("Q10333", "Q10336", "Q10339"),
    "hypotheses": (
        {
            "id": "number_of_contours_vs_open_contour_count",
            "ruled_out": False,
            "why": (
                "Q10333 live UI named Contours=1. Q10336 verify named "
                "OpenContourCount=0. Same field vs different field is "
                "unknown. Do not treat OpenContourCount as NumberOfContours."
            ),
        },
        {
            "id": "bend_vs_outer_contour",
            "ruled_out": False,
            "why": (
                "Q10333 has 8 bends + Contours=1. Q10336 has bends=1 and "
                "OpenContourCount=0. A bend count is not an outer-contour "
                "count. Do not invent which geometry filled Contours."
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
            "id": "filelist_internaldata_on_finish",
            "ruled_out": False,
            "why": (
                "OnAddDXFClick copies #gridDXFParts as-is. Q10336 posted "
                "AddItem_DXFFiles after UpdateItemType. FileList "
                "InternalData emptiness on that Finish was not restated. "
                "Do not invent InternalData or a fill XHR."
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
            "ruled_out": False,
            "why": (
                "Q10336 named Upload→Data→/part/create→UpdateItemType→"
                "PartImage→GetBorderSize→AddItem_DXFFiles→ItemEdit and "
                "still OpenContourCount=0. Q10339 is the same "
                "automation Cad→Finish soft PASS class (Contours=0 / "
                "OCC=0). Named sequence is not Contours≥1."
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
                "Finish is refused invent=false. That class is not the "
                "Q10336/Q10339 soft PASS; it never reaches AddItem_DXFFiles."
            ),
        },
    ),
}


def q10333_q10336_contours_gap() -> dict[str, Any]:
    """Read-only gap. Does not unlock Contours fill."""
    out = dict(Q10333_Q10336_CONTOURS_GAP)
    out["hypotheses"] = [dict(h) for h in Q10333_Q10336_CONTOURS_GAP["hypotheses"]]
    out["q10333"] = q10333_h638_pass_dump()
    out["q10336"] = q10336_h638_cad_finish_dump()
    out["q10339"] = q10339_h638_cad_finish_dump()
    out["named_cad_finish_xhr_sequence"] = tuple(CAD_FINISH_NAMED_XHR_SEQUENCE)
    return out
