"""Spent 29341-1 — ProductID+InternalData+hole, list0_pack still empty.

Leftover c23fba3d-ef02-412b-b06e-f91ffa9076a6 Time Waco on PR 18
2026-09-07. Leave it. Do not PATCH. Do not remint.

What worked: org Time Waco; Image Files upload; catalog bind
GET/POST Products Sheets Read_Data_Plate Total=1341 → PL1/4-A572
id 9528f0c2-b0d0-443d-b263-bec2b9b9aea8 (not PlateConfig Total=3);
AddNewPDFFeature + InternalData n=1; Weight stamped.

STILL FAIL after OnAddPDFClick / GET: BadgeString '' (need PR),
OCL [] (need Laser, Drafting, Laser-Setup, Sheet Loading, Deburr),
UnitCost 3.0 == UnitWeightCost 3.0.

QuoteOrderEdit /bundles/QuoteOrderEdit capture (not a gold GET):
GetPDFData() copies dataItem.ProductID onto FileList — same as the
bag field. HasSelectedProductID is 0 hits. ProductName is not a
GetPDFData key. Machine is copied as-is (leftovers already posted
Laser - Bay1). OnAddPDFClick success is AddRow of n.List.

Named miss after ProductID+InternalData: InternalData n=1 is not
gold 14501-1 NumberOfContours/Pierces 1/1. AddNewPDFFeature writes
JSON.stringify(PDFGetData()) immediately; PDFGetData Dim1 is
[data-edit='dim1'] (QuoteOrderEdit has 0 'Diameter' strings).
GetPDFData omits NumberOfContours/Pierces. Gold GET OutsidePerimeter
0 is not the miss. Pack is List[0] BadgeString PR + laser OCL.
Fail-close if list0_pack BadgeString empty after ProductID+hole.
"""

from __future__ import annotations

from typing import Any

from secturafab.website import (
    GOLD_LASER_CALCULATOR_NAMES,
    PDFGETDATA_FEATURE_KEYS,
    QUOTE_ORDER_EDIT_GETPDFDATA,
    QUOTE_ORDER_EDIT_PDF_FINISH_HYPOTHESES,
)

SPENT_QUOTE_ID = "c23fba3d-ef02-412b-b06e-f91ffa9076a6"
SPENT_QUOTE_NUMBER = "29341-1"
ORG = "Time Waco"
SKU = "PL1/4-A572"
# Observed catalog bind — do not invent. Leave leftover; do not PATCH.
FILELIST_PRODUCT_ID = "9528f0c2-b0d0-443d-b263-bec2b9b9aea8"
UNIT_COST = 3.0
UNIT_WEIGHT_COST = 3.0

FILELIST_BAG: dict[str, Any] = {
    "Machine": "Laser - Bay1",
    "ProductID": FILELIST_PRODUCT_ID,
    "Qty": 1,
    "Weight_UseLocal": True,
    "Material": "A572",
    "Thickness": "0.25",
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
}

GOLD_FINISH_SUCCESS_LIST0: dict[str, Any] = {
    "BadgeString": "PR",
    "OperationCostList": list(GOLD_LASER_CALCULATOR_NAMES),
    "UnitCost": 36.22,
    "UnitWeightCost": 14.65,
    "DataPartPDF.NumberOfContours": 1,
    "DataPartPDF.NumberOfPierces": 1,
}


def leftover_productid_hole_empty_badge_dump() -> dict[str, Any]:
    """Leftover: ProductID+InternalData+hole; list0_pack BadgeString empty."""
    return {
        "quote_id": SPENT_QUOTE_ID,
        "quote_number": SPENT_QUOTE_NUMBER,
        "readonly": True,
        "finish_posted": True,
        "invent_internaldata": False,
        "cookie_addfeature": False,
        "invent_contours_on_filelist": False,
        "filelist_bag": dict(FILELIST_BAG),
        "list0_pack": dict(LIST0_PACK),
        "GetPDFData": dict(QUOTE_ORDER_EDIT_GETPDFDATA),
        "PDFGetData": {
            "is_xhr": False,
            "keys": list(PDFGETDATA_FEATURE_KEYS),
            "dim1": "[data-edit='dim1']",
            "writes": "InternalData",
            "empty_dim1_not_gold": True,
        },
        "AddNewPDFFeature": {
            "call": 'AddNewPDFFeature("Hole", "cad")',
            "xhr": "GET /Quote/PDFInternal",
            "then": "PDFGetData",
            "writes": "InternalData",
            "dim1_before_pdfgetdata": True,
            "invent_internaldata": False,
        },
        "OnAddPDFClick": {
            "FileList": "GetPDFData()",
            "success": "DisplaySummaryData + AddRow(n.List)",
            "list_pack_keys": ("BadgeString", "OperationCostList", "UnitCost"),
        },
        "gold_finish_success_list0": dict(GOLD_FINISH_SUCCESS_LIST0),
        "hypotheses": dict(QUOTE_ORDER_EDIT_PDF_FINISH_HYPOTHESES),
        "live_29341_1": {
            "files_kendo": True,
            "filelist_from_kendo": True,
            "productid": FILELIST_PRODUCT_ID,
            "sku": SKU,
            "plate_catalog": "v1/product/plate",
            "plate_catalog_total": 1341,
            "hole": True,
            "pdfinternal": True,
            "internaldata_n": 1,
            "internaldata_n1_is_gold_contours": False,
            "badge_string": "",
            "ocl_n": 0,
            "unit_cost": UNIT_COST,
            "unit_weight_cost": UNIT_WEIGHT_COST,
            "outside_perimeter_n": 0,
            "gold_get_outside_perimeter_0_not_miss": True,
            "list0_pack_is_gold": False,
            "pack_is_productid": False,
            "invented_guid": False,
            "onaddpdfclick": True,
        },
    }


def leftover_productid_hole_empty_badge_result() -> dict[str, Any]:
    """OnAddPDFClick List[0] after ProductID+hole — BadgeString empty."""
    return {
        "response_list_n": 1,
        "response_tag": "",
        "response_badge_string": "",
        "response_production_ready": False,
        "response_ocl_n": 0,
        "response_ocl_names": [],
        "response_unit_cost": UNIT_COST,
        "response_unit_weight_cost": UNIT_WEIGHT_COST,
        "filelist_from_kendo": True,
        "via": "page_fn",
        "finish_fn": "OnAddPDFClick",
        "filelist_bag": dict(FILELIST_BAG),
    }
