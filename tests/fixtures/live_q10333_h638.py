"""Q10333 / H.6.38 Safe Cave — live Contours UI PASS protect.

Live proof (do not remint / PATCH / ZZ-DEL):
  Q10333 / b5f56ac3-326d-48e9-b82d-1e09a7897107 / H.6.38 / Safe Cave
  ProductType Cad / Contours=1 / 8 bends + Profile / Laser Bay1 / UC 176.96

Unlock: Component→Cad then thickness inches then Contours fill.
Kyle Loom Adjust Properties defaults ProductType to Component after
Geometry Cleanup. Automation writes API/kendo ProductType=100 +
SetPartMode 0 (not a UI click). Cad classify ≠ Contours fill
(H638-CADPLATE / 5e7bfc0b, Q10334 / e2683a3f). invent=false —
still fail-close if Contours/InternalData stay empty after Cad.

Tip 0759273 wrongly forbade this as an empty-Contours ZZ-DEL fail.
That narrative is reversed: forever-protect like other live PASSes.
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
    "product_type": "Cad",
    "product_type_enum": 100,
    "number_of_contours": 1,
    "bends": 8,
    "profile": True,
    "machine": "Laser Bay1",
    "unit_cost": 176.96,
    "laser_costs_filled": True,
    "unlock": "component_to_cad_then_thickness_inches_then_contours_fill",
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
