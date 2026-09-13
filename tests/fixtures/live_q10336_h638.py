"""Q10336 / f73dd116 — Cad+Laser Finish leftover (finished Contours match Q10333).

Live continuous mouse Cad→Finish on Safe Cave H.6.38 (same STEP family
as Q10333). Sequence (named XHRs only; capture JSON was not on box):
  1. CadImport/UploadItem_DXFFiles
  2. CadImport/Data
  3. /part/create
  4. POST /Part/UpdateItemType (real mouse Cad)
  5. /part/PartImage
  6. /Quote/GetBorderSize Thickness_Units=inch
  7. POST /Quote/AddItem_DXFFiles (Finish)
  8. quote/ItemEdit

Live GET after Finish is semantically identical to Q10333 / Q10339:
  NumberOfContours=1 (v1 ItemList) — Contours PASS signal
  CadImport OpenContourCount=0 (expected; same on human PASS Q10333)
  bends=8 / OCL Profile×5 + Bend×2
  InternalData absent post-Finish
  Cad ProductType 100 / Laser Bay1 / UC 64.25

Soft-pass Contours=0 / OpenContourCount / bends=1 labels were stage
notes, not a finished-field gap. Do not gate Contours≥1 unlock on
OCC≥1 (false-fails H.6.38 including Q10333). invent=false.
Forever-protect; never remint / PATCH / ZZ-DEL. Does not unlock invent
Contours fill.

Q10335 / bcff1a24 stays the empty-Contours / lost-CAD-row forbid.
Unused Time STEPs that explode empty InternalData stay a separate
fail-close. Mid-wizard XHR probe still useful to see NumberOfContours
flip 0→1.
"""

from __future__ import annotations

from typing import Any

from secturafab.cadimport_js import (
    GET_BORDER_SIZE_PATH,
    UPDATE_ITEM_TYPE_CAD,
    UPDATE_ITEM_TYPE_PATH,
)

Q10336_CAD_FINISH: dict[str, Any] = {
    "quote_id": "f73dd116-f33e-485f-947c-f5662633d23a",
    "quote_id_prefix": "f73dd116",
    "quote_number": "Q10336",
    "part_number": "H.6.38",
    "customer": "Safe Cave",
    "source": "Onshape STEP",
    "same_step_family_as": "Q10333",
    "via": "mouse_updateitemtype_cad_then_finish",
    "xhr_sequence": (
        "/CadImport/UploadItem_DXFFiles",
        "/CadImport/Data",
        "/part/create",
        UPDATE_ITEM_TYPE_PATH,
        "/part/PartImage",
        GET_BORDER_SIZE_PATH,
        "/Quote/AddItem_DXFFiles",
        "/quote/ItemEdit",
    ),
    "update_item_type_path": UPDATE_ITEM_TYPE_PATH,
    "update_item_type_itemtype": UPDATE_ITEM_TYPE_CAD,
    "update_item_type_before_additem_dxf": True,
    "get_border_size_path": GET_BORDER_SIZE_PATH,
    "get_border_size_thickness_units": "inch",
    "finish_path": "/Quote/AddItem_DXFFiles",
    "pass": True,
    "contours_pass": True,
    "cad_laser_finish_soft_pass": True,
    "soft_pass_labels_were_stage_notes": True,
    "finished_semantics_match_q10333": True,
    "product_type": "Cad",
    "product_type_enum": 100,
    "open_contour_count": 0,
    "number_of_contours": 1,
    "contours_ge_1": True,
    "contours_pass_signal": "v1_itemlist_number_of_contours_ge_1",
    "bends": 8,
    "profile": True,
    "ocl_profile_count": 5,
    "ocl_bend_count": 2,
    "internaldata_absent_post_finish": True,
    "machine": "Laser Bay1",
    "unit_cost": 64.25,
    "laser_costs_filled": True,
    "finish_clicked": True,
    "finish_posted": True,
    "invent": False,
    "zz_del": False,
    "zz_del_number": None,
    "protect": True,
    "readonly": True,
    "do_not_remint": True,
    "do_not_patch": True,
    "cad_set_via": "mouse_updateitemtype_cad",
    "unlocks_automation_contours_fill": False,
    "update_item_type_fills_contours": False,
}


def q10336_h638_cad_finish_dump() -> dict[str, Any]:
    """Read-only Cad+Finish leftover. Never remint / PATCH / ZZ-DEL."""
    out = dict(Q10336_CAD_FINISH)
    out["xhr_sequence"] = tuple(Q10336_CAD_FINISH["xhr_sequence"])
    return out
