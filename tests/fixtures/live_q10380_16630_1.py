"""Q10380 / 16630-1 Rotation Top Stop mixed classify PASS leftover.

Live tip 937b19c: NEW remint PASS — plate Cad Contours + CT/ring
Long/Linear. invent=false. Complete Quote NOT DONE. OPEN-NEW draft
(CAD Finish ≠ Complete Quote).

Per-kid (stated only; do not invent Contours / InternalData):
- Plate 16629-1 EAR: Cad, A36, .5-1/2", NumberOfContours=1, qty 2
- Ring 16628-1: Long/Linear tube, IsLinear, A513 7.25 OD × 6.0 ID
  × 1.69 L wall 0.625, qty 1

Never remint / PATCH Q10380. Do not forbid 16630-1 (PN remint).
"""

from __future__ import annotations

from typing import Any

Q10380_QUOTE_ID = "754089f2-fd55-4e3d-865c-8dffa63181fa"
Q10380_QUOTE_ID_PREFIX = "754089f2"

Q10380_16630_1_MIXED_CLASSIFY_PASS: dict[str, Any] = {
    "quote_number": "Q10380",
    "quote_id": Q10380_QUOTE_ID,
    "part_number": "16630-1",
    "job": "Rotation Top Stop",
    "live_probe_tip": "937b19c",
    "complete_quote_done": False,
    "open_new_draft": True,
    "complete_quote_note": "OPEN-NEW (CAD Finish ≠ Complete Quote)",
    "pass": True,
    "mixed_classify": True,
    "kids": (
        {
            "name": "16629-1",
            "label": "EAR",
            "classify": "Cad",
            "material": "A36",
            "thickness_in": 0.5,
            "thickness_label": '.5-1/2"',
            "qty": 2,
            "is_plate": True,
            "number_of_contours": 1,
            "number_of_contours_ge1": True,
            "contours_path": True,
        },
        {
            "name": "16628-1",
            "classify": "Long/Linear",
            "shape": "tube",
            "material": "A513",
            "size_label": "7.25 OD × 6.0 ID × 1.69 L wall 0.625",
            "qty": 1,
            "is_plate": False,
            "is_tube": True,
            "is_ring": True,
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


def q10380_16630_1_mixed_classify_pass() -> dict[str, Any]:
    """Read-only Q10380 mixed classify PASS leftover. No invented Contours."""
    out = dict(Q10380_16630_1_MIXED_CLASSIFY_PASS)
    out["kids"] = [dict(row) for row in Q10380_16630_1_MIXED_CLASSIFY_PASS["kids"]]
    return out
