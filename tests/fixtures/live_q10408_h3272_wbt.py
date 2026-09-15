"""Q10408 / Safe Cave H.32.72.WBT Contours FAIL leftover.

Live tip c08c47b: OPEN-NEW leftover. Same POST /part/create
List=[] empty InternalData class as Q10407 / H.8.42.
Contours FAIL. invent=false.

Stated only. Do not invent Contours / InternalData.

Never remint / PATCH Q10408. Do not forbid H.32.72.WBT (PN remint).
"""

from __future__ import annotations

from typing import Any

Q10408_QUOTE_ID = "09bae33d-f244-4afb-a25e-b40a98b725d1"
Q10408_QUOTE_ID_PREFIX = "09bae33d"

Q10408_H3272_WBT_CONTOURS_FAIL: dict[str, Any] = {
    "quote_number": "Q10408",
    "quote_id": Q10408_QUOTE_ID,
    "part_number": "H.32.72.WBT",
    "customer": "Safe Cave",
    "piece": "H.32.72.WBT",
    "live_probe_tip": "c08c47b",
    "complete_quote_done": False,
    "open_new_draft": True,
    "complete_quote_note": "OPEN-NEW leftover",
    "pass": False,
    "contours_pass": False,
    "same_class_as": "Q10407 POST /part/create List=[] empty InternalData",
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


def q10408_h3272_wbt_contours_fail() -> dict[str, Any]:
    """Read-only Q10408 leftover. No invented Contours."""
    return dict(Q10408_H3272_WBT_CONTOURS_FAIL)
