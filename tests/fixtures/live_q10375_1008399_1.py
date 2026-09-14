"""Q10375 / 1008399-1 remint — Contours EXEC_FAIL leftover.

Live tip 6a4f536: remint EXEC_FAIL. Cad/A572 G50/.375-3/8 plate +
Linear Saw bar + Component hardware set. Contours≥1 not verified
(blank CAD editor). invent=false. Complete Quote NOT DONE.

Stated only. Do not invent Contours / InternalData.

Never remint / PATCH Q10375. Do not forbid 1008399-1 (PN remint).
"""

from __future__ import annotations

from typing import Any

from secturafab.website import STEP_CAD_FINISH_HARD_GATE_EXEC_FAIL

Q10375_QUOTE_ID = "60de939f-85f0-4f1a-9412-39c29211ad30"
Q10375_QUOTE_ID_PREFIX = "60de939f"

Q10375_1008399_1_CONTOURS_FAIL: dict[str, Any] = {
    "quote_number": "Q10375",
    "quote_id": Q10375_QUOTE_ID,
    "part_number": "1008399-1",
    "live_probe_tip": "6a4f536",
    "complete_quote_done": False,
    "exec_fail": STEP_CAD_FINISH_HARD_GATE_EXEC_FAIL,
    "contours_ge1_verified": False,
    "blank_cad_editor": True,
    "kids": (
        {
            "role": "plate",
            "classify": "Cad",
            "material": "A572 G50",
            "thickness_label": ".375-3/8",
            "is_plate": True,
            "contours_ge1_verified": False,
            "blank_cad_editor": True,
        },
        {
            "role": "bar",
            "classify": "Linear",
            "machine": "Saw",
            "is_plate": False,
            "is_bar": True,
            "is_linear": True,
            "contours_path": False,
        },
        {
            "role": "hardware",
            "classify": "Component",
            "is_plate": False,
            "is_hardware": True,
            "contours_path": False,
        },
    ),
    "invent": False,
    "invent_contours": False,
    "invent_internaldata": False,
    "do_not_remint_quote_number": True,
    "do_not_forbid_part_number": True,
    "do_not_patch": True,
}


def q10375_1008399_1_contours_fail() -> dict[str, Any]:
    """Read-only Q10375 remint leftover. No invented Contours."""
    out = dict(Q10375_1008399_1_CONTOURS_FAIL)
    out["kids"] = [dict(row) for row in Q10375_1008399_1_CONTOURS_FAIL["kids"]]
    return out
