"""Q10382 / 35146-1 Jib Turret mixed classify PASS leftover.

Live tip 86906b7: NEW remint PASS — 2 plate Cad Contours + CT
Long/Linear. invent=false. Complete Quote NOT DONE. OPEN-NEW draft
(CAD Finish ≠ Complete Quote).

Per-kid (stated only; do not invent Contours / InternalData):
- Plate 35123: Cad, DOMEX, .1875, NumberOfContours=1
- Plate 35125: Cad, DOMEX, 10GA, NumberOfContours=1
- Tube 35124: Long/Linear CT, IsLinear, A513 4.25×3.75×6.25

Never remint / PATCH Q10382. Do not forbid 35146-1 (PN remint).
"""

from __future__ import annotations

from typing import Any

Q10382_QUOTE_ID = "2d42dcc3-76e3-439b-be02-32c2f1b3c9a2"
Q10382_QUOTE_ID_PREFIX = "2d42dcc3"

Q10382_35146_1_MIXED_CLASSIFY_PASS: dict[str, Any] = {
    "quote_number": "Q10382",
    "quote_id": Q10382_QUOTE_ID,
    "part_number": "35146-1",
    "job": "Jib Turret",
    "live_probe_tip": "86906b7",
    "complete_quote_done": False,
    "open_new_draft": True,
    "complete_quote_note": "OPEN-NEW (CAD Finish ≠ Complete Quote)",
    "pass": True,
    "mixed_classify": True,
    "kids": (
        {
            "name": "35123",
            "classify": "Cad",
            "material": "DOMEX",
            "thickness_in": 0.1875,
            "thickness_label": ".1875",
            "is_plate": True,
            "number_of_contours": 1,
            "number_of_contours_ge1": True,
            "contours_path": True,
        },
        {
            "name": "35125",
            "classify": "Cad",
            "material": "DOMEX",
            "thickness_label": "10GA",
            "is_plate": True,
            "number_of_contours": 1,
            "number_of_contours_ge1": True,
            "contours_path": True,
        },
        {
            "name": "35124",
            "classify": "Long/Linear",
            "shape": "tube",
            "label": "CT",
            "material": "A513",
            "size_label": "4.25×3.75×6.25",
            "is_plate": False,
            "is_tube": True,
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


def q10382_35146_1_mixed_classify_pass() -> dict[str, Any]:
    """Read-only Q10382 mixed classify PASS leftover. No invented Contours."""
    out = dict(Q10382_35146_1_MIXED_CLASSIFY_PASS)
    out["kids"] = [dict(row) for row in Q10382_35146_1_MIXED_CLASSIFY_PASS["kids"]]
    return out
