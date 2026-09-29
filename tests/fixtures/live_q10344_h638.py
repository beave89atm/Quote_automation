"""Q10344 / 55f12530 — Safe Cave H.6.38 Kyle UI control PASS leftover.

Kyle UI control on Safe Cave H.6.38 (same STEP family as Q10333):
  Q10344 / 55f12530-e97b-40cc-8e7f-e799d9d6b234 / H.6.38 / Safe Cave
  ProductType Cad + thickness 0.1875 inch → Contours fill → Finish

Contours-good control leftover. invent=false — do not invent
InternalData / Contours geometry / unstated live GET fields.
Forever-protect; never remint / PATCH / ZZ-DEL. Does not unlock
invent Contours fill.

Unlock path named by the control: Component→Cad then thickness
inches then Contours fill. Hard-gate before Finish: ProductType
Cad, then inch thickness (not blank, not meter); missing thickness
is EXEC_FAIL, not Contours empty.
"""

from __future__ import annotations

from typing import Any

Q10344_KYLE_UI_CONTROL: dict[str, Any] = {
    "quote_id": "55f12530-e97b-40cc-8e7f-e799d9d6b234",
    "quote_id_prefix": "55f12530",
    "quote_number": "Q10344",
    "part_number": "H.6.38",
    "customer": "Safe Cave",
    "source": "Kyle UI control",
    "same_step_family_as": "Q10333",
    "via": "kyle_ui_producttype_cad_thickness_0_1875_inch_then_contours_fill_then_finish",
    "id_unknown": False,
    "pass": True,
    "contours_pass": True,
    "kyle_ui_control_pass": True,
    "product_type": "Cad",
    "product_type_enum": 100,
    "thickness": "0.1875",
    "thickness_units": "inch",
    "thickness_inches": True,
    "contours_fill": True,
    "finish_clicked": True,
    "finish_posted": True,
    "invent": False,
    "zz_del": False,
    "zz_del_number": None,
    "protect": True,
    "readonly": True,
    "do_not_remint": True,
    "do_not_patch": True,
    "cad_set_via": "kyle_ui_control",
    "unlock": "component_to_cad_then_thickness_inches_then_contours_fill",
    "unlocks_automation_contours_fill": False,
}


def q10344_h638_kyle_ui_control_dump() -> dict[str, Any]:
    """Read-only Kyle UI control PASS leftover. Never remint / PATCH / ZZ-DEL."""
    return dict(Q10344_KYLE_UI_CONTROL)
