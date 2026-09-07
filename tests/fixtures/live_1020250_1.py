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

5a231aa live 3e222215 (ZZ-DEL): getperim_internal_dim1_n=1 but
form_lw_synced=false / outside_perimeter_n=0 / Weight~0.05
(hole-only). fc94ca9 live 1ca884cc (ZZ-DEL, prior 111633b8):
form_lw_synced=true (17.375×17.375) + OP 69.5 / Weight 17.98
but OnAddPDFClick posted FileList n=0 (row0 null). Stamp
dataSource n=1 Status=1 is not GetPDFData(). 77ddb70 live
6150c5c7 (ZZ-DEL): GetPDFData/FileList n=1 + ProductID + OP
but Finish bag InternalData null — Contours stay 0. 55a0294
live bab8f668 (ZZ-DEL): InternalData Type=hole Dim1=5.375
proven, FileList n=1, but ProductType=bar / ProductSubType=
bar_flat on a Sheets & Plates ProductID. 533ef0f live
c751780e (ZZ-DEL): ProductType/SubType prt_pdf + hole Dim1
+ OP, still Contours=0 / no PR. GetPDFData copies OutsideArea
/ TrueWeight / Description; posted row dropped OutsideArea
(undefined), TrueWeight 0, Description null. OnAddPDFClick
AddRow n.List — Nest is later. Do not invent Contours keys.
Leave gold a7dc46bf / 8bcc226b / 21678-1. No mint. No PATCH.
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
            "8_form_lw_synced_false": (
                QUOTE_ORDER_EDIT_UPW_INTERNAL["form_lw_synced_false_miss"]
            ),
            "9_finish_filelist_n0": (
                QUOTE_ORDER_EDIT_UPW_INTERNAL["finish_filelist_n0_miss"]
            ),
            "10_finish_internaldata_null": (
                QUOTE_ORDER_EDIT_UPW_INTERNAL["finish_internaldata_null_miss"]
            ),
            "11_finish_producttype_bar": (
                QUOTE_ORDER_EDIT_UPW_INTERNAL["finish_producttype_bar_miss"]
            ),
            "12_finish_prt_pdf_still_contours_zero": (
                QUOTE_ORDER_EDIT_UPW_INTERNAL["finish_prt_pdf_still_contours_zero_miss"]
            ),
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


def leftover_form_lw_unsynced_after_internal_dim1_dump() -> dict[str, Any]:
    """5a231aa / 3e222215: Internal Dim1 UPW, form_lw_synced=false, OP=0."""
    return {
        "quote_id": "3e222215-0000-4000-8000-000000000001",
        "quote_number": SPENT_QUOTE_NUMBER,
        "readonly": True,
        "invent_contours_on_filelist": False,
        "operation_profile_graft": False,
        "UpdatePerimeterWeight": dict(QUOTE_ORDER_EDIT_UPW_INTERNAL),
        "live_5a231aa": {
            "quote_id_prefix": "3e222215",
            "getperim_internal_n": 1,
            "getperim_internal_dim1_n": 1,
            "form_lw_synced": False,
            "outside_perimeter_n": 0,
            "weight": 0.05,
            "hole_dim1_via": "data-edit=dim1",
            "pdfinternal_html": True,
            "badge_string": "",
            "ocl_n": 0,
            "number_of_contours": 0,
        },
    }


def leftover_form_lw_unsynced_stamp() -> dict[str, Any]:
    """Stamp result that must skip Finish (form L×W miss)."""
    return {
        "ok": True,
        "stamped": 1,
        "outside_perimeter_n": 0,
        "weight_n": 1,
        "productid_n": 1,
        "internaldata_n": 1,
        "form_lw_synced": False,
        "form_length": "",
        "form_width": "",
        "getperim_internal_n": 1,
        "getperim_internal_dim1_n": 1,
        "pdfinternal_html": True,
        "pdfinternal_xhr": True,
        "hole_dim1_via": "data-edit=dim1",
        "getperimeter_xhr": True,
    }


def leftover_finish_filelist_n0_after_form_lw_dump() -> dict[str, Any]:
    """fc94ca9 / 1ca884cc: form_lw_synced + OP>0, Finish FileList n=0."""
    return {
        "quote_id": "1ca884cc-0000-4000-8000-000000000001",
        "quote_number": SPENT_QUOTE_NUMBER,
        "readonly": True,
        "invent_contours_on_filelist": False,
        "operation_profile_graft": False,
        "UpdatePerimeterWeight": dict(QUOTE_ORDER_EDIT_UPW_INTERNAL),
        "live_1ca884cc": {
            "quote_id_prefix": "1ca884cc",
            "form_lw_synced": True,
            "form_length": 17.375,
            "form_width": 17.375,
            "outside_perimeter": OUTSIDE_PERIMETER,
            "weight": WEIGHT,
            "productid": FILELIST_PRODUCT_ID,
            "hole_dim1": HOLE_DIM1,
            "getperim_internal_dim1_n": 1,
            "pdfinternal_html": True,
            "finish_filelist_n": 0,
            "filelist_raw": "[]",
            "posted_keys": ["ID", "ItemID", "FileList_raw", "FileList"],
            "badge_string": "",
            "ocl_n": 0,
            "number_of_contours": 0,
        },
    }


