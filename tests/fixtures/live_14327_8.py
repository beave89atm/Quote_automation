"""Spent 14327-8 — leftover 1cd941c6 after empty-InternalData Contours FAIL.

Live capture @ 7b59ff0 (emptiness / key names only — no Contours JSON):

    mint 14327-8
      → POST /part/create InternalData empty
      → Finish refused (invented=false)
      → ZZ-DEL-14327-8

Same pattern as leftover 14327-5 / c5cd8689. QuoteOrderEdit has no extra
CadImport/UI fill XHR. Exact missing call is server
``POST /part/create t.List InternalData+ImageString``. Do not invent
Contours / InternalData. Do not remint / PATCH 14327-8 / 1cd941c6 /
ZZ-DEL-14327-8.
"""

from __future__ import annotations

from typing import Any

SPENT_QUOTE_ID = "1cd941c6-9167-41e9-ac93-b7268f18f282"
SPENT_QUOTE_ID_PREFIX = "1cd941c6"
SPENT_QUOTE_NUMBER = "14327-8"
SPENT_ZZ_DEL_NUMBER = "ZZ-DEL-14327-8"

LIVE_14327_8_CAPTURE: dict[str, Any] = {
    "quote_id": SPENT_QUOTE_ID,
    "quote_id_prefix": SPENT_QUOTE_ID_PREFIX,
    "quote_number": SPENT_QUOTE_NUMBER,
    "zz_del_number": SPENT_ZZ_DEL_NUMBER,
    "readonly": True,
    "zz_del": True,
    "same_pattern_as": "14327-5",
    "finish_posted": False,
    "finish_refused": True,
    "finish_why": "cad_internaldata_empty_after_explode",
    "step_explode_no_internaldata": True,
    "tlist_bind_source": False,
    "internaldata_empty": True,
    "contours_empty": True,
    "contours_never_filled": True,
    "invent": False,
    "unlocks_contours_fill": False,
    "fail_close": True,
    "no_extra_cadimport_xhr": True,
    "missing_call": "POST /part/create t.List InternalData+ImageString",
}


def leftover_14327_8_dump() -> dict[str, Any]:
    """Read-only 14327-8 emptiness. Does not unlock Contours fill."""
    return dict(LIVE_14327_8_CAPTURE)
