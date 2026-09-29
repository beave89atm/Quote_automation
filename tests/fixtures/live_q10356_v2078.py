"""Q10356 / 05bee105 — Safe Cave V.20.78 Contours FAIL leftover.

  Q10356 / 05bee105-824c-4100-9bc8-f66727fa5681
  Safe Cave / V.20.78
  Cad selector + 0.1875 in were set but finished ProductType
  rendered ``part``. NumberOfContours missing / Contours PASS
  not proven.

Same empty-InternalData / Contours-FAIL leftover class as
Q10354 / 7881d4b3 / D.H.38.96 (and Q10334 / Q10335) — not the
Contours PASS pattern. Q10354 stays FAIL. Q10349 / D.H.30.96
stays PASS. invent=false — do not invent InternalData / Contours /
NumberOfContours / unstated live GET fields.

Forever-forbid; never remint / PATCH. Does not unlock invent
Contours fill.
"""

from __future__ import annotations

from typing import Any

Q10356_V2078_FAIL: dict[str, Any] = {
    "quote_id": "05bee105-824c-4100-9bc8-f66727fa5681",
    "quote_id_prefix": "05bee105",
    "quote_number": "Q10356",
    "part_number": "V.20.78",
    "customer": "Safe Cave",
    "piece": "V.20.78",
    "source": "Kyle UI / named leftover",
    "outside_h638_family": True,
    "h638_contours_good": False,
    "via": "cad_selector_0_1875_in_finished_producttype_part",
    "same_pattern_as": "empty-InternalData Contours FAIL",
    "same_class_as": "Q10354 / D.H.38.96",
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


def q10356_v2078_fail_dump() -> dict[str, Any]:
    """Read-only V.20.78 Contours FAIL leftover. Never remint / PATCH."""
    return dict(Q10356_V2078_FAIL)
