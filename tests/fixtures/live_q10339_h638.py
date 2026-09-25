"""Q10339 / 76cecc73 — Cad+Laser Finish leftover (finished Contours match Q10333).

EOD STP Cad→Finish on Safe Cave H.6.38 (same STEP family as Q10333).
Live GET after Finish is semantically identical to Q10333 / Q10336:

  Q10339 / 76cecc73-257e-4fa7-91b7-ed15a4c90caa / H.6.38 / Safe Cave
  NumberOfContours=1 (v1 ItemList) — Contours PASS signal
  CadImport OpenContourCount=0 (expected; same on human PASS Q10333)
  bends=8 / OCL Profile×5 + Bend×2
  InternalData absent post-Finish
  Laser Bay1 / UC 64.25 / unit price 176.96

Soft-pass Contours=0 / OpenContourCount labels were stage notes, not a
finished-field gap. Do not gate Contours≥1 unlock on OCC≥1 (false-fails
H.6.38 including Q10333). invent=false. Forever-protect; never remint /
PATCH / ZZ-DEL. Does not unlock invent Contours fill.

Unused Time STEPs that explode empty InternalData stay a separate
fail-close. Mid-wizard XHR probe still useful to see NumberOfContours
flip 0→1.
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
    "id_unknown": False,
    "pass": True,
    "contours_pass": True,
    "cad_laser_finish_soft_pass": True,
    "soft_pass_labels_were_stage_notes": True,
    "finished_semantics_match_q10333": True,
    "product_type": "Cad",
    "product_type_enum": 100,
    "machine": "Laser Bay1",
    "unit_cost": 64.25,
    "unit_price": 176.96,
    "number_of_contours": 1,
    "open_contour_count": 0,
    "contours_ge_1": True,
    "contours_pass_signal": "v1_itemlist_number_of_contours_ge_1",
    "bends": 8,
    "profile": True,
    "ocl_profile_count": 5,
    "ocl_bend_count": 2,
    "internaldata_absent_post_finish": True,
    "finish_clicked": True,
    "finish_posted": True,
    "invent": False,
    "zz_del": False,
    "zz_del_number": None,
    "protect": True,
    "readonly": True,
    "do_not_remint": True,
    "do_not_patch": True,
    "cad_set_via": "eod_stp_cad_then_finish",
    "unlocks_automation_contours_fill": False,
    "update_item_type_fills_contours": False,
}


def q10339_h638_cad_finish_dump() -> dict[str, Any]:
    """Read-only Cad+Finish leftover. Never remint / PATCH / ZZ-DEL."""
    return dict(Q10339_CAD_FINISH)
