"""Spent P904272-1 — ZZ-DEL before classify @ 0163ffd Login fail.

Leftover EDIT still painted the amtech footer after
``.AspNet.ApplicationCookie`` died. Mint navigated, session was Login,
quote was ZZ-DEL before classify→Finish. Do not remint P904272-1 /
30f50f96. Require in-page GET /Quote 200 before mint.

Leave a7d6ca50. Do not remint 35145-1 / Q10243 / 21785-1/2/3.
"""

from __future__ import annotations

from typing import Any

LOOM_COMMIT = "0163ffd"
SPENT_QUOTE_ID_PREFIX = "30f50f96"
SPENT_QUOTE_NUMBER = "P904272-1"

LIVE_P904272_1 = {
    "quote_id_prefix": SPENT_QUOTE_ID_PREFIX,
    "quote_number": SPENT_QUOTE_NUMBER,
    "readonly": True,
    "zz_del": True,
    "classify_ran": False,
    "finish_posted": False,
    "edit_footer_amtech": True,
    "aspnet_cookie_live": False,
    "quotes_fetch_status": 302,
    "quotes_fetch_200": False,
    "login_after_mint_navigate": True,
}


def live_p904272_1_session_dump() -> dict[str, Any]:
    return dict(LIVE_P904272_1)
