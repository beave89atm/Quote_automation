"""Spent 28768-1 — ZZ-DEL after empty-InternalData Cad page Finish @ f656655.

Live unused Time plate STEP: chrome_ok, Quotes fetch 200, PartMode Cad
via page_fn, page OnAddDXFClick fired (FileList n=1, HTTP 200).
GET item_count=0 / no Cad Contours/PR/laser.

Posted FileList: InternalData null, OutsidePerimeter 0, ProductSubType
bar_flat on Cad PartMode 0 / ProductType 100. Stock_X=3 Stock_Y=3
Stock_Z=14.5 (bar-like). ImageString preview only.

Kyle Loom c9d7 Cad plates Finish with real explode profile geometry.
Do not invent Contours/InternalData. Do not remint 28768-1 / 28708035.
"""

from __future__ import annotations

from typing import Any

CAPTURE_COMMIT = "f656655"
SPENT_QUOTE_ID_PREFIX = "28708035"
SPENT_QUOTE_NUMBER = "28768-1"

LIVE_28768_1 = {
    "quote_id_prefix": SPENT_QUOTE_ID_PREFIX,
    "quote_number": SPENT_QUOTE_NUMBER,
    "readonly": True,
    "zz_del": True,
    "partmode_cad": True,
    "page_finish": True,
    "finish_fn": "OnAddDXFClick",
    "finish_http_200": True,
    "filelist_n": 1,
    "internaldata_empty": True,
    "outsideperimeter": 0,
    "productsubtype": "bar_flat",
    "producttype": "100",
    "get_cad": 0,
}


def live_28768_1_finish_dump() -> dict[str, Any]:
    return dict(LIVE_28768_1)
