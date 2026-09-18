"""Q10407 / Q10408 Safe Cave List=[] leftovers.

Prefix-only (full GUIDs not restated). invent=false.
Never remint / PATCH. Not golds / not PASS protects.
"""

from __future__ import annotations

from typing import Any

Q10407_QUOTE_ID_PREFIX = "d796cdbe"
Q10408_QUOTE_ID_PREFIX = "09bae33d"

Q10407_SAFE_CAVE_LIST_EMPTY: dict[str, Any] = {
    "quote_number": "Q10407",
    "quote_id_prefix": Q10407_QUOTE_ID_PREFIX,
    "customer": "Safe Cave",
    "list_empty": True,
    "itemlist": [],
    "invent": False,
    "do_not_remint_quote_number": True,
    "do_not_patch": True,
    "protect": True,
}

Q10408_SAFE_CAVE_LIST_EMPTY: dict[str, Any] = {
    "quote_number": "Q10408",
    "quote_id_prefix": Q10408_QUOTE_ID_PREFIX,
    "customer": "Safe Cave",
    "list_empty": True,
    "itemlist": [],
    "invent": False,
    "do_not_remint_quote_number": True,
    "do_not_patch": True,
    "protect": True,
}


def q10407_safe_cave_list_empty() -> dict[str, Any]:
    """Read-only Q10407 Safe Cave List=[] leftover."""
    out = dict(Q10407_SAFE_CAVE_LIST_EMPTY)
    out["itemlist"] = list(Q10407_SAFE_CAVE_LIST_EMPTY["itemlist"])
    return out


def q10408_safe_cave_list_empty() -> dict[str, Any]:
    """Read-only Q10408 Safe Cave List=[] leftover."""
    out = dict(Q10408_SAFE_CAVE_LIST_EMPTY)
    out["itemlist"] = list(Q10408_SAFE_CAVE_LIST_EMPTY["itemlist"])
    return out
