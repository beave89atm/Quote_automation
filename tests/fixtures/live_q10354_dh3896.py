"""Q10354 / 7881d4b3 — Safe Cave D.H.38.96 Contours FAIL leftover.

  Q10354 / 7881d4b3-5408-4ff4-ab18-6490170e6331
  Safe Cave / D.H.38.96
  Cad selector + 0.1875 in were set but finished ProductType
  rendered ``part``. NumberOfContours unavailable / Contours PASS
  not proven.

Same empty-InternalData / Contours-FAIL leftover class as
14327-5 / 14327-8 / H638-CADPLATE / Q10334 / Q10335 — not the
Contours PASS pattern. Q10349 / c4394006 / D.H.30.96 stays PASS.
invent=false — do not invent InternalData / Contours /
NumberOfContours / unstated live GET fields.

Forever-forbid; never remint / PATCH. Does not unlock invent
Contours fill.
"""

from __future__ import annotations

from typing import Any

Q10354_DH3896_FAIL: dict[str, Any] = {
    "quote_id": "7881d4b3-5408-4ff4-ab18-6490170e6331",
    "quote_id_prefix": "7881d4b3",
    "quote_number": "Q10354",
    "part_number": "D.H.38.96",
    "customer": "Safe Cave",
    "piece": "D.H.38.96",
    "source": "Kyle UI / named leftover",
    "outside_h638_family": True,
    "h638_contours_good": False,
    "via": "cad_selector_0_1875_in_finished_producttype_part",
    "same_pattern_as": "empty-InternalData Contours FAIL",
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


def q10354_dh3896_fail_dump() -> dict[str, Any]:
    """Read-only D.H.38.96 Contours FAIL leftover. Never remint / PATCH."""
    return dict(Q10354_DH3896_FAIL)
