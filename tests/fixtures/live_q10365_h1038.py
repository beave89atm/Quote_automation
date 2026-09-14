"""Q10365 / 7801ab99 — Safe Cave H.10.38 Contours FAIL leftover.

  Q10365 / 7801ab99-13af-4efc-b996-897daf8e677a
  Safe Cave / H.10.38
  Mouse Cad + 0.1875 in were set but finished ProductType
  rendered ``part``. No Contours / InternalData fill;
  fill_xhr=null. Contours PASS not proven.

Same empty-InternalData / Contours-FAIL leftover class as
Q10354 / 7881d4b3 / D.H.38.96 and Q10356 / 05bee105 / V.20.78
(and Q10334 / Q10335) — not the Contours PASS pattern.
Q10354 and Q10356 stay FAIL. Q10349 / D.H.30.96 and Q10351 /
H.8.38 stay PASS. invent=false — do not invent InternalData /
Contours / NumberOfContours / unstated live GET fields.

Forever-forbid; never remint / PATCH. Does not unlock invent
Contours fill.
"""

from __future__ import annotations

from typing import Any

Q10365_H1038_FAIL: dict[str, Any] = {
    "quote_id": "7801ab99-13af-4efc-b996-897daf8e677a",
    "quote_id_prefix": "7801ab99",
    "quote_number": "Q10365",
    "part_number": "H.10.38",
    "customer": "Safe Cave",
    "piece": "H.10.38",
    "source": "Kyle UI / named leftover",
    "outside_h638_family": True,
    "h638_contours_good": False,
    "via": "cad_selector_0_1875_in_finished_producttype_part",
    "same_pattern_as": "empty-InternalData Contours FAIL",
    "same_class_as": "Q10354 / Q10356",
    "id_unknown": False,
    "pass": False,
    "contours_pass": False,
    "contours_pass_proven": False,
    "product_type": "part",
    "cad_selector_set": True,
    "thickness": "0.1875",
    "thickness_units": "inch",
    "thickness_inches": True,
    "number_of_contours_unavailable": True,
    "internaldata_empty": True,
    "contours_empty": True,
    "contours_fill": False,
    "fill_xhr": None,
    "invent": False,
    "zz_del": False,
    "zz_del_number": None,
    "protect": False,
    "readonly": True,
    "do_not_remint": True,
    "do_not_patch": True,
    "unlocks_automation_contours_fill": False,
    "unlocks_contours_fill": False,
    "fail_close": True,
}


def q10365_h1038_fail_dump() -> dict[str, Any]:
    """Read-only H.10.38 Contours FAIL leftover. Never remint / PATCH."""
    return dict(Q10365_H1038_FAIL)
