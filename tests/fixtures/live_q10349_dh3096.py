"""Q10349 / c4394006 — Safe Cave D.H.30.96 Contours PASS leftover.

  Q10349 / c4394006-667f-4bf6-a9b0-aa4b1722160a
  Safe Cave / D.H.30.96
  ProductType Cad + thickness 0.1875 inch → Contours fill → Finish

Outside the H.6.38 Contours-good family (Q10333 / Q10336 / Q10339 /
Q10344). invent=false — do not invent InternalData / Contours
geometry / unstated live GET fields.

Forever-protect; never remint / PATCH. Does not unlock invent
Contours fill.
"""

from __future__ import annotations

from typing import Any

Q10349_DH3096_PASS: dict[str, Any] = {
    "quote_id": "c4394006-667f-4bf6-a9b0-aa4b1722160a",
    "quote_id_prefix": "c4394006",
    "quote_number": "Q10349",
    "part_number": "D.H.30.96",
    "customer": "Safe Cave",
    "piece": "D.H.30.96",
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


def q10349_dh3096_pass_dump() -> dict[str, Any]:
    """Read-only D.H.30.96 Contours PASS leftover. Never remint / PATCH."""
    return dict(Q10349_DH3096_PASS)