def leftover_finish_filelist_n0_stamp() -> dict[str, Any]:
    """Stamp that looks good (form L×W + OP) but GetPDFData n=0."""
    return {
        "ok": True,
        "stamped": 1,
        "outside_perimeter_n": 1,
        "weight_n": 1,
        "productid_n": 1,
        "internaldata_n": 1,
        "form_lw_synced": True,
        "form_length": "17.375",
        "form_width": "17.375",
        "getperim_internal_n": 1,
        "getperim_internal_dim1_n": 1,
        "pdfinternal_html": True,
        "pdfinternal_xhr": True,
        "hole_dim1_via": "data-edit=dim1",
        "getperimeter_xhr": True,
        "getpdfdata_n": 0,
        "getpdfdata_productid_n": 0,
        "getpdfdata_internal_dim1_n": 0,
        "getpdfdata_outside_perimeter_n": 0,
    }


def leftover_finish_filelist_n0_result() -> dict[str, Any]:
    """OnAddPDFClick posted empty FileList after a good stamp."""
    return {
        "via": "skipped",
        "finish_fn": "OnAddPDFClick",
        "finish_why": "empty_getpdfdata",
        "finish_filelist_n": 0,
        "filelist_from_kendo": False,
        "filelist_raw": "[]",
        "posted_keys": ["ID", "ItemID", "FileList"],
        "getpdfdata_n": 0,
        "getpdfdata_productid_n": 0,
        "getpdfdata_internal_dim1_n": 0,
        "getpdfdata_outside_perimeter_n": 0,
        "response_list_n": 0,
        "response_badge_string": "",
        "response_ocl_n": 0,
        "response_number_of_contours": 0,
    }


def leftover_finish_internaldata_null_dump() -> dict[str, Any]:
    """77ddb70 / 6150c5c7: GetPDFData n=1 but Finish bag InternalData null."""
    bag = dict(FILELIST_BAG)
    bag["InternalData"] = None
    return {
        "quote_id": "6150c5c7-0000-4000-8000-000000000001",
        "quote_number": SPENT_QUOTE_NUMBER,
        "readonly": True,
        "invent_contours_on_filelist": False,
        "operation_profile_graft": False,
        "UpdatePerimeterWeight": dict(QUOTE_ORDER_EDIT_UPW_INTERNAL),
        "filelist_bag": bag,
        "hypotheses": {
            "6_upw_internal_dim1_form_lw": (
                QUOTE_ORDER_EDIT_UPW_INTERNAL["named_miss"]
            ),
            "7_nest_best_sheet": "falsified_nest_is_later",
            "8_form_lw_synced_false": (
                QUOTE_ORDER_EDIT_UPW_INTERNAL["form_lw_synced_false_miss"]
            ),
            "9_finish_filelist_n0": (
                QUOTE_ORDER_EDIT_UPW_INTERNAL["finish_filelist_n0_miss"]
            ),
            "10_finish_internaldata_null": (
                QUOTE_ORDER_EDIT_UPW_INTERNAL["finish_internaldata_null_miss"]
            ),
            "11_finish_producttype_bar": (
                QUOTE_ORDER_EDIT_UPW_INTERNAL["finish_producttype_bar_miss"]
            ),
            "12_finish_prt_pdf_still_contours_zero": (
                QUOTE_ORDER_EDIT_UPW_INTERNAL["finish_prt_pdf_still_contours_zero_miss"]
            ),
        },
        "live_6150c5c7": {
            "quote_id_prefix": "6150c5c7",
            "form_lw_synced": True,
            "outside_perimeter": OUTSIDE_PERIMETER,
            "weight": WEIGHT,
            "productid": FILELIST_PRODUCT_ID,
            "hole_dim1": HOLE_DIM1,
            "getpdfdata_n": 1,
            "getpdfdata_productid_n": 1,
            "getpdfdata_internal_dim1_n": 1,
            "getpdfdata_outside_perimeter_n": 1,
            "finish_filelist_n": 1,
            "filelist_internaldata": None,
            "filelist_internaldata_dim1_n": 0,
            "badge_string": "",
            "ocl_n": 0,
            "number_of_contours": 0,
        },
    }


