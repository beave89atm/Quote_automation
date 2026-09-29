"""Q10420 / 35146-1 tip-prove remint — EXEC_FAIL leftover.

Live tip c08c47b: remint EXEC_FAIL 2026-09-15. chrome_cdp skipped
page Finish solely because InternalData empty after explode,
despite tip refuse-relax (cad_material_inches_recipe_complete /
cad_filelist_refuses_additem_dxf returning None). Contours never
filled. invent=false. Complete Quote NOT DONE. OPEN-NEW leftover.

Stated only. Do not invent Contours / InternalData.

Never remint / PATCH Q10420. Do not forbid 35146-1 (PN remint).
"""

from __future__ import annotations

from typing import Any

from secturafab.website import STEP_CAD_FINISH_HARD_GATE_EXEC_FAIL

Q10420_QUOTE_ID = "4054443b-bc2a-47f4-95b1-b0ed037868c9"
Q10420_QUOTE_ID_PREFIX = "4054443b"

Q10420_35146_1_CONTOURS_FAIL: dict[str, Any] = {
    "quote_number": "Q10420",
    "quote_id": Q10420_QUOTE_ID,
    "part_number": "35146-1",
    "job": "Jib Turret",
    "live_probe_tip": "c08c47b",
    "remint_attempt_date": "2026-09-15",
    "tip_prove": True,
    "complete_quote_done": False,
    "open_new_draft": True,
    "complete_quote_note": (
        "OPEN-NEW leftover from tip-prove 35146 remint 2026-09-15"
    ),
    "pass": False,
    "exec_fail": STEP_CAD_FINISH_HARD_GATE_EXEC_FAIL,
    "chrome_cdp_skipped_page_finish": True,
    "skip_why": "cad_internaldata_empty_after_explode",
    "tip_refuse_relax_ignored": True,
    "cad_material_inches_recipe_complete": True,
    "contours_never_filled": True,
    "invent": False,
    "invent_contours": False,
    "invent_internaldata": False,
    "do_not_remint_quote_number": True,
    "do_not_forbid_part_number": True,
    "do_not_patch": True,
    "protect": True,
}


def q10420_35146_1_contours_fail() -> dict[str, Any]:
    """Read-only Q10420 remint leftover. No invented Contours."""
    return dict(Q10420_35146_1_CONTOURS_FAIL)
