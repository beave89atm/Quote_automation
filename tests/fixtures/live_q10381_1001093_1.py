"""Q10381 / 1001093-1 Hose Guide mixed classify PASS leftover.

Live tip 6fefaac: NEW remint PASS — 3 plate Cad Contours + RD BAR
Long/Linear. invent=false. Complete Quote NOT DONE. OPEN-NEW draft
(CAD Finish ≠ Complete Quote).

Per-kid (stated only; do not invent Contours / InternalData):
- Plate 1000480: Cad, A572 G50, .1875-3/16, NumberOfContours=1
- Plate 1001090: Cad, A572 G50, .1875-3/16, NumberOfContours=1
- Plate 1001091: Cad, A572 G50, .1875-3/16, NumberOfContours=1
- Bar 1001092-1: Long/Linear RD BAR, IsLinear, CRS/CR1018 .188 × 5.5625

Never remint / PATCH Q10381. Do not forbid 1001093-1 (PN remint).
"""

from __future__ import annotations

from typing import Any

Q10381_QUOTE_ID = "bb31a132-c93a-4c21-84f3-7a83c62cead6"
Q10381_QUOTE_ID_PREFIX = "bb31a132"

Q10381_1001093_1_MIXED_CLASSIFY_PASS: dict[str, Any] = {
    "quote_number": "Q10381",
    "quote_id": Q10381_QUOTE_ID,
    "part_number": "1001093-1",
    "job": "Hose Guide",
    "live_probe_tip": "6fefaac",
    "complete_quote_done": False,
    "open_new_draft": True,
    "complete_quote_note": "OPEN-NEW (CAD Finish ≠ Complete Quote)",
    "pass": True,
    "mixed_classify": True,
    "kids": (
        {
            "name": "1000480",
            "classify": "Cad",
            "material": "A572 G50",
            "thickness_in": 0.1875,
            "thickness_label": ".1875-3/16",
            "is_plate": True,
            "number_of_contours": 1,
            "number_of_contours_ge1": True,
            "contours_path": True,
        },
        {
            "name": "1001090",
            "classify": "Cad",
            "material": "A572 G50",
            "thickness_in": 0.1875,
            "thickness_label": ".1875-3/16",
            "is_plate": True,
            "number_of_contours": 1,
            "number_of_contours_ge1": True,
            "contours_path": True,
        },
        {
            "name": "1001091",
            "classify": "Cad",
            "material": "A572 G50",
            "thickness_in": 0.1875,
            "thickness_label": ".1875-3/16",
            "is_plate": True,
            "number_of_contours": 1,
            "number_of_contours_ge1": True,
            "contours_path": True,
        },
        {
            "name": "1001092-1",
            "classify": "Long/Linear",
            "shape": "bar_round",
            "label": "RD BAR",
            "material": "CRS/CR1018",
            "size_label": ".188 × 5.5625",
            "is_plate": False,
            "is_bar": True,
            "is_linear": True,
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


def q10381_1001093_1_mixed_classify_pass() -> dict[str, Any]:
    """Read-only Q10381 mixed classify PASS leftover. No invented Contours."""
    out = dict(Q10381_1001093_1_MIXED_CLASSIFY_PASS)
    out["kids"] = [dict(row) for row in Q10381_1001093_1_MIXED_CLASSIFY_PASS["kids"]]
    return out
