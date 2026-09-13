"""Q10346 / d859a239 — Safe Cave Sprout B80510901 Contours PASS (outside H.6.38).

  Q10346 / d859a239-a811-4b23-a812-29921956e880
  Safe Cave / Sprout B80510901 main plate
  ProductType Cad + thickness 0.0598 inch → Contours fill → Finish

Outside the H.6.38 Contours-good family (Q10333 / Q10336 / Q10339 /
Q10344). invent=false — do not invent InternalData / Contours
geometry / unstated live GET fields.

Forever-protect; never remint / PATCH. Does not unlock invent
Contours fill.
"""

from __future__ import annotations

from typing import Any

Q10346_SPROUT_PASS: dict[str, Any] = {
    "quote_id": "d859a239-a811-4b23-a812-29921956e880",
    "quote_id_prefix": "d859a239",
    "quote_number": "Q10346",
    "part_number": "B80510901",
    "customer": "Safe Cave",
    "piece": "Sprout B80510901 main plate",
    "source": "Kyle UI / named control",
    "outside_h638_family": True,
    "h638_contours_good": False,
    "via": "producttype_cad_thickness_0_0598_inch_then_contours_fill_then_finish",
    "id_unknown": False,
    "pass": True,
    "contours_pass": True,
    "product_type": "Cad",
    "product_type_enum": 100,
    "thickness": "0.0598",
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
    "unlock": "component_to_cad_then_thickness_inches_then_contours_fill",
    "unlocks_automation_contours_fill": False,
}


def q10346_sprout_pass_dump() -> dict[str, Any]:
    """Read-only Sprout Contours PASS leftover. Never remint / PATCH."""
    return dict(Q10346_SPROUT_PASS)
