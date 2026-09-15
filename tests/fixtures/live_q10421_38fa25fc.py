"""Q10421 / 38fa25fc prior burn leftover — Q10421→Q10407 drift.

Prefix-only: full UUID not found in repo, git history, or Dropbox.
Never remint / PATCH that UUID. invent=false.
Do not invent Contours / InternalData.
Do not forbid 35146-1 (PN remint).
"""

from __future__ import annotations

from typing import Any

Q10421_QUOTE_ID_PREFIX = "38fa25fc"

Q10421_38FA25FC_DRIFT: dict[str, Any] = {
    "quote_number": "Q10421",
    "quote_id_prefix": Q10421_QUOTE_ID_PREFIX,
    "full_uuid_found": False,
    "full_uuid": None,
    "prior_burn": "Q10421→Q10407 drift",
    "drifted_toward": "Q10407",
    "invent": False,
    "invent_contours": False,
    "invent_internaldata": False,
    "do_not_remint_quote_number": True,
    "do_not_forbid_part_number": True,
    "do_not_patch": True,
    "protect": True,
}


def q10421_38fa25fc_drift() -> dict[str, Any]:
    """Read-only Q10421 prefix leftover. No invented Contours or full UUID."""
    return dict(Q10421_38FA25FC_DRIFT)
