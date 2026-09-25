"""Q10379 / 11643-1 Platform Mount mixed classify PASS leftover.

Live tip d34b5b4: NEW remint PASS — plate Cad Contours + tube/slug
Long/Linear. invent=false. Complete Quote NOT DONE. OPEN-NEW draft
(CAD Finish ≠ Complete Quote).

Per-kid (stated only; do not invent Contours / InternalData):
- Plate 11640-1: Cad, A572 G50, .25, NumberOfContours=1
- Plate 11642-2: Cad, A36, .375, NumberOfContours=1
- Tube 11641-1: Long/Linear tube_round, IsLinear, A513 2.00×1.50×7.4375
- Slug 32070-1: Long/Linear bar_round, IsLinear, C1018 2.00×0.45

Never remint / PATCH Q10379. Do not forbid 11643-1 (PN remint).
"""

from __future__ import annotations

from typing import Any

Q10379_QUOTE_ID = "70e69d9c-9d9f-4b2e-b7f1-7ac9ae80da9e"
Q10379_QUOTE_ID_PREFIX = "70e69d9c"

Q10379_11643_1_MIXED_CLASSIFY_PASS: dict[str, Any] = {
    "quote_number": "Q10379",
    "quote_id": Q10379_QUOTE_ID,
    "part_number": "11643-1",
    "job": "Platform Mount",
    "live_probe_tip": "d34b5b4",
    "complete_quote_done": False,
    "open_new_draft": True,
    "complete_quote_note": "OPEN-NEW (CAD Finish ≠ Complete Quote)",
    "pass": True,
    "mixed_classify": True,
    "kids": (
        {
            "name": "11640-1",
            "classify": "Cad",
            "material": "A572 G50",
            "thickness_in": 0.25,
            "thickness_label": ".25",
            "is_plate": True,
            "number_of_contours": 1,
            "number_of_contours_ge1": True,
            "contours_path": True,
        },
        {
            "name": "11642-2",
            "classify": "Cad",
            "material": "A36",
            "thickness_in": 0.375,
            "thickness_label": ".375",
            "is_plate": True,
            "number_of_contours": 1,
            "number_of_contours_ge1": True,
            "contours_path": True,
        },
        {
            "name": "11641-1",
            "classify": "Long/Linear",
            "shape": "tube_round",
            "material": "A513",
            "size_label": "2.00×1.50×7.4375",
            "is_plate": False,
            "is_tube": True,
            "is_linear": True,
            "contours_path": False,
        },
        {
            "name": "32070-1",
            "classify": "Long/Linear",
            "shape": "bar_round",
            "material": "C1018",
            "size_label": "2.00×0.45",
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


def q10379_11643_1_mixed_classify_pass() -> dict[str, Any]:
    """Read-only Q10379 mixed classify PASS leftover. No invented Contours."""
    out = dict(Q10379_11643_1_MIXED_CLASSIFY_PASS)
    out["kids"] = [dict(row) for row in Q10379_11643_1_MIXED_CLASSIFY_PASS["kids"]]
    return out
