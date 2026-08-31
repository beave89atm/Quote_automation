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
    }
