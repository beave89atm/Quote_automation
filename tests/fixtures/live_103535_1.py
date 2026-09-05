"""Spent 103535-1 GATE WELDMENT — cookie HTTP upload left #gridPDF empty.

Minted bd5c2e3e-948d-463d-8844-4366910bb5ec (Q10095) on PR 18 2cbf1b0.
5 plate PDFs via cookie HTTP UploadItem_PDFFiles; 4 L×W stamps; OnAddPDFClick
skipped empty_dataSource; GET 0 Cad. Leave the shell. Do not PATCH. Do not remint.
"""

from __future__ import annotations

from typing import Any

SPENT_QUOTE_ID = "bd5c2e3e-948d-463d-8844-4366910bb5ec"
SPENT_QUOTE_NUMBER = "103535-1"
SPENT_Q_NUMBER = "Q10095"
HEADER_TITLE = "GATE WELDMENT"

COOKIE_HTTP_PLATE_STEMS = ("102196", "30345", "103545", "103544", "103546")
STAMP_N = 4
MISSING_FLATS_STEM = "103544"

# Leftover Image Files dialog on bd5c2e3e (read-only; dialog closed; no Finish).
# Capture named /workspace/live-103535-1-gridpdf-bind.json — not on this VM.
LEFTOVER_GRIDPDF_BIND = {
    "quote_id": SPENT_QUOTE_ID,
    "quote_number": SPENT_QUOTE_NUMBER,
    "readonly": True,
    "dialog_closed": True,
    "finish_posted": False,
    "getitem_addview": {
        "ItemType": "pdf",
        "gridPDF": {"Data": [], "Total": 0},
        "kendoUpload": "#files",
    },
    "kendoUpload": {
        "selector": "#files",
        "success": "onSuccess_PDFUpload",
        "complete": "onComplete_PDFUpload",
        "upload": "onUpload_PDFUpload",
        "dropZone": ".dropZoneElement",
        "async": {
            "saveUrl": "/Attachment/UploadItem_PDFFiles",
            "autoUpload": True,
            "batch": True,
        },
    },
    "onUpload_PDFUpload": {
        "data": {
            "Location": "$('#InventoryLocation').val()",
            "quoteId": "$('#ID').val()",
        },
    },
    "onSuccess_PDFUpload": {
        "only_fill": True,
        "adds": "#gridPDF.dataSource.add from n.response.List",
        "copies": (
            "Status",
            "FileID",
            "FileName",
            "Machine",
            "Material",
            "Thickness",
            "InternalData",
        ),
    },
    "gridPDF_transport": {"read": {"url": ""}},
    "GetPDFData": {
        "is_xhr": False,
        "walks": "#gridPDF tbody dataItem",
        "keeps": "Status>0",
    },
    "OnAddPDFClick": {
        "body": ("ID", "ItemID", "FileList"),
        "FileList": "GetPDFData()",
        "path": "controllerName+/AddItem_PDFFiles",
    },
    "live_103535_1": {
        "cookie_http_uploads": 5,
        "stamp_n": STAMP_N,
        "datasource_n": 0,
        "getpdfdata_n": 0,
        "finish_why": "empty_dataSource",
    },
}


def live_103535_1_cookie_http_empty_grid() -> dict[str, Any]:
    """Notes + GET shape after cookie HTTP upload / empty #gridPDF."""
    return {
        "ID": SPENT_QUOTE_ID,
        "QuoteNumber": SPENT_QUOTE_NUMBER,
        "Description": HEADER_TITLE,
        "ItemCount": 1,
        "ItemList": [
            {
                "ID": "asm-1",
                "Description": f"{SPENT_QUOTE_NUMBER} - {HEADER_TITLE}",
                "ProductType": 300,
                "IsAssembly": True,
                "Quantity": 1,
                "UnitCost": 0,
                "OperationCostList": [],
            }
        ],
        "cookie_http_uploads": 5,
        "stamp_n": STAMP_N,
        "finish_why": "empty_dataSource",
        "filelist_from_kendo": False,
        "cad_n": 0,
        "datasource_n": 0,
        "getpdfdata_n": 0,
    }


def leftover_gridpdf_bind_dump() -> dict[str, Any]:
    """Leftover Image Files dialog: #files kendoUpload is the only #gridPDF fill."""
    return dict(LEFTOVER_GRIDPDF_BIND)
