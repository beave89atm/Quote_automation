"""Contours gap: Q10333 human PASS vs Q10336 mouse Cad+Finish.

Same Safe Cave H.6.38 STEP family. invent=false — hypotheses only.
Does not unlock Contours fill. Forever-protect both leftovers.

Q10333 / b5f56ac3 — human Component→Cad + thickness + Finish:
  Contours=1 / 8 bends PASS (Cad / Profile / Laser Bay1 / UC 176.96)

Q10336 / f73dd116 — mouse UpdateItemType Cad then AddItem_DXFFiles:
  OpenContourCount=0 / bends=1 Cad+Laser Finish soft PASS
  (Cad ProductType 100 / Laser Bay1 / UC 64.25)

NumberOfContours on Q10336 was not restated. InternalData on Finish
was not restated. Do not invent either.
"""

from __future__ import annotations

from typing import Any

from tests.fixtures.live_q10333_h638 import q10333_h638_pass_dump
from tests.fixtures.live_q10336_h638 import q10336_h638_cad_finish_dump

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
    "forever_protect": ("Q10333", "Q10336"),
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
    ),
}


def q10333_q10336_contours_gap() -> dict[str, Any]:
    """Read-only gap. Does not unlock Contours fill."""
    out = dict(Q10333_Q10336_CONTOURS_GAP)
    out["hypotheses"] = [dict(h) for h in Q10333_Q10336_CONTOURS_GAP["hypotheses"]]
    out["q10333"] = q10333_h638_pass_dump()
    out["q10336"] = q10336_h638_cad_finish_dump()
    return out
