"""28110-2 first /part/create FileList — nested ASSY/WELDMENT only (6c02c08).

Do not PATCH quote 75b3a938-ff89-4525-80d9-c6000d055a48 / 28110-2.
These names are the one-level nest cited on that live FAIL. Leaf plate/tube
nouns were missing; Finish 200 + GET ItemList 0. Used only as explode fixtures.
"""

from __future__ import annotations

# Cited live names plus additional ASSY/WELDMENT titles to make FileList=15.
LIVE_28110_NESTED_NAMES: list[str] = [
    "Root",
    "28110-2",
    "28109 COMP LINK ASSY WITH INSERT-5997_28109-1",
    "28248 COMPLINK END WELDMENT INSULATED-5994_28248-2",
    "28248 COMPLINK END WELDMENT INSULATED-5994_28248-3",
    "28109 COMP LINK ASSY WITH INSERT-5997_28109-2",
    "28248 COMPLINK CENTER WELDMENT-5995_28248-4",
    "28247 COMP LINK ASSY-5996_28247-1",
    "28249 END WELDMENT-5993_28249-1",
    "28250 COMPLINK ASSY INSULATED-5992_28250-1",
    "28251 LINK WELDMENT-5991_28251-1",
    "28252 COMP LINK ASSEMBLY-5990_28252-1",
    "28253 INSERT ASSY-5989_28253-1",
    "28254 END WELDMENT INSULATED-5988_28254-1",
    "28255 COMPLINK ASSY-5987_28255-1",
]

# Second /part/create kids — leaf Cad/Linear nouns + remaining WELDMENT.
LIVE_28110_LEAF_NAMES: list[str] = [
    "LINK PLATE",
    "INSERT GUSSET",
    "END TUBE",
    "MOUNT PLATE",
    "28248 COMPLINK END WELDMENT INSULATED-5994_28248-2",
]
