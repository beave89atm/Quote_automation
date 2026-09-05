"""Spent 29340-1 — API mint then cookie GetItem_AddView 302 / GET 0.

Minted 8fb3da71-1948-4da2-a70f-8ef06b78cf32. Image Files never ran.
Cookie GET /Quote/GetItem_AddView(pdf) 302 while Chrome 9224
*Quote-Q10xxx EDIT was signed in (not Login). Created via the old
API ("Created SecturaFAB quote" + Quote Request attachments) then
aborted Finish. Cookie HTTP that 302s is fail-closed. In-page
mint is not gated on the cookie file (live 34603-2 cookie 302
after Chrome refresh; CDP omitted .AspNet.ApplicationCookie).
Leave 8fb3da71. Do not PATCH. Do not remint 29340-1.
"""

from __future__ import annotations

from typing import Any

SPENT_QUOTE_ID = "8fb3da71-1948-4da2-a70f-8ef06b78cf32"
SPENT_QUOTE_NUMBER = "29340-1"
CHROME_TITLE = "*Quote-Q10xxx"

LEFTOVER_API_MINT_COOKIE_FINISH = {
    "quote_id": SPENT_QUOTE_ID,
    "quote_number": SPENT_QUOTE_NUMBER,
    "readonly": True,
    "itemlist_n": 0,
    "image_files_ran": False,
    "created_via": "api",
    "finish_via": "cookie_http",
    "getitem_addview": {
        "ItemType": "pdf",
        "status": 302,
        "path": "/Quote/GetItem_AddView",
    },
    "chrome_9224": {
        "title": CHROME_TITLE,
        "path": "/Quote/EDIT",
        "login": False,
        "signed_in": True,
    },
    "cookie_302_is_logout": False,
    "AddItem_PDFFiles": {
        "via": "cookie_http",
        "is_success": False,
        "skips_files_kendo": True,
    },
    "live_29340_1": {
        "itemlist_n": 0,
        "image_files_ran": False,
        "api_mint": True,
        "cookie_finish": True,
        "getitem_addview_302": True,
        "chrome_signed_in": True,
    },
}


def leftover_api_mint_cookie_finish_dump() -> dict[str, Any]:
    """Leftover: API mint + cookie AddView 302 + Image Files never ran."""
    return dict(LEFTOVER_API_MINT_COOKIE_FINISH)


def live_29340_1_quote() -> dict[str, Any]:
    """GET after abort: ItemList 0."""
    return {
        "ID": SPENT_QUOTE_ID,
        "QuoteNumber": SPENT_QUOTE_NUMBER,
        "ItemCount": 0,
        "ItemList": [],
    }
