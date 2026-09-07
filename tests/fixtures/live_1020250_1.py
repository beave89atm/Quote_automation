"""Live 1020250-1 RESERVOIR TOP PLATE — Contours=0 after ProductID+hole Dim1.

2026-09-07 CT Chief of Staff Chrome CDP 9224 (amtech AI Agent).
PDF bind via DOM.getDocument + setFileInputFiles. ProductID PASS:
PL7 Ga-A572 = 135352d6-dc2d-4b82-b516-80d617b90d82 from GET
v1/product/plate Total=1341 (not PlateConfig Total=3). Hole Dim1
5.375 via AddNewPDFFeature + [data-edit='dim1']; InternalData
present. OP 69.5 / Weight 17.98. OnAddPDFClick HTTP 200 → ItemList=1.

STILL FAIL Cad DoD: BadgeString '', OCL [], UnitCost==UnitWeightCost
7.37, DataPartPDF NumberOfContours=0, NumberOfPierces null.

QuoteOrderEdit /bundles/QuoteOrderEdit (353603 bytes):
GetPDFData omits NumberOfContours/Pierces (0 hits in the bundle).
UpdatePerimeterWeight POSTs Internal: PDFGetData() and reads
#length/#width/#MaterialEdit/#LoadThickness — not kendo cells.
onInternalDataChange writes InternalData then
UpdatePerimeterWeight(true, false) with that Internal array.
That is the geometry XHR before OnAddPDFClick. Nest /
Renest_BestSheet is later. Do not invent Contours FileList keys.
Do not Operation→Profile graft.

Named miss: last GetPerimeterAndWeight Internal Dim1 empty / form
L×W not synced, so server Contours stay 0. Leave gold a7dc46bf /
8bcc226b / 21678-1. No mint. No PATCH of this proof quote.
"""

from __future__ import annotations

from typing import Any

from secturafab.website import (
    QUOTE_ORDER_EDIT_UPW_INTERNAL,
    QUOTE_ORDER_EDIT_PDF_FINISH_HYPOTHESES,
)

SPENT_QUOTE_NUMBER = "1020250-1"
HEADER_TITLE = "RESERVOIR TOP PLATE"
SKU = "PL7 Ga-A572"
FILELIST_PRODUCT_ID = "135352d6-dc2d-4b82-b516-80d617b90d82"
HOLE_DIM1 = 5.375
OUTSIDE_PERIMETER = 69.5
WEIGHT = 17.98
UNIT_COST = 7.37
UNIT_WEIGHT_COST = 7.37

FILELIST_BAG: dict[str, Any] = {
    "Machine": "Laser - Bay1",
    "ProductID": FILELIST_PRODUCT_ID,
    "Qty": 1,
    "Weight": WEIGHT,
    "Weight_UseLocal": True,
    "OutsidePerimeter": OUTSIDE_PERIMETER,
    "OutsidePerimeter_UseLocal": True,
    "Material": "A572",
    "Thickness": "0.1793",
}

LIST0_PACK: dict[str, Any] = {
    "list_n": 1,
    "tag": "",
    "badge_string": "",
    "production_ready": False,
    "ocl_n": 0,
    "ocl_names": [],
    "unit_cost": UNIT_COST,
    "unit_weight_cost": UNIT_WEIGHT_COST,
    "number_of_contours": 0,
    "number_of_pierces": None,
}


def leftover_contours_zero_after_productid_hole_dump() -> dict[str, Any]:
    """ProductID+Dim1+InternalData+OP; list0_pack Contours=0 / BadgeString empty."""
    return {
        "quote_number": SPENT_QUOTE_NUMBER,
        "readonly": True,
        "finish_posted": True,
        "invent_internaldata": False,
        "invent_contours_on_filelist": False,
        "cookie_addfeature": False,
        "operation_profile_graft": False,
        "nest_best_sheet": False,
        "filelist_bag": dict(FILELIST_BAG),
        "list0_pack": dict(LIST0_PACK),
        "GetPDFData": {
            "omits": ("NumberOfContours", "NumberOfPierces", "CuttingLength"),
            "contours_not_a_bag_key": True,
        },
        "UpdatePerimeterWeight": dict(QUOTE_ORDER_EDIT_UPW_INTERNAL),
        "hypotheses": {
            "1_productid_getpdfdata_vs_bag": "falsified_getpdfdata_copies_productid",
            "2_hasselectedproductid_productname": "falsified_not_getpdfdata_fields",
            "3_contours_pierces_after_hole": (
                QUOTE_ORDER_EDIT_PDF_FINISH_HYPOTHESES["3_contours_pierces_after_hole"]
            ),
            "4_machine_laser_vs_bay1": "falsified_leftover_already_laser_bay1",
            "5_finish_success_list": "badge_ocl_unitcost_and_datapdf_contours",
            "6_upw_internal_dim1_form_lw": (
                QUOTE_ORDER_EDIT_UPW_INTERNAL["named_miss"]
            ),
            "7_nest_best_sheet": "falsified_nest_is_later",
        },
        "live_1020250_1": {
            "files_kendo": True,
            "filelist_from_kendo": True,
            "productid": FILELIST_PRODUCT_ID,
            "sku": SKU,
            "plate_catalog": "v1/product/plate",
            "plate_catalog_total": 1341,
            "hole": True,
            "hole_dim1": HOLE_DIM1,
            "pdfinternal": True,
            "internaldata_n": 1,
            "outside_perimeter": OUTSIDE_PERIMETER,
            "weight": WEIGHT,
            "badge_string": "",
            "ocl_n": 0,
            "unit_cost": UNIT_COST,
            "unit_weight_cost": UNIT_WEIGHT_COST,
            "number_of_contours": 0,
            "number_of_pierces": None,
            "onaddpdfclick": True,
            "itemlist_n": 1,
            "list0_pack_is_gold": False,
            "invented_contours": False,
            "nest_best_sheet": False,
        },
    }


def leftover_contours_zero_after_productid_hole_result() -> dict[str, Any]:
    """OnAddPDFClick List[0] after ProductID+hole Dim1 — Contours=0."""
    return {
        "response_list_n": 1,
        "response_tag": "",
        "response_badge_string": "",
        "response_production_ready": False,
        "response_ocl_n": 0,
        "response_ocl_names": [],
        "response_unit_cost": UNIT_COST,
        "response_unit_weight_cost": UNIT_WEIGHT_COST,
        "response_number_of_contours": 0,
        "response_number_of_pierces": 0,
        "filelist_from_kendo": True,
        "via": "page_fn",
        "finish_fn": "OnAddPDFClick",
        "filelist_bag": dict(FILELIST_BAG),
    }
