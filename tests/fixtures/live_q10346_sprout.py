"""Q10346 — Safe Cave Sprout B80510901 Contours PASS (outside H.6.38).

Kyle UI / named control:
  Q10346 / Safe Cave / Sprout B80510901 main plate
  ProductType Cad + thickness 0.0598 inch → Contours fill → Finish

Outside the H.6.38 Contours-good family (Q10333 / Q10336 / Q10339 /
Q10344). invent=false — do not invent InternalData / Contours
geometry / an unstated quote UUID.

Forever-protect by QuoteNumber Q10346 and description B80510901.
Never remint / PATCH. Does not unlock invent Contours fill.

TODO: add quote_id / quote_id_prefix once the UUID is restated
(resolving in parallel). Do not invent an ID.
"""

from __future__ import annotations

from typing import Any

# TODO: restated UUID → FORBIDDEN_LIVE_QUOTE_IDS + prefix. Do not invent.
Q10346_QUOTE_ID_TODO = "quote_id once known"

Q10346_SPROUT_PASS: dict[str, Any] = {
    "quote_id": None,
    "quote_id_prefix": None,
    "quote_id_todo": Q10346_QUOTE_ID_TODO,
    "quote_number": "Q10346",
    "part_number": "B80510901",
    "customer": "Safe Cave",
    "piece": "Sprout B80510901 main plate",
    "source": "Kyle UI / named control",
    "outside_h638_family": True,
    "h638_contours_good": False,
    "via": "producttype_cad_thickness_0_0598_inch_then_contours_fill_then_finish",
    "id_unknown": True,
    "id_source": "UUID resolving in parallel; not restated in repo",
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
    """Read-only Sprout Contours PASS. Number-only until UUID is known."""
    return dict(Q10346_SPROUT_PASS)
