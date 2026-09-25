"""Q10377 / 1008399-1 Time Boom Rest mixed classify PASS leftover.

Live tip 8f5d17c: NEW remint PASS — Cad Contours + Long/Linear +
Component. invent=false. Complete Quote NOT DONE.

Per-kid (stated only; do not invent Contours / InternalData):
- Plate 1008400-1: Cad, A572 G50, .375-3/8", NumberOfContours=1
  (Finish→tree verify)
- Bar 31454-1: Long/Linear Saw, IsLinear=true
- Hardware 40003 / 40006: IsComponent=true

Never remint / PATCH Q10377. Do not forbid 1008399-1 (PN remint).
"""

from __future__ import annotations

from typing import Any

Q10377_QUOTE_ID = "12bd2530-e6ed-4792-9e47-bdd20fff1e70"
Q10377_QUOTE_ID_PREFIX = "12bd2530"

Q10377_1008399_1_MIXED_CLASSIFY_PASS: dict[str, Any] = {
    "quote_number": "Q10377",
    "quote_id": Q10377_QUOTE_ID,
    "part_number": "1008399-1",
    "job": "Time Boom Rest",
    "live_probe_tip": "8f5d17c",
    "complete_quote_done": False,
    "pass": True,
    "mixed_classify": True,
    "kids": (
        {
            "name": "1008400-1",
            "classify": "Cad",
            "material": "A572 G50",
            "thickness_label": '.375-3/8"',
            "is_plate": True,
            "number_of_contours": 1,
            "finish_tree_verify": True,
            "number_of_contours_ge1": True,
            "contours_path": True,
        },
        {
            "name": "31454-1",
            "classify": "Long/Linear",
            "machine": "Saw",
            "is_plate": False,
            "is_bar": True,
            "is_linear": True,
            "contours_path": False,
        },
        {
            "name": "40003",
            "classify": "Component",
            "is_plate": False,
            "is_hardware": True,
            "is_component": True,
            "contours_path": False,
        },
        {
            "name": "40006",
            "classify": "Component",
            "is_plate": False,
            "is_hardware": True,
            "is_component": True,
            "contours_path": False,
        },
    ),
    "contours_ge1_laser_gate_applies_to": "plate_sheet_cad_kids",
    "invent": False,
    "invent_contours": False,
    "invent_internaldata": False,
    "do_not_remint_quote_number": True,
    "do_not_forbid_part_number": True,
    "do_not_patch": True,
    "protect": True,
}


def q10377_1008399_1_mixed_classify_pass() -> dict[str, Any]:
    """Read-only Q10377 mixed classify PASS leftover. No invented Contours."""
    out = dict(Q10377_1008399_1_MIXED_CLASSIFY_PASS)
    out["kids"] = [dict(row) for row in Q10377_1008399_1_MIXED_CLASSIFY_PASS["kids"]]
    return out
