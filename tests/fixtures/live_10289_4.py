"""Spent 10289-4 — ZZ-DEL after page Finish skip @ 2320c6d.

Live: PartMode Cad was set, then page OnAddDXFClick was skipped
(``finish_why=filelist_cad_payload_empty``). Reconstructed
AddItem_DXFFiles returned 200 empty body / GET 0 Cad.

Kyle Loom c9d7 clicks green Finish after Part Mode without filling
Cad L×W / CadType / InternalData on the classify grid. Packs stamp
after page Finish. Do not remint 10289-4 / 1004f017.

The page never posted a FileList body on this quote. Live FileList
shape (keys + nonempty names only) is in
``LIVE_ADDITEM_DXF_FILELIST_POST`` from 28768-1 @ f656655
(bar_flat + empty InternalData — refuse that Cad Finish).
Do not invent InternalData / CadType / Stock values.
"""

from __future__ import annotations

from typing import Any

CAPTURE_COMMIT = "2320c6d"
SPENT_QUOTE_ID_PREFIX = "1004f017"
SPENT_QUOTE_NUMBER = "10289-4"

LIVE_10289_4 = {
    "quote_id_prefix": SPENT_QUOTE_ID_PREFIX,
    "quote_number": SPENT_QUOTE_NUMBER,
    "readonly": True,
    "zz_del": True,
    "partmode_cad": True,
    "kyle_classify_before_finish": True,
    "finish_why": "filelist_cad_payload_empty",
    "page_finish": False,
    "reconstructed": True,
    "empty_body": True,
    "get_cad": 0,
}


def live_10289_4_skip_dump() -> dict[str, Any]:
    return dict(LIVE_10289_4)
