"""Q10460 leftover — EXEC_FAIL gate6 AddItem_DXFFiles empty body.

EXEC_FAIL gate6 AddItem_DXFFiles empty body / missing List,Result
after Linear stick + PR62 Finish. Contours none. invent=false.
OPEN-NEW leftover 2026-09-15.

Stated only. Do not invent Contours / InternalData.

Never remint / PATCH Q10460 / 2873e5f8-4339-41b1-ab82-2fb6a27026d3.
Do not forbid 35146-1 (PN remint).
"""

from __future__ import annotations

from typing import Any

from secturafab.website import STEP_CAD_FINISH_HARD_GATE_EXEC_FAIL

Q10460_QUOTE_ID = "2873e5f8-4339-41b1-ab82-2fb6a27026d3"
Q10460_QUOTE_ID_PREFIX = "2873e5f8"

Q10460_35146_1_CONTOURS_NONE: dict[str, Any] = {
    "quote_number": "Q10460",
    "quote_id": Q10460_QUOTE_ID,
    "quote_id_prefix": Q10460_QUOTE_ID_PREFIX,
    "part_number": "35146-1",
    "remint_attempt_date": "2026-09-15",
    "complete_quote_done": False,
    "open_new_draft": True,
    "complete_quote_note": (
        "OPEN-NEW leftover 2026-09-15 after Linear stick + PR62 Finish"
    ),
    "pass": False,
    "exec_fail": STEP_CAD_FINISH_HARD_GATE_EXEC_FAIL,
    "gate6_additem_dxffiles_empty_body": True,
    "missing_list_result": True,
    "after_linear_stick": True,
    "after_pr62_finish": True,
    "contours_none": True,
    "invent": False,
    "invent_contours": False,
    "invent_internaldata": False,
    "do_not_remint_quote_number": True,
    "do_not_forbid_part_number": True,
    "do_not_patch": True,
    "protect": True,
}


def q10460_35146_1_contours_none() -> dict[str, Any]:
    """Read-only Q10460 leftover. No invented Contours."""
    return dict(Q10460_35146_1_CONTOURS_NONE)
