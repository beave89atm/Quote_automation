"""Q10358 / 34328-1 keep-grid prove — InternalData empty after Cad+inches.

Live tip 4cc4481: keep_grid_via=live, live_grid_n=3, Cad×3 after
SetPartMode/UpdateItemType — kids retained (keep-grid works). Finish
EXEC_FAIL: FileList InternalData empty after explode → refused
AddItem_DXFFiles. invent=false. ZZ-DEL'd. Do not remint Q10358.

Contrast: single-plate Safe Cave Contours PASSes Q10344/46/48/49/51
fill Contours after Kyle UI Cad+inches in Adjust Properties. Multi-kid
keep-grid skips that page_fn (Q10355 first-child edit wipes
#gridDXFParts).

Hypothesis discarded: single-plate automation does not fire
CadImport/Data or GetBorderSize as a Contours fill. Overlay GET Data
is copy-if-nonempty (same path single and multi, now also after
Cad+inches). GetBorderSize is a thickness companion (Q10335 Contours 0;
21839-1 full trail still empty). Missing call stays
POST /part/create t.List InternalData+ImageString.

Do not invent Contours / InternalData. Do not forbid 34328-1 (PO may
remint the PN). Q10358 number is spent.
"""

from __future__ import annotations

from typing import Any

from secturafab.website import (
    CAD_INTERNALDATA_EMPTY_AFTER_EXPLODE,
    STEP_CAD_FINISH_HARD_GATE_EXEC_FAIL,
    STEP_CONTOURS_FILL_UNLOCKED,
    STEP_CONTOURS_MISSING_CALL,
    STEP_EXPLODE_NO_INTERNALDATA,
)

Q10358_34328_1_KEEP_GRID_PROVE: dict[str, Any] = {
    "quote_number": "Q10358",
    "part_number": "34328-1",
    "customer": "Time Manufacturing Waco",
    "id_unknown": True,
    "quote_id": None,
    "live_probe_tip": "4cc4481",
    "keep_grid_via": "live",
    "live_grid_n": 3,
    "cad_after_setpartmode": 3,
    "keep_grid_works": True,
    "cad_inches_on_kids": True,
    "internaldata_empty_after_explode": True,
    "finish_refused": True,
    "finish_why": CAD_INTERNALDATA_EMPTY_AFTER_EXPLODE,
    "step_explode_no_internaldata": STEP_EXPLODE_NO_INTERNALDATA,
    "exec_fail": STEP_CAD_FINISH_HARD_GATE_EXEC_FAIL,
    "missing_call": STEP_CONTOURS_MISSING_CALL,
    "invent": False,
    "invent_contours": False,
    "invent_internaldata": False,
    "fill_unlocked": STEP_CONTOURS_FILL_UNLOCKED,
    "unlocks_automation_contours_fill": False,
    "hypothesis_data_getbordersize_is_fill": False,
    "hypothesis_discarded": True,
    "single_plate_pass_contrast": (
        "Q10344",
        "Q10346",
        "Q10348",
        "Q10349",
        "Q10351",
    ),
    "not_grid_loss": True,
    "not_q10355_wipe": True,
    "zz_del": True,
    "zz_del_number": "ZZ-DEL-Q10358",
    "do_not_remint_quote_number": True,
    "do_not_forbid_part_number": True,
    "do_not_patch": True,
}


def q10358_34328_1_keep_grid_prove() -> dict[str, Any]:
    """Read-only Q10358 keep-grid prove. No invented InternalData."""
    out = dict(Q10358_34328_1_KEEP_GRID_PROVE)
    out["single_plate_pass_contrast"] = tuple(
        Q10358_34328_1_KEEP_GRID_PROVE["single_plate_pass_contrast"]
    )
    return out
