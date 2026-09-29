"""Q10372 / 34328-1 Time weldment Contours remint — EXEC_FAIL leftover.

Live tip d2616fc: remint EXEC_FAIL; Complete Quote NOT DONE. invent=false.

Per-kid:
- HOOK 31454-1 Contours=0 (was mistreated as A36/.50 plate)
- 34329 Contours=1 at A36/.25 gauge-list

Drawing truth for HOOK: RD BAR CR 1018, 1/2 DIA — NOT plate.
Contours≥1 Laser gate applies to plate/sheet Cad kids. Round-bar
kids (RD BAR) are a different ops path; Contours=0 with
Material+thickness set is expected until Profile/Saw/bar path
exists. invent=false still.

Never remint / PATCH Q10372. Do not forbid 34328-1 (PO remint).
Do not invent Contours / InternalData.
"""

from __future__ import annotations

from typing import Any

from secturafab.website import STEP_CAD_FINISH_HARD_GATE_EXEC_FAIL

Q10372_QUOTE_ID = "d62e2ad1-7324-4034-a44e-cbd7a3acee9d"
Q10372_QUOTE_ID_PREFIX = "d62e2ad1"

Q10372_34328_1_CONTOURS_FAIL: dict[str, Any] = {
    "quote_number": "Q10372",
    "quote_id": Q10372_QUOTE_ID,
    "part_number": "34328-1",
    "customer": "Time Manufacturing Waco",
    "live_probe_tip": "d2616fc",
    "complete_quote_done": False,
    "exec_fail": STEP_CAD_FINISH_HARD_GATE_EXEC_FAIL,
    "kids": (
        {
            "name": "HOOK 31454-1",
            "drawing_stock": "RD BAR CR 1018",
            "drawing_size": "1/2 DIA",
            "mistreated_as": "A36/.50 plate",
            "is_plate": False,
            "number_of_contours": 0,
            "contours_zero_expected_until_bar_path": True,
        },
        {
            "name": "34329",
            "material": "A36",
            "thickness_in": 0.25,
            "gauge_list": True,
            "is_plate": True,
            "number_of_contours": 1,
        },
    ),
    "contours_ge1_laser_gate_applies_to": "plate_sheet_cad_kids",
    "rd_bar_ops_path": "profile_saw_bar_not_yet",
    "invent": False,
    "invent_contours": False,
    "invent_internaldata": False,
    "do_not_remint_quote_number": True,
    "do_not_forbid_part_number": True,
    "do_not_patch": True,
}


def q10372_34328_1_contours_fail() -> dict[str, Any]:
    """Read-only Q10372 remint findings. No invented Contours."""
    out = dict(Q10372_34328_1_CONTOURS_FAIL)
    out["kids"] = [dict(row) for row in Q10372_34328_1_CONTOURS_FAIL["kids"]]
    return out
