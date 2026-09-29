"""Q10383 / 21641-1 TIP SLEEVE remint — EXEC_FAIL leftover.

Live tip f7e689d: remint EXEC_FAIL 2026-09-14. Contours=0 all
plate Cad kids after Finish. CadImport InternalData empty.
PrimaryOrganizationID lost mid CAD wizard. Kids not per-PN
classified (all named 21641-1 @ 0.25). invent=false.
Complete Quote NOT DONE. OPEN-NEW leftover.

Stated only. Do not invent Contours / InternalData.

Never remint / PATCH Q10383. Do not forbid 21641-1 (PN remint).
"""

from __future__ import annotations

from typing import Any

from secturafab.website import STEP_CAD_FINISH_HARD_GATE_EXEC_FAIL

Q10383_QUOTE_ID = "9d7cc06e-0c7a-4393-a49f-498a1f484c31"
Q10383_QUOTE_ID_PREFIX = "9d7cc06e"

Q10383_21641_1_CONTOURS_FAIL: dict[str, Any] = {
    "quote_number": "Q10383",
    "quote_id": Q10383_QUOTE_ID,
    "part_number": "21641-1",
    "job": "TIP SLEEVE",
    "live_probe_tip": "f7e689d",
    "remint_attempt_date": "2026-09-14",
    "complete_quote_done": False,
    "open_new_draft": True,
    "complete_quote_note": (
        "OPEN-NEW leftover from 21641-1 TIP SLEEVE remint attempt 2026-09-14"
    ),
    "pass": False,
    "exec_fail": STEP_CAD_FINISH_HARD_GATE_EXEC_FAIL,
    "cadimport_internaldata_empty": True,
    "primary_organization_id_lost_mid_cad_wizard": True,
    "kids_not_per_pn_classified": True,
    "kids_all_named": "21641-1",
    "kids_all_thickness_in": 0.25,
    "all_plate_cad_kids_contours_after_finish": 0,
    "kids": (
        {
            "name": "21641-1",
            "classify": "Cad",
            "is_plate": True,
            "thickness_in": 0.25,
            "per_pn_classified": False,
            "number_of_contours": 0,
        },
    ),
    "invent": False,
    "invent_contours": False,
    "invent_internaldata": False,
    "do_not_remint_quote_number": True,
    "do_not_forbid_part_number": True,
    "do_not_patch": True,
    "protect": True,
}


def q10383_21641_1_contours_fail() -> dict[str, Any]:
    """Read-only Q10383 remint leftover. No invented Contours."""
    out = dict(Q10383_21641_1_CONTOURS_FAIL)
    out["kids"] = [dict(row) for row in Q10383_21641_1_CONTOURS_FAIL["kids"]]
    return out
