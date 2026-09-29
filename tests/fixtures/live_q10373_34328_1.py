"""Q10373 / 34328-1 Time weldment mixed classify PASS leftover.

Live tip 1650cf5: NEW remint PASS — mixed classify prove.
invent=false. Complete Quote NOT DONE. OPEN-NEW draft.

Per-kid (stated only; do not invent Contours / InternalData):
- Plate 34329: Cad, A36, .25-1/4" gauge, Laser, NumberOfContours≥1
- Bar 31454-1 HOOK: Long/Linear Hot Rolled Round Bar, CRS
  (closest to RD BAR CR 1018), 0.5" × 4.375", Saw; no Contours path

Never remint / PATCH Q10373. Do not forbid 34328-1 (PO remint).
"""

from __future__ import annotations

from typing import Any

Q10373_QUOTE_ID = "523d8328-f310-434d-a502-00502c987dd2"
Q10373_QUOTE_ID_PREFIX = "523d8328"

Q10373_34328_1_MIXED_CLASSIFY_PASS: dict[str, Any] = {
    "quote_number": "Q10373",
    "quote_id": Q10373_QUOTE_ID,
    "part_number": "34328-1",
    "customer": "Time Manufacturing Waco",
    "live_probe_tip": "1650cf5",
    "complete_quote_done": False,
    "open_new_draft": True,
    "pass": True,
    "mixed_classify": True,
    "kids": (
        {
            "name": "34329",
            "classify": "Cad",
            "material": "A36",
            "thickness_in": 0.25,
            "thickness_label": '.25-1/4"',
            "gauge_list": True,
            "machine": "Laser",
            "is_plate": True,
            "number_of_contours_ge1": True,
            "contours_path": True,
        },
        {
            "name": "HOOK 31454-1",
            "classify": "Long/Linear",
            "shape": "Hot Rolled Round Bar",
            "material": "CRS",
            "drawing_stock": "RD BAR CR 1018",
            "drawing_stock_note": "CRS closest to RD BAR CR 1018",
            "diameter_in": 0.5,
            "length_in": 4.375,
            "machine": "Saw",
            "is_plate": False,
            "is_bar": True,
            "is_linear": True,
            "contours_path": False,
        },
    ),
    "contours_ge1_laser_gate_applies_to": "plate_sheet_cad_kids",
    "rd_bar_ops_path": "long_linear_hot_rolled_round_bar_saw",
    "invent": False,
    "invent_contours": False,
    "invent_internaldata": False,
    "do_not_remint_quote_number": True,
    "do_not_forbid_part_number": True,
    "do_not_patch": True,
    "protect": True,
}


def q10373_34328_1_mixed_classify_pass() -> dict[str, Any]:
    """Read-only Q10373 mixed classify PASS leftover. No invented Contours."""
    out = dict(Q10373_34328_1_MIXED_CLASSIFY_PASS)
    out["kids"] = [dict(row) for row in Q10373_34328_1_MIXED_CLASSIFY_PASS["kids"]]
    return out
