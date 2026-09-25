"""Spent 21681-1 KNUCKLE PLATE — empty bind ProductID skip was wrong.

Minted 646a3d98-cd73-4f94-be67-6e40eeb2c309 on PR 18 b92f503.
Image Files #files bound #gridPDF n=1. bind_productid_n=0.
Product box empty. Upload row defaults: Material=316 Polished,
Thickness=0.0178, Machine="", Status=0, ProductID=null.
Drawing is 1/2 DOMEX/WELDOX — never stamped because Finish was
fail-closed on empty bind ProductID.

GetPDFData Status=0 so n=0. Finish skipped. GET 0.

Upload List ProductID is always null on Image Files PDFs. keepPid
never has anything to restore. Empty ProductID is the Image Files
default, not a skip. 33819-1 already Finished with ProductID=None
+ A572/0.625/Laser Bay 1 + Weight/Perimeter and still no pack.

DoD: bind ProductID null + 316 Polished default + Finish skipped
= wrong skip. Leave 646a3d98.
Do not PATCH. Do not remint. No graft. No Operation→Profile. No nest.
Do not invent a GUID. Drive the page Product picker.
Capture named /workspace/live-21681-1-run.json — fixture here.
"""

from __future__ import annotations

from typing import Any

SPENT_QUOTE_ID = "646a3d98-cd73-4f94-be67-6e40eeb2c309"
SPENT_QUOTE_NUMBER = "21681-1"
HEADER_TITLE = "KNUCKLE PLATE"

FILES_KENDO = True
BIND_PRODUCTID_N = 0
UPLOAD_MATERIAL = "316 Polished"
UPLOAD_THICKNESS = 0.0178
UPLOAD_MACHINE = ""
UPLOAD_STATUS = 0
DRAWING_MATERIAL = "DOMEX/WELDOX"
DRAWING_THICKNESS = 0.5


def live_21681_1_quote() -> dict[str, Any]:
    """GET 0 after empty-bind-ProductID skip (no Cad line)."""
    return {
        "ID": SPENT_QUOTE_ID,
        "QuoteNumber": SPENT_QUOTE_NUMBER,
        "Description": HEADER_TITLE,
        "OrganizationName": "Time Waco",
        "ItemCount": 0,
        "ItemList": [],
        "files_kendo": FILES_KENDO,
        "bind_productid_n": BIND_PRODUCTID_N,
        "cad_n": 0,
        "getpdfdata_n": 0,
        "finish_skipped": True,
        "skip_reason": "empty_bind_productid",
        "upload_material": UPLOAD_MATERIAL,
        "upload_thickness": UPLOAD_THICKNESS,
        "drawing_material": DRAWING_MATERIAL,
        "stamped": False,
    }


LEFTOVER_EMPTY_BIND_PRODUCTID_SKIP = {
    "quote_id": SPENT_QUOTE_ID,
    "quote_number": SPENT_QUOTE_NUMBER,
    "readonly": True,
    "finish_posted": False,
    "finish_skipped": True,
    "skip_reason": "empty_bind_productid",
    "filelist_keys_logged": False,
    "GetPDFData": {
        "is_xhr": False,
        "keeps": "Status>0",
        "status_n": 0,
        "n": 0,
        "omits": ("CuttingLength", "Status", "Tag", "ProductionReady"),
    },
    "upload_list": {
        "ProductID": None,
        "Material": UPLOAD_MATERIAL,
        "Thickness": UPLOAD_THICKNESS,
        "Machine": UPLOAD_MACHINE,
        "Status": UPLOAD_STATUS,
    },
    "drawing": {
        "material": DRAWING_MATERIAL,
        "thickness": DRAWING_THICKNESS,
        "stamped": False,
    },
    "live_21681_1": {
        "files_kendo": True,
        "grid_pdf_n": 1,
        "bind_productid_n": BIND_PRODUCTID_N,
        "product_box": "",
        "upload_material": UPLOAD_MATERIAL,
        "upload_thickness": UPLOAD_THICKNESS,
        "upload_machine": UPLOAD_MACHINE,
        "upload_status": UPLOAD_STATUS,
        "drawing_material": DRAWING_MATERIAL,
        "stamped": False,
        "getpdfdata_n": 0,
        "cad_n": 0,
    },
}


def leftover_empty_bind_productid_skip_dump() -> dict[str, Any]:
    """Leftover: bind ProductID null + 316 Polished + Finish skipped."""
    return dict(LEFTOVER_EMPTY_BIND_PRODUCTID_SKIP)
