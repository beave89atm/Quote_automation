"""Mocked Sectura page responses for a PDF-only gold line.

These are not live quotes. Image Files returns the PR-only Cad badge and
the laser Primary Costs pack. Long returns Saw + Saw-Setup and a filled
UnitCost. UnitWeightCost is material weight only.
"""

from __future__ import annotations

from typing import Any

from secturafab.website import GOLD_LASER_CALCULATOR_NAMES, GOLD_SAW_CALCULATOR_NAMES

# Drawing text. Thickness, flats, and cut length are the only values the
# push is allowed to use.
PLATE_DRAWING = "\n".join(
    [
        "TITLE",
        "LIFT LOG GUSSET",
        "MATERIAL",
        "5/8",
        "A572",
        "PLATE SIZE 2.88 X 2.5",
    ]
)
PLATE_THICKNESS_IN = 0.625
PLATE_FLATS = (2.88, 2.5)

TUBE_DRAWING = "\n".join(
    [
        "TITLE",
        "PEDESTAL TUBE",
        "2 X 2 X 0.250 TUBE",
        "48 LG.",
    ]
)
TUBE_CUT_LENGTH_IN = 48.0
TUBE_SKU = "RT2X2X0.250"
TUBE_PRODUCT_ID = "11111111-1111-4111-8111-111111111111"

PLATE_MISSING_FLATS = "\n".join(
    [
        "TITLE",
        "LIFT LOG GUSSET",
        "MATERIAL",
        "5/8",
        "A36",
    ]
)


def plate_upload_bound() -> dict[str, Any]:
    """In-page #files kendo filled #gridPDF. Not cookie HTTP."""
    return {
        "upload_via": "page_add_files",
        "bound": True,
        "files_kendo": True,
        "grid_pdf_row_count": 1,
        "status_gt0_n": 1,
        "productid_n": 0,
    }


def plate_perimeter_stamp() -> dict[str, Any]:
    """L×W typed, perimeter and weight landed. No hole, so no PDFInternal."""
    return {
        "getperimeter_xhr": True,
        "perimeter_via": "UpdatePerimeterWeight",
        "form_lw_synced": True,
        "outside_perimeter_n": 1,
        "weight_n": 1,
        "getpdfdata_n": 1,
        "getpdfdata_productid_n": 1,
        "getpdfdata_outside_perimeter_n": 1,
        "productid_n": 0,
    }


def plate_gold_finish_response() -> dict[str, Any]:
    """OnAddPDFClick List[0]: PR badge, laser pack, UnitCost above weight cost."""
    return {
        "via": "page_fn",
        "finish_fn": "OnAddPDFClick",
        "filelist_from_kendo": True,
        "status": 200,
        "ok": True,
        "finish_filelist_n": 1,
        "grid_pdf_row_count": 1,
        "response_list_n": 1,
        "response_tag": "",
        "response_badge_string": "PR",
        "response_production_ready": False,
        "response_ocl_n": len(GOLD_LASER_CALCULATOR_NAMES),
        "response_ocl_names": list(GOLD_LASER_CALCULATOR_NAMES),
        "response_unit_cost": 12.5,
        "response_unit_weight_cost": 1.25,
    }


def plate_gold_line(description: str) -> dict[str, Any]:
    """Saved Cad line after Image Files. Badge is PR only."""
    return {
        "ID": "cad-1",
        "Description": description,
        "ProductType": 100,
        "Category": "Cad",
        "BadgeString": "PR",
        "UnitCost": 12.5,
        "UnitWeightCost": 1.25,
        "MaterialCost": 1.1,
        "Material": "A572 Grade 50",
        "Thickness": PLATE_THICKNESS_IN,
        "Machine": "Laser",
        "Width": PLATE_FLATS[0],
        "Length": PLATE_FLATS[1],
        "OperationCostList": [
            {
                "OperationName": "Profile",
                "CalculatorName": name,
                "UnitTime": 0.03,
            }
            for name in GOLD_LASER_CALCULATOR_NAMES
        ],
    }


def tube_catalog_product() -> dict[str, Any]:
    return {
        "ID": TUBE_PRODUCT_ID,
        "ProductName": TUBE_SKU,
        "SKU": TUBE_SKU,
        "MaterialGrade": "A36",
        "ProductDescription": "Mechanical Tube",
        "Dim1": 2.0,
        "Dim2": 2.0,
        "Dim3": 0.25,
        "Active": True,
    }


def tube_gold_finish_response() -> dict[str, Any]:
    """OnAddLinearClick List[0]: Saw + Saw-Setup and a filled UnitCost."""
    return {
        "response_list_n": 1,
        "response_tag": "",
        "response_badge_string": "",
        "response_production_ready": False,
        "response_ocl_n": 2,
        "response_ocl_names": list(GOLD_SAW_CALCULATOR_NAMES),
        "response_unit_cost": 7.63,
        "response_unit_weight_cost": 0.55,
        "response_product_id": TUBE_PRODUCT_ID,
        "response_sku": TUBE_SKU,
        "long_from_page": True,
        "long_clicked": True,
        "opened_via": "AddNewItemHTML('bar') / #but_bar",
        "via": "page_fn",
        "finish_fn": "OnAddLinearClick",
        "ok": True,
        "status": 200,
    }


def tube_gold_line(description: str) -> dict[str, Any]:
    """Saved Linear line. Saw packs are Primary Costs, not a Saw badge."""
    return {
        "ID": "lin-1",
        "Description": description,
        "ProductType": 30,
        "Category": "Linear",
        "IsLinear": True,
        "Machine": "Saw",
        "Length": TUBE_CUT_LENGTH_IN,
        "UnitCost": 7.63,
        "UnitWeightCost": 0.55,
        "MaterialCost": 0.55,
        "SKU": TUBE_SKU,
        "ProductID": TUBE_PRODUCT_ID,
        "BadgeString": "",
        "OperationCostList": [
            {"CalculatorName": "Saw", "OperationName": "Cut", "UnitCost": 4.0},
            {"CalculatorName": "Saw-Setup", "OperationName": "Cut", "UnitCost": 3.63},
        ],
    }
