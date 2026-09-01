"""Named persist: gold Cad pack is contours/pierces 1/1 + list0_pack.

Gold look remains 1001898-1 a7dc46bf first Cad (14501-1). Do not GET
that quote from this agent. Do not PATCH. Do not remint.

Leftover Cad misses (33204-1, 1007092-1, 1002323-1, …) already had
L×W / Weight / Machine / FileList-from-kendo and still landed
DataPartPDF NumberOfContours/Pierces 0/0, InternalData '',
BadgeString empty, OperationCostList [], UnitCost==UnitWeightCost.

That 0/0 is the miss. Gold 14501-1 is 1/1 plus BadgeString PR,
laser CalculatorNames (Laser, Drafting, Deburr, Laser-Setup,
Sheet Loading) in Primary Costs, and UnitCost > UnitWeightCost.
Tag is empty on gold — not a fail. Pack is on AddItem_PDFFiles
List[0], not a later Operation→Profile graft.

Missing pre-Finish page step: when the drawing has holes, page
AddNewPDFFeature("Hole","cad") must wait for GET /Quote/PDFInternal
(not a 400ms race), then page PDFGetData() onto InternalData.
That is what creates NumberOfContours/Pierces. GetPDFData omits
those keys (same as CuttingLength) — do not invent them on FileList.
Do not cookie-POST /Quote/AddFeature. Do not invent InternalData JSON.
"""

from __future__ import annotations

from typing import Any

from secturafab.website import GOLD_LASER_CALCULATOR_NAMES

GOLD_QUOTE_ID = "a7dc46bf-836a-4250-b038-9331cc0595a7"
GOLD_QUOTE_NUMBER = "1001898-1"
GOLD_PART_NO = "14501-1"
GOLD_NOUN = "Ø21.875"

GOLD_LIST0_PACK: dict[str, Any] = {
    "list_n": 1,
    "tag": "",
    "badge_string": "PR",
    "production_ready": False,
    "ocl_n": 5,
    "ocl_names": list(GOLD_LASER_CALCULATOR_NAMES),
    "unit_cost": 36.22,
    "unit_weight_cost": 14.65,
    "number_of_contours": 1,
    "number_of_pierces": 1,
}

LEFTOVER_MISS: dict[str, Any] = {
    "had": ("Length", "Width", "Weight", "Machine", "OutsidePerimeter"),
    "internaldata": "",
    "badge_string": "",
    "ocl_n": 0,
    "unit_cost_equals_unit_weight_cost": True,
    "number_of_contours": 0,
    "number_of_pierces": 0,
    "pdfinternal_xhr": False,
    "race_400ms": True,
    "invent_contours_on_filelist": False,
}

GOLD_CAD_PACK_BIND: dict[str, Any] = {
    "quote_id": GOLD_QUOTE_ID,
    "quote_number": GOLD_QUOTE_NUMBER,
    "part_no": GOLD_PART_NO,
    "readonly": True,
    "finish_posted": True,
    "invent_internaldata": False,
    "cookie_addfeature": False,
    "invent_cuttinglength": False,
    "invent_contours_on_filelist": False,
    "pack_already_on_additem_list": True,
    "list_pack_keys": ("BadgeString", "OperationCostList", "UnitCost"),
    "gold_14501_1": {
        "part_no": GOLD_PART_NO,
        "noun": GOLD_NOUN,
        "badge_string": "PR",
        "tag": "",
        "ocl_names": list(GOLD_LASER_CALCULATOR_NAMES),
        "unit_cost": GOLD_LIST0_PACK["unit_cost"],
        "unit_weight_cost": GOLD_LIST0_PACK["unit_weight_cost"],
        "number_of_contours": 1,
        "number_of_pierces": 1,
        "thickness_in": 0.1875,
        "should_be": "Cad",
    },
    "leftover_miss": dict(LEFTOVER_MISS),
    "list0_pack": dict(GOLD_LIST0_PACK),
    "AddNewPDFFeature": {
        "optional": False,
        "when": "drawing_has_holes",
        "call": 'AddNewPDFFeature("Hole", "cad")',
        "xhr": "GET /Quote/PDFInternal",
        "then": "PDFGetData",
        "writes": "InternalData",
        "creates": ("NumberOfContours", "NumberOfPierces"),
        "invent_internaldata": False,
        "cookie_addfeature": False,
        "no_arg_not_gold": True,
        "wait_for_pdfinternal": True,
        "race_400ms_not_gold": True,
    },
    "GetPDFData": {
        "is_xhr": False,
        "omits": (
            "Status",
            "CadType",
            "CuttingLength",
            "CuttingLengthDisp",
            "ProductionReady",
            "Tag",
            "NumberOfContours",
            "NumberOfPierces",
        ),
        "cuttinglengthdisp_display_only": True,
        "status_is_filter_only": True,
        "contours_not_a_bag_key": True,
    },
}


def gold_cad_pack_bind_dump() -> dict[str, Any]:
    """Signed-off gold 14501-1 pack shape vs leftover 0/0 contours miss."""
    return dict(GOLD_CAD_PACK_BIND)


def gold_list0_pack_result() -> dict[str, Any]:
    """AddItem_PDFFiles List[0] capture that is gold pack + 1/1 contours."""
    return {
        "response_list_n": GOLD_LIST0_PACK["list_n"],
        "response_tag": GOLD_LIST0_PACK["tag"],
        "response_badge_string": GOLD_LIST0_PACK["badge_string"],
        "response_production_ready": GOLD_LIST0_PACK["production_ready"],
        "response_ocl_n": GOLD_LIST0_PACK["ocl_n"],
        "response_ocl_names": list(GOLD_LIST0_PACK["ocl_names"]),
        "response_unit_cost": GOLD_LIST0_PACK["unit_cost"],
        "response_unit_weight_cost": GOLD_LIST0_PACK["unit_weight_cost"],
        "response_number_of_contours": GOLD_LIST0_PACK["number_of_contours"],
        "response_number_of_pierces": GOLD_LIST0_PACK["number_of_pierces"],
        "filelist_from_kendo": True,
        "via": "page_fn",
        "finish_fn": "OnAddPDFClick",
    }


def leftover_list0_pack_zero_contours_result() -> dict[str, Any]:
    """Leftover List[0]: L×W bag can be full; contours 0/0 + empty pack."""
    return {
        "response_list_n": 1,
        "response_tag": "",
        "response_badge_string": "",
        "response_production_ready": False,
        "response_ocl_n": 0,
        "response_ocl_names": [],
        "response_unit_cost": 5.05,
        "response_unit_weight_cost": 5.05,
        "response_number_of_contours": 0,
        "response_number_of_pierces": 0,
        "filelist_from_kendo": True,
        "via": "page_fn",
        "finish_fn": "OnAddPDFClick",
    }
