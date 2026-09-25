"""Q10351 / 0c62fce9 — Safe Cave H.8.38 Contours PASS leftover.

  Q10351 / 0c62fce9-d56a-434e-a33a-372ddb12a2b4
  Safe Cave / H.8.38
  ProductType Cad + thickness inches → Contours fill → Finish

Outside the H.6.38 Contours-good family (Q10333 / Q10336 / Q10339 /
Q10344). invent=false — do not invent InternalData / Contours
geometry / unstated live GET fields.

Forever-protect; never remint / PATCH. Does not unlock invent
Contours fill.
"""

from __future__ import annotations

from typing import Any

Q10351_H838_PASS: dict[str, Any] = {
    "quote_id": "0c62fce9-d56a-434e-a33a-372ddb12a2b4",
    "quote_id_prefix": "0c62fce9",
    "quote_number": "Q10351",
    "part_number": "H.8.38",
    "customer": "Safe Cave",
    "piece": "H.8.38",
    "source": "Kyle UI / named control",
    "outside_h638_family": True,
    "h638_contours_good": False,
    "via": "producttype_cad_thickness_inches_then_contours_fill_then_finish",
    "id_unknown": False,
    "pass": True,
    "contours_pass": True,
    "product_type": "Cad",
    "product_type_enum": 100,
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


def q10351_h838_pass_dump() -> dict[str, Any]:
    """Read-only H.8.38 Contours PASS leftover. Never remint / PATCH."""
    return dict(Q10351_H838_PASS)
