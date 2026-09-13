"""Q10339 — Cad→Finish soft PASS leftover (Contours≥1 still gap).

Automation Cad→Finish after UpdateItemType. Same soft PASS class as
Q10336 / f73dd116: Contours=0 / OpenContourCount=0 after
UpdateItemType+Finish. invent=false.

Quote ID was not restated in repo / PR 18 / prior leftover transcript /
Dropbox. Forbid the Q number only — do not invent an ID. Forever-protect
as a Cad+Laser Finish leftover. Not a Contours=1 PASS. Never remint /
PATCH.

Q10333 / b5f56ac3 stays Contours PASS protect. Unused Time STEPs that
explode with empty InternalData still refuse Finish. Fill stays locked.
"""

from __future__ import annotations

from typing import Any

Q10339_CAD_FINISH: dict[str, Any] = {
    "quote_id": None,
    "quote_id_prefix": None,
    "quote_number": "Q10339",
    "part_number": None,
    "customer": None,
    "id_unknown": True,
    "id_source": "not restated in repo / PR 18 / Dropbox / leftover notes",
    "same_class_as": "Q10336",
    "via": "automation_updateitemtype_cad_then_finish",
    "pass": True,
    "contours_pass": False,
    "cad_laser_finish_soft_pass": True,
    "open_contour_count": 0,
    "number_of_contours": 0,
    "contours_ge_1": False,
    "finish_clicked": True,
    "finish_posted": True,
    "invent": False,
    "zz_del": False,
    "zz_del_number": None,
    "protect": True,
    "readonly": True,
    "do_not_remint": True,
    "do_not_patch": True,
    "cad_set_via": "automation_updateitemtype_cad",
    "unlocks_automation_contours_fill": False,
    "update_item_type_fills_contours": False,
}


def q10339_h638_cad_finish_dump() -> dict[str, Any]:
    """Read-only Cad+Finish leftover. ID unknown. Never remint / PATCH."""
    return dict(Q10339_CAD_FINISH)
