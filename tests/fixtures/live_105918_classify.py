"""105918-1 FileList nouns from the live GET (do not PATCH that quote).

Finish stamped 66 lines as Component/Assembly. Kyle: leftover Component is
not the classify rule. These names are the STEP kids / nested weldments
cited on that GET — used only as classify fixtures.
"""

from __future__ import annotations

# (Name as on #gridDXFParts / ItemList Description, expected File type)
LIVE_105918_KID_NAMES: list[tuple[str, str]] = [
    ("105918-1", "Assembly"),
    ("PLATFORM BASE WELDMENT-2623_103603-1", "Assembly"),
    ("GATE WELDMENT-2640_103535-1", "Assembly"),
    ("SUPPORT WELDMENT-2720_103629-1", "Assembly"),
    ("REST WELDMENT-2742_105094-1", "Assembly"),
    ("PLATE-1297_30345-19", "Cad"),
    ("RAIL MOUNT", "Cad"),
    ("TRIANGLE GUSSET", "Cad"),
    ("FLOOR GUSSET", "Cad"),
    ("CHANNEL PLATE", "Cad"),
    ("ANCHOR PLATE", "Cad"),
    ("SUPPORT PLATE", "Cad"),
    ("gate gusset", "Cad"),
    ("KICK CHANNEL", "Linear"),
    ("vertical tube", "Linear"),
    ("main channel", "Linear"),
]
