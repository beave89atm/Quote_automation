"""Q10399 / 21641-1 hardened remint — EXEC_FAIL leftover.

Live tip 6a26835: remint EXEC_FAIL 2026-09-14 after dig
checklist gates 1–4 PASS. Gate5 InternalData empty after
explode refused AddItem_DXFFiles. Contours never filled.
invent=false. Complete Quote NOT DONE. OPEN-NEW leftover.

Stated only. Do not invent Contours / InternalData.

Never remint / PATCH Q10399. Do not forbid 21641-1 (PN remint).
"""

from __future__ import annotations

from typing import Any

from secturafab.website import STEP_CAD_FINISH_HARD_GATE_EXEC_FAIL

Q10399_QUOTE_ID = "039d8464-6fe1-424a-a120-a31e59964e7e"
Q10399_QUOTE_ID_PREFIX = "039d8464"

Q10399_21641_1_CONTOURS_FAIL: dict[str, Any] = {
    "quote_number": "Q10399",
    "quote_id": Q10399_QUOTE_ID,
    "part_number": "21641-1",
    "job": "TIP SLEEVE",
    "live_probe_tip": "6a26835",
    "remint_attempt_date": "2026-09-14",
    "hardened_remint": True,
    "complete_quote_done": False,
    "open_new_draft": True,
    "complete_quote_note": (
        "OPEN-NEW leftover from hardened 21641 remint 2026-09-14"
    ),
    "pass": False,
    "exec_fail": STEP_CAD_FINISH_HARD_GATE_EXEC_FAIL,
    "dig_checklist_gates_1_to_4_pass": True,
    "gate5_internaldata_empty_after_explode": True,
    "additem_dxffiles_refused": True,
    "contours_never_filled": True,
    "invent": False,
    "invent_contours": False,
    "invent_internaldata": False,
    "do_not_remint_quote_number": True,
    "do_not_forbid_part_number": True,
    "do_not_patch": True,
    "protect": True,
}


def q10399_21641_1_contours_fail() -> dict[str, Any]:
    """Read-only Q10399 remint leftover. No invented Contours."""
    return dict(Q10399_21641_1_CONTOURS_FAIL)
