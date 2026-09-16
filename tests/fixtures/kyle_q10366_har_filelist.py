"""Kyle Q10366 HAR Finish FileList shape — Cad Contours plate.

Key names / tokens only. No Contours JSON, no InternalData values,
no invented geometry. invent=false.

Q10366 / fd0b6e45 Safe Cave H.6.38 Contours PASS. Status key absent.
ImageString key absent. FileType / PartMode / SourceDataID absent.
ItemType=cad ProductType=bar productSubType=bar_flat Machine=Laser
Length/Width in meters. AddItem success = HTTP 200 AND List length ≥1
(List=[] is fail even if body has List,Result keys).
"""

from __future__ import annotations

from typing import Any

KYLE_Q10366_HAR_FINISH_FILELIST: dict[str, Any] = {
    "source": "Q10366 HAR Finish AddItem_DXFFiles FileList",
    "quote_number": "Q10366",
    "quote_id_prefix": "fd0b6e45",
    "invent_status": False,
    "send_imagestring": False,
    "item_type": "cad",
    "product_type": "bar",
    "product_subtype": "bar_flat",
    "machine": "Laser",
    "length_width_units": "meter",
    "absent_keys": (
        "Status",
        "ImageString",
        "FileType",
        "PartMode",
        "SourceDataID",
        "Width_Units",
        "drawing_thickness_in",
        "thickness_source",
        "CadType",
        "HadOpenContours",
        "IsPlate",
    ),
    "invent_contours": False,
    "additem_list_min": 1,
}
