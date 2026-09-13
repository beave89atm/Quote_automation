"""Spent Cad-for-plate leftovers — automation Cad classify ≠ Contours fill.

Live verify after Cad-for-plate (tip ce2514f). invented=false.
Do not remint / PATCH. Do not invent Contours / InternalData.

    5e7bfc0b / H638-CADPLATE / ZZ-DEL-H638-CADPLATE
      App SetPartMode 0 + ProductType 100: Cad:1 classify OK,
      InternalData empty → Finish refuse
    e2683a3f / Q10334 / ZZ-DEL-Q10334
      Chrome UI kendo row.set Cad/100 + 0.1875 in + Laser-Bay1:
      Contours still empty

Q10333 / b5f56ac3 / H.6.38 Safe Cave is NOT this class. It is a
Contours PASS protect (Cad / Contours=1 / 8 bends + Profile /
Laser Bay1 / UC 176.96) after a human Component→Cad dropdown +
thickness + Finish. See ``live_q10333_h638``. Never remint /
PATCH / ZZ-DEL.

Human dropdown Contours fill is NOT reproduced by kendo row.set /
SetPartMode / UpdateData*. unlocks_automation_contours_fill=false.
"""

from __future__ import annotations

from typing import Any

LEFTOVER_CAD_FOR_PLATE: tuple[dict[str, Any], ...] = (
    {
        "quote_id": "5e7bfc0b-ecf9-46cf-8851-d61062141ce7",
        "quote_id_prefix": "5e7bfc0b",
        "quote_number": "H638-CADPLATE",
        "part_number": "H638-CADPLATE",
        "zz_del_number": "ZZ-DEL-H638-CADPLATE",
        "via": "app_setpartmode_0_producttype_100",
        "classify_cad": True,
        "cad_badge": 1,
        "internaldata_empty": True,
        "contours_empty": True,
        "finish_clicked": False,
        "finish_posted": False,
        "finish_refused": True,
        "invent": False,
        "unlocks_automation_contours_fill": False,
        "unlocks_contours_fill": False,
        "fail_close": True,
        "readonly": True,
        "zz_del": True,
    },
    {
        "quote_id": "e2683a3f-daf5-49ff-83c1-79aed35207a1",
        "quote_id_prefix": "e2683a3f",
        "quote_number": "Q10334",
        "part_number": "H638-CADPLATE",
        "zz_del_number": "ZZ-DEL-Q10334",
        "via": "chrome_kendo_set_cad_100_thickness_in_laser_bay1",
        "product_type": 100,
        "thickness_inches": "0.1875",
        "machine": "Laser-Bay1",
        "classify_cad": True,
        "internaldata_empty": True,
        "contours_empty": True,
        "finish_clicked": False,
        "finish_posted": False,
        "invent": False,
        "unlocks_automation_contours_fill": False,
        "unlocks_contours_fill": False,
        "fail_close": True,
        "readonly": True,
        "zz_del": True,
    },
)


def leftover_cad_for_plate_dumps() -> list[dict[str, Any]]:
    """Read-only Cad-for-plate leftovers. Does not unlock Contours fill."""
    return [dict(row) for row in LEFTOVER_CAD_FOR_PLATE]
