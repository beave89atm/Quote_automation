"""Q10368 / 34328-1 keep-grid Material remint — Contours 0/1/0.

Live tip 8d4626a: keep-grid Material worked. 3 Cad kids all A36 +
per-kid thickness through Finish. Contours 0/1/0. invent=false.

PASS: 34329 BOOM SUPPORT A36 0.25in Contours=1
FAIL: two HOOK BOOM REST-7742_31454-1 A36 0.5in Contours=0

Findings (no Contours invent):
1. Thickness is per-row (0.25 vs 0.5), not one drawing gauge stamped
   on every kid. 0.5in is still ≤ 3/4 laser Cad class.
2. Two FAIL kids share the same explode name — duplicate instances,
   not two drawing PNs. Do not collapse them (would weaken the
   every-Cad-kid Contours≥1 gate).
3. HOOK BOOM REST is not a plate/sheet noun and not a Linear hint.
   0.5in is below flat_bar min 0.76in, so stock classify stays Cad.
   Do not reclass Long on the name alone.

Cad+Material+inches ≠ Contours fill on every kid. Finish filled the
flattenable 0.25in plate and left the HOOK solids at 0. Fill XHR
still unnamed. Post-Finish gate stays every Cad kid ≥1; Q10368
adds per-kid names in the EXEC_FAIL. Never remint / PATCH Q10368.
Do not forbid 34328-1 (PO may remint the PN).
"""

from __future__ import annotations

from typing import Any

from secturafab.website import STEP_CAD_FINISH_HARD_GATE_EXEC_FAIL

Q10368_QUOTE_ID = "5e0ce1df-e18b-4118-945a-8be85378069e"
Q10368_QUOTE_ID_PREFIX = "5e0ce1df"

Q10368_34328_1_KEEP_GRID_MATERIAL: dict[str, Any] = {
    "quote_number": "Q10368",
    "quote_id": Q10368_QUOTE_ID,
    "part_number": "34328-1",
    "customer": "Time Manufacturing Waco",
    "live_probe_tip": "8d4626a",
    "keep_grid_material_worked": True,
    "cad_kids": 3,
    "material": "A36",
    "contours": (0, 1, 0),
    "pass_kid": {
        "name": "34329 BOOM SUPPORT",
        "material": "A36",
        "thickness_in": 0.25,
        "number_of_contours": 1,
    },
    "fail_kids": (
        {
            "name": "HOOK BOOM REST-7742_31454-1",
            "material": "A36",
            "thickness_in": 0.5,
            "number_of_contours": 0,
        },
        {
            "name": "HOOK BOOM REST-7742_31454-1",
            "material": "A36",
            "thickness_in": 0.5,
            "number_of_contours": 0,
        },
    ),
    "thickness_from_drawing_stamped_on_all": False,
    "duplicate_explode_same_name": True,
    "hook_should_be_long": False,
    "hook_class": "Cad",
    "flat_bar_min_in": 0.76,
    "invent": False,
    "invent_contours": False,
    "invent_internaldata": False,
    "exec_fail": STEP_CAD_FINISH_HARD_GATE_EXEC_FAIL,
    "do_not_remint_quote_number": True,
    "do_not_forbid_part_number": True,
    "do_not_patch": True,
    "do_not_weaken_every_cad_kid_gate": True,
}


def q10368_34328_1_keep_grid_material() -> dict[str, Any]:
    """Read-only Q10368 remint findings. No invented Contours."""
    out = dict(Q10368_34328_1_KEEP_GRID_MATERIAL)
    out["pass_kid"] = dict(Q10368_34328_1_KEEP_GRID_MATERIAL["pass_kid"])
    out["fail_kids"] = [
        dict(row) for row in Q10368_34328_1_KEEP_GRID_MATERIAL["fail_kids"]
    ]
    return out
