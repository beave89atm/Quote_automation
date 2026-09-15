"""Q10407 / Safe Cave H.8.42 Contours FAIL leftover.

Live tip c08c47b: OPEN-NEW leftover. POST /part/create List=[]
empty InternalData. Contours FAIL. invent=false.

Stated only. Do not invent Contours / InternalData.

Never remint / PATCH Q10407. Do not forbid H.8.42 (PN remint).
"""

from __future__ import annotations

from typing import Any

Q10407_QUOTE_ID = "d796cdbe-b4b6-4d64-937f-826f19efa623"
Q10407_QUOTE_ID_PREFIX = "d796cdbe"

Q10407_H842_CONTOURS_FAIL: dict[str, Any] = {
    "quote_number": "Q10407",
    "quote_id": Q10407_QUOTE_ID,
    "part_number": "H.8.42",
    "customer": "Safe Cave",
    "piece": "H.8.42",
    "live_probe_tip": "c08c47b",
    "complete_quote_done": False,
    "open_new_draft": True,
    "complete_quote_note": "OPEN-NEW leftover",
    "pass": False,
    "contours_pass": False,
    "same_class_as": "POST /part/create List=[] empty InternalData",
    "part_create_list": [],
    "part_create_list_empty": True,
    "internaldata_empty": True,
    "contours_never_filled": True,
    "invent": False,
    "invent_contours": False,
    "invent_internaldata": False,
    "do_not_remint_quote_number": True,
    "do_not_forbid_part_number": True,
    "do_not_patch": True,
    "protect": True,
}


def q10407_h842_contours_fail() -> dict[str, Any]:
    """Read-only Q10407 leftover. No invented Contours."""
    return dict(Q10407_H842_CONTOURS_FAIL)
