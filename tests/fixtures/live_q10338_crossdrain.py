"""Q10338 / 4902c597 — AIM Cross Drain Cad Image Files PASS leftover.

EOD inbox Image Files PASS (Kyle inbox Cross Drain zip). Do not remint
/ PATCH. invent=false.

Live Finish snapshot (PASS basis):
  Q10338 / 4902c597-2ad6-4ebf-b577-dd6cf20a7d87 / CROSSDRAIN-12X7X60
  AIM Cross Drain / Time Waco / 14ga 316 SS PL14 Ga-SS316
  69.875×25.875 / Laser Bay1 / Contours=1 / Finish UC 100.45
  + PR laser pack / bends_count=8 from shop PDF
  UpdateItemType Cad 200

Post-pass bend-API dabble may show live UC 3.25. That is not the PASS
basis and is not a repair target — forever-protect the Finish snapshot
UC 100.45. Do not try to restore UnitCost via PATCH.
"""

from __future__ import annotations

from typing import Any

Q10338_IMAGE_FILES_PASS: dict[str, Any] = {
    "quote_id": "4902c597-2ad6-4ebf-b577-dd6cf20a7d87",
    "quote_id_prefix": "4902c597",
    "quote_number": "Q10338",
    "part_number": "CROSSDRAIN-12X7X60",
    "customer": "AIM Cross Drain",
    "org": "Time Waco",
    "source": "Kyle inbox Cross Drain zip",
    "path": "image_files",
    "pass": True,
    "image_files_pass": True,
    "contours_pass": True,
    "product_type": "Cad",
    "product_type_enum": 100,
    "update_item_type_status": 200,
    "update_item_type_itemtype": "Cad",
    "number_of_contours": 1,
    "bends_count": 8,
    "bends_from": "shop_pdf",
    "material": "PL14 Ga-SS316",
    "thickness": "14ga",
    "grade": "316 SS",
    "size": "69.875×25.875",
    "machine": "Laser Bay1",
    "unit_cost": 100.45,
    "finish_unit_cost": 100.45,
    "live_unit_cost_after_bend_dabble": 3.25,
    "pass_basis_unit_cost": 100.45,
    "pr_laser_pack": True,
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
    "do_not_repair_via_patch": True,
}


def q10338_crossdrain_pass_dump() -> dict[str, Any]:
    """Read-only Image Files PASS leftover. Never remint / PATCH."""
    return dict(Q10338_IMAGE_FILES_PASS)