def leftover_finish_internaldata_null_result() -> dict[str, Any]:
    """OnAddPDFClick FileList n=1 with InternalData null after stamp dim1_n=1."""
    bag = dict(FILELIST_BAG)
    bag["InternalData"] = None
    return {
        "via": "skipped",
        "finish_fn": "OnAddPDFClick",
        "finish_why": "empty_internaldata",
        "finish_filelist_n": 1,
        "filelist_from_kendo": False,
        "filelist_internaldata": None,
        "filelist_internaldata_dim1_n": 0,
        "getpdfdata_n": 1,
        "getpdfdata_productid_n": 1,
        "getpdfdata_internal_dim1_n": 1,
        "getpdfdata_outside_perimeter_n": 1,
        "filelist_bag": bag,
        "response_list_n": 0,
        "response_badge_string": "",
        "response_ocl_n": 0,
        "response_number_of_contours": 0,
    }


def leftover_finish_producttype_bar_dump() -> dict[str, Any]:
    """55a0294 / bab8f668: plate ProductID + hole InternalData, ProductType=bar."""
    bag = dict(FILELIST_BAG)
    bag["InternalData"] = (
        '[{"Type":"hole","Dim1":5.375,"Dim2":0,"Qty":1,"Qty2":0,"Note":""}]'
    )
    bag["ProductType"] = "bar"
    bag["ProductSubType"] = "bar_flat"
    bag["ItemType"] = "cad"
    return {
        "quote_id": "bab8f668-0000-4000-8000-000000000001",
        "quote_number": SPENT_QUOTE_NUMBER,
        "readonly": True,
        "invent_contours_on_filelist": False,
        "operation_profile_graft": False,
        "UpdatePerimeterWeight": dict(QUOTE_ORDER_EDIT_UPW_INTERNAL),
        "filelist_bag": bag,
        "hypotheses": {
            "6_upw_internal_dim1_form_lw": (
                QUOTE_ORDER_EDIT_UPW_INTERNAL["named_miss"]
            ),
            "7_nest_best_sheet": "falsified_nest_is_later",
            "8_form_lw_synced_false": (
                QUOTE_ORDER_EDIT_UPW_INTERNAL["form_lw_synced_false_miss"]
            ),
            "9_finish_filelist_n0": (
                QUOTE_ORDER_EDIT_UPW_INTERNAL["finish_filelist_n0_miss"]
            ),
            "10_finish_internaldata_null": (
                QUOTE_ORDER_EDIT_UPW_INTERNAL["finish_internaldata_null_miss"]
            ),
            "11_finish_producttype_bar": (
                QUOTE_ORDER_EDIT_UPW_INTERNAL["finish_producttype_bar_miss"]
            ),
            "12_finish_prt_pdf_still_contours_zero": (
                QUOTE_ORDER_EDIT_UPW_INTERNAL["finish_prt_pdf_still_contours_zero_miss"]
            ),
        },
        "live_bab8f668": {
            "quote_id_prefix": "bab8f668",
            "form_lw_synced": True,
            "outside_perimeter": OUTSIDE_PERIMETER,
            "weight": WEIGHT,
            "productid": FILELIST_PRODUCT_ID,
            "hole_dim1": HOLE_DIM1,
            "getpdfdata_n": 1,
            "getpdfdata_productid_n": 1,
            "getpdfdata_internal_dim1_n": 1,
            "getpdfdata_outside_perimeter_n": 1,
            "finish_filelist_n": 1,
            "filelist_internaldata_dim1_n": 1,
            "filelist_producttype": "bar",
            "filelist_productsubtype": "bar_flat",
            "filelist_itemtype": "cad",
            "badge_string": "",
            "ocl_n": 0,
            "number_of_contours": 0,
        },
    }


def leftover_finish_producttype_bar_result() -> dict[str, Any]:
    """OnAddPDFClick FileList n=1 with ProductType=bar after plate ProductID."""
    bag = dict(FILELIST_BAG)
    bag["InternalData"] = (
        '[{"Type":"hole","Dim1":5.375,"Dim2":0,"Qty":1,"Qty2":0,"Note":""}]'
    )
    bag["ProductType"] = "bar"
    bag["ProductSubType"] = "bar_flat"
    bag["ItemType"] = "cad"
    return {
        "via": "skipped",
        "finish_fn": "OnAddPDFClick",
        "finish_why": "bar_producttype",
        "finish_filelist_n": 1,
        "filelist_from_kendo": False,
        "filelist_internaldata": bag["InternalData"],
        "filelist_internaldata_dim1_n": 1,
        "filelist_producttype": "bar",
        "filelist_productsubtype": "bar_flat",
        "filelist_itemtype": "cad",
        "getpdfdata_n": 1,
        "getpdfdata_productid_n": 1,
        "getpdfdata_internal_dim1_n": 1,
        "getpdfdata_outside_perimeter_n": 1,
        "filelist_bag": bag,
        "response_list_n": 0,
        "response_badge_string": "",
        "response_ocl_n": 0,
        "response_number_of_contours": 0,
    }


