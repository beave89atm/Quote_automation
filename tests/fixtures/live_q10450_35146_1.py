"""Q10450 leftover after PR62 CDP prove — Contours never landed.

Minted as Q10450 after PR62 CDP prove. Contours never landed.
Live QuoteNumber drifted toward forbid Q10408 label.
OPEN-DRAFT. invent=false 2026-09-15.

Stated only. Do not invent Contours / InternalData.

Never remint / PATCH Q10450 / 1d59ef4a-5b75-49e7-89fe-02e125830162.
Do not forbid 35146-1 (PN remint).
"""

from __future__ import annotations

from typing import Any

Q10450_QUOTE_ID = "1d59ef4a-5b75-49e7-89fe-02e125830162"
Q10450_QUOTE_ID_PREFIX = "1d59ef4a"

Q10450_35146_1_CONTOURS_NEVER_LANDED: dict[str, Any] = {
    "quote_number": "Q10450",
    "quote_id": Q10450_QUOTE_ID,
    "quote_id_prefix": Q10450_QUOTE_ID_PREFIX,
    "part_number": "35146-1",
    "minted_after": "PR62 CDP prove",
    "remint_attempt_date": "2026-09-15",
    "complete_quote_done": False,
    "open_draft": True,
    "complete_quote_note": (
        "OPEN-DRAFT leftover after PR62 CDP prove 2026-09-15; "
        "live QN drifted toward forbid Q10408 label"
    ),
    "live_qn_drifted_toward": "Q10408",
    "pass": False,
    "contours_never_landed": True,
    "invent": False,
    "invent_contours": False,
    "invent_internaldata": False,
    "do_not_remint_quote_number": True,
    "do_not_forbid_part_number": True,
    "do_not_patch": True,
    "protect": True,
}


def q10450_35146_1_contours_never_landed() -> dict[str, Any]:
    """Read-only Q10450 leftover. No invented Contours."""
    return dict(Q10450_35146_1_CONTOURS_NEVER_LANDED)
