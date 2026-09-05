"""107877-1 first /part/create FileList — unnamed + GATE/REST WELDMENT (1e76c96).

Do not PATCH quote e2cc0a7d-90fa-4629-b48f-db1e8163557b / 107877-1.
Cited unique names: Root, 26× ``-28656``, 11× GATE WELDMENT, 2× REST WELDMENT.
No plate/tube nouns. Re-explode must use child ID/FileID when SourceDataID
is the pass-1 upload id.
"""

from __future__ import annotations

LIVE_107877_NESTED_NAMES: list[str] = (
    ["Root"]
    + ["-28656"] * 26
    + ["GATE WELDMENT-2640_103535-1"] * 11
    + ["REST WELDMENT-2742_105094-1"] * 2
)

LIVE_107877_LEAF_NAMES: list[str] = [
    "FLOOR PLATE",
    "REST GUSSET",
    "GATE TUBE",
    "RAIL MOUNT",
    "GATE WELDMENT-2640_103535-1",
]
