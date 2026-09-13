"""Sprout GSB20570006 empty InternalData — outside H.6.38 / Time pick.

Live leftover (CoS hold):
  GSB20570006 / afee7458-6651-447e-ba1b-62c1c9c90ce8
           Sprout 1.1 piece part. Empty InternalData after full
           Cad+wizard mid-wizard (11 parts). Finish refused
           invent=false; ZZ-DEL-GSB20570006.

Same Sectura-side empty-InternalData refuse class as Time STEPs
28898-1 / 28772-1 / 14327-18 / 15911-9 / 21839-1, but this is
not a Time pick and not H.6.38 Contours-good (Q10333 / Q10336 /
Q10339). Do not invent Contours / InternalData. Never remint /
PATCH Q10333 / Q10336 / Q10338 / Q10339 / golds.
"""

from __future__ import annotations

from typing import Any

from secturafab.cadimport_js import CAD_FINISH_NAMED_XHR_SEQUENCE
from secturafab.website import (
    CAD_INTERNALDATA_EMPTY_AFTER_EXPLODE,
    STEP_CONTOURS_FILL_UNLOCKED,
)

SPROUT_EMPTY_INTERNALDATA_PN = "GSB20570006"
SPROUT_EMPTY_INTERNALDATA_QUOTE_ID = "afee7458-6651-447e-ba1b-62c1c9c90ce8"
SPROUT_EMPTY_INTERNALDATA_QUOTE_ID_PREFIX = "afee7458"
SPROUT_EMPTY_INTERNALDATA_ZZ_DEL = "ZZ-DEL-GSB20570006"

SPROUT_EMPTY_INTERNALDATA: dict[str, Any] = {
    "invent": False,
    "unlocks_automation_contours_fill": False,
    "fill_unlocked": STEP_CONTOURS_FILL_UNLOCKED,
    "outside_h638_family": True,
    "outside_time_pick": True,
    "h638_contours_good": ("Q10333", "Q10336", "Q10339"),
    "part_number": SPROUT_EMPTY_INTERNALDATA_PN,
    "customer": "Sprout",
    "piece_part": "1.1",
    "part_count": 11,
    "known_quote_id": SPROUT_EMPTY_INTERNALDATA_QUOTE_ID,
    "known_quote_id_prefix": SPROUT_EMPTY_INTERNALDATA_QUOTE_ID_PREFIX,
    "zz_del_number": SPROUT_EMPTY_INTERNALDATA_ZZ_DEL,
    "live_probe_tip": "2f6d74f",
    "cos_hold": True,
    "full_cad_wizard_mid_wizard": True,
    "internaldata_empty_after_full_trail": True,
    "finish_refused": True,
    "finish_why": CAD_INTERNALDATA_EMPTY_AFTER_EXPLODE,
    "named_cad_finish_xhr_sequence": CAD_FINISH_NAMED_XHR_SEQUENCE,
    "named_sequence_unlocks_fill": False,
    "do_not_remint": True,
    "do_not_patch": True,
    "same_class_as_time_steps": (
        "28898-1",
        "28772-1",
        "14327-18",
        "15911-9",
        "21839-1",
    ),
}


def sprout_empty_internaldata_dig() -> dict[str, Any]:
    """Read-only dig. No invented InternalData. Does not unlock fill."""
    out = dict(SPROUT_EMPTY_INTERNALDATA)
    out["same_class_as_time_steps"] = tuple(
        SPROUT_EMPTY_INTERNALDATA["same_class_as_time_steps"]
    )
    out["h638_contours_good"] = tuple(SPROUT_EMPTY_INTERNALDATA["h638_contours_good"])
    out["named_cad_finish_xhr_sequence"] = tuple(CAD_FINISH_NAMED_XHR_SEQUENCE)
    return out
