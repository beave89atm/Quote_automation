"""Q10339 / 76cecc73 — Cad+Laser Finish leftover (Contours≥1 still gap).

EOD STP Cad→Finish soft PASS on Safe Cave H.6.38 (same STEP family
as Q10333). Named live numbers only; invent=false:

  Q10339 / 76cecc73-257e-4fa7-91b7-ed15a4c90caa / H.6.38 / Safe Cave
  Laser Bay1 / UC 64.25 / unit price 176.96
  Contours=0 / OpenContourCount=0

Forever-protect like Q10336 (never remint / PATCH / ZZ-DEL) as a
Cad+Laser Finish leftover. Not a Contours=1 PASS. Contours≥1 still
gap vs Q10333 / b5f56ac3 (human Cad / Contours=1 / 8 bends / UC 176.96).
Does not unlock automation Contours fill.
"""

from __future__ import annotations

from typing import Any

Q10339_CAD_FINISH: dict[str, Any] = {
    "quote_id": "76cecc73-257e-4fa7-91b7-ed15a4c90caa",
    "quote_id_prefix": "76cecc73",
    "quote_number": "Q10339",
    "part_number": "H.6.38",
    "customer": "Safe Cave",
    "source": "STP",
    "same_step_family_as": "Q10333",
    "via": "eod_stp_cad_then_finish",
    "pass": True,
    "contours_pass": False,
    "cad_laser_finish_soft_pass": True,
    "machine": "Laser Bay1",
    "unit_cost": 64.25,
    "unit_price": 176.96,
    "number_of_contours": 0,
    "open_contour_count": 0,
    "contours_ge_1": False,
    "finish_clicked": True,
    "finish_posted": True,
    "invent": False,
    "zz_del": False,
    "zz_del_number": None,
    "protect": True,
    "readonly": True,
    "do_not_remint": True,
    "do_not_patch": True,
    "unlocks_automation_contours_fill": False,
}


def q10339_h638_cad_finish_dump() -> dict[str, Any]:
    """Read-only Cad+Finish leftover. Never remint / PATCH / ZZ-DEL."""
    return dict(Q10339_CAD_FINISH)
