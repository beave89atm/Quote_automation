"""Q10348 / 1defeed8 — Safe Cave H.16.70 Contours PASS leftover.

  Q10348 / 1defeed8-d95d-4939-b2fd-0a1774e56c6e
  Safe Cave / H.16.70
  ProductType Cad + thickness 0.1875 inch → Contours fill → Finish

Outside the H.6.38 Contours-good family (Q10333 / Q10336 / Q10339 /
Q10344). invent=false — do not invent InternalData / Contours
geometry / unstated live GET fields.

Forever-protect; never remint / PATCH. Does not unlock invent
Contours fill.
"""

from __future__ import annotations

from typing import Any

Q10348_H1670_PASS: dict[str, Any] = {
    "quote_id": "1defeed8-d95d-4939-b2fd-0a1774e56c6e",
    "quote_id_prefix": "1defeed8",
    "quote_number": "Q10348",
    "part_number": "H.16.70",
    "customer": "Safe Cave",
    "piece": "H.16.70",
    "source": "Kyle UI / named control",
    "outside_h638_family": True,
    "h638_contours_good": False,
    "via": "producttype_cad_thickness_0_1875_inch_then_contours_fill_then_finish",
    "id_unknown": False,
    "pass": True,
    "contours_pass": True,
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
    "unlock": "component_to_cad_then_thickness_inches_then_contours_fill",
    "unlocks_automation_contours_fill": False,
}


def q10348_h1670_pass_dump() -> dict[str, Any]:
    """Read-only H.16.70 Contours PASS leftover. Never remint / PATCH."""
    return dict(Q10348_H1670_PASS)
