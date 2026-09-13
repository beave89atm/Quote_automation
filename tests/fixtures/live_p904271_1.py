"""Spent P904271-1 — ZZ-DEL after classify @ 0163ffd InternalData refuse.

Live: classify/SetPartMode worked (Cad×3, kyle_classify_before_finish=true)
but Finish was refused because InternalData was still empty 3/3
(ImageString preview only). Kyle Loom c9d7 clicks green Finish after
Part Mode without on-screen InternalData — packs appear after Finish.

Do not remint P904271-1 / 0837ad33. Do not remint P904272-1 / 35145-1 /
21785-1/2/3. Leave a7d6ca50. Do not invent InternalData.
"""

from __future__ import annotations

from typing import Any

CAPTURE_COMMIT = "0163ffd"
SPENT_QUOTE_ID_PREFIX = "0837ad33"
SPENT_QUOTE_NUMBER = "P904271-1"

LIVE_P904271_1 = {
    "quote_id_prefix": SPENT_QUOTE_ID_PREFIX,
    "quote_number": SPENT_QUOTE_NUMBER,
    "readonly": True,
    "zz_del": True,
    "classify_ran": True,
    "cad_n": 3,
    "kyle_classify_before_finish": True,
    "internaldata_empty_n": 3,
    "imagestring_preview_only": True,
    "finish_posted": False,
    "finish_refused_too_early": True,
}


def live_p904271_1_classify_dump() -> dict[str, Any]:
    return dict(LIVE_P904271_1)