def leftover_finish_prt_pdf_still_contours_zero_dump() -> dict[str, Any]:
    """533ef0f / c751780e: prt_pdf + hole Dim1 + OP, Contours=0 / no PR."""
    bag = dict(FILELIST_BAG)
    bag["InternalData"] = (
        '[{"Type":"hole","Dim1":5.375,"Dim2":0,"Qty":1,"Qty2":0,"Note":""}]'
    )
    bag["ProductType"] = "prt_pdf"
    bag["ProductSubType"] = "prt_pdf"
    bag["ItemType"] = "cad"
    bag["TrueWeight"] = 0
    bag["MaterialCost"] = ""
    bag["Description"] = None
    return {
        "quote_id": "c751780e-0000-4000-8000-000000000001",
        "quote_number": SPENT_QUOTE_NUMBER,
        "readonly": True,
        "invent_contours_on_filelist": False,
        "operation_profile_graft": False,
        "nest_best_sheet": False,
        "UpdatePerimeterWeight": dict(QUOTE_ORDER_EDIT_UPW_INTERNAL),
        "filelist_bag": bag,
        "hypotheses": {
            "6_upw_internal_dim1_form_lw": (
                QUOTE_ORDER_EDIT_UPW_INTERNAL["named_miss"]
            ),
            "7_nest_best_sheet": "falsified_nest_is_later",
            "8_form_lw_synced_false": (
                QUOTE_ORDER_EDIT_UPW_INTERNAL["form_lw_synced_false_miss"]
            ),
            "9_finish_filelist_n0": (
                QUOTE_ORDER_EDIT_UPW_INTERNAL["finish_filelist_n0_miss"]
            ),
            "10_finish_internaldata_null": (
                QUOTE_ORDER_EDIT_UPW_INTERNAL["finish_internaldata_null_miss"]
            ),
            "11_finish_producttype_bar": (
                QUOTE_ORDER_EDIT_UPW_INTERNAL["finish_producttype_bar_miss"]
            ),
            "12_finish_prt_pdf_still_contours_zero": (
                QUOTE_ORDER_EDIT_UPW_INTERNAL["finish_prt_pdf_still_contours_zero_miss"]
            ),
        },
        "live_c751780e": {
            "quote_id_prefix": "c751780e",
            "form_lw_synced": True,
            "outside_perimeter": OUTSIDE_PERIMETER,
            "weight": WEIGHT,
            "productid": FILELIST_PRODUCT_ID,
            "hole_dim1": HOLE_DIM1,
            "getpdfdata_n": 1,
            "getpdfdata_productid_n": 1,
            "getpdfdata_internal_dim1_n": 1,
            "getpdfdata_outside_perimeter_n": 1,
            "finish_filelist_n": 1,
            "filelist_internaldata_dim1_n": 1,
            "filelist_producttype": "prt_pdf",
            "filelist_productsubtype": "prt_pdf",
            "outsidearea": None,
            "trueweight": 0,
            "materialcost": "",
            "description": None,
            "badge_string": "",
            "ocl_n": 0,
            "number_of_contours": 0,
        },
    }


def leftover_finish_prt_pdf_still_contours_zero_result() -> dict[str, Any]:
    """OnAddPDFClick 200 after prt_pdf + hole Dim1 — Contours=0 / no PR."""
    bag = dict(FILELIST_BAG)
    bag["InternalData"] = (
        '[{"Type":"hole","Dim1":5.375,"Dim2":0,"Qty":1,"Qty2":0,"Note":""}]'
    )
    bag["ProductType"] = "prt_pdf"
    bag["ProductSubType"] = "prt_pdf"
    bag["ItemType"] = "cad"
    bag["TrueWeight"] = 0
    bag["MaterialCost"] = ""
    bag["Description"] = None
    return {
        "via": "page_fn",
        "finish_fn": "OnAddPDFClick",
        "finish_why": "ok",
        "finish_filelist_n": 1,
        "filelist_from_kendo": True,
        "filelist_internaldata": bag["InternalData"],
        "filelist_internaldata_dim1_n": 1,
        "filelist_producttype": "prt_pdf",
        "filelist_productsubtype": "prt_pdf",
        "filelist_itemtype": "cad",
        "getpdfdata_n": 1,
        "getpdfdata_productid_n": 1,
        "getpdfdata_internal_dim1_n": 1,
        "getpdfdata_outside_perimeter_n": 1,
        "filelist_bag": bag,
        "response_list_n": 1,
        "response_badge_string": "",
        "response_ocl_n": 0,
        "response_number_of_contours": 0,
    }
