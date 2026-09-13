"""Q10333 / H.6.38 Safe Cave — Contours PASS protect.

Kyle Component→Cad + thickness inches + Finish. Laser costs filled.
Forever-protect like other live PASSes. Never remint / PATCH / ZZ-DEL.

Tip 0759273 wrongly forbade this as an empty-Contours ZZ-DEL fail.
That narrative is reversed: keep the ID/Q forbidden from remint/PATCH
as a PASS protect, not a leftover to discard.

Kyle Loom: STEP CAD Files Adjust Properties defaults ProductType to
Component. Plate/sheet laser must be Cad for Contours to fill.
Automation writes API/kendo ProductType=100 + SetPartMode 0 (not a
UI click). Still invent=false / fail-close if Contours stay empty.
"""

from __future__ import annotations

from typing import Any

Q10333_PASS: dict[str, Any] = {
    "quote_id": "b5f56ac3-326d-48e9-b82d-1e09a7897107",
    "quote_id_prefix": "b5f56ac3",
    "quote_number": "Q10333",
    "part_number": "H.6.38",
    "customer": "Safe Cave",
    "source": "Onshape STEP",
    "pass": True,
    "contours_pass": True,
    "laser_costs_filled": True,
    "kyle_component_to_cad": True,
    "thickness_inches": True,
    "finish_clicked": True,
    "finish_posted": True,
    "invent": False,
    "zz_del": False,
    "zz_del_number": None,
    "protect": True,
    "readonly": True,
    "do_not_remint": True,
    "do_not_patch": True,
    "kyle_loom_component_to_cad": True,
    "cad_set_via": "adjust_properties_dropdown_human",
    "unlocks_automation_contours_fill": False,
}


def q10333_h638_pass_dump() -> dict[str, Any]:
    """Read-only Contours PASS protect. Never remint / PATCH / ZZ-DEL."""
    return dict(Q10333_PASS)
