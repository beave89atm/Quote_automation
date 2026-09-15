"""Live page ``POST /Quote/AddItem_DXFFiles`` FileList shape.

Kyle green Finish after Part Mode posts the EDIT ``#gridDXFParts``
row as FileList. Persist **key names** and which fields were nonempty.
Never contour JSON, InternalData / ImageString values, or invented
geometry.

Live **28768-1** / **28708035** @ ``f656655`` posted FileList n=1
(PartMode Cad, ProductSubType bar_flat, InternalData empty) then
GET 0 Cad. Shape only — do not reuse those values on a new quote.
"""

from __future__ import annotations

from typing import Any

# Keys + nonempty/empty names from live-additem-dxf-filelist-28768-1.json.
# No payload values. bar_flat on Cad PartMode is the miss to refuse/clear.
LIVE_ADDITEM_DXF_FILELIST_POST: dict[str, Any] = {
    "source": "live-additem-dxf-filelist-28768-1.json",
    "quote_number": "28768-1",
    "quote_id_prefix": "28708035",
    "keys": [
        "CadType",
        "Category",
        "Depth",
        "ErrorStatus",
        "FileType",
        "HadOpenContours",
        "ImageString",
        "InternalData",
        "InternalHTML",
        "IsLinear",
        "IsPlate",
        "ItemType",
        "Length",
        "Machine",
        "Material",
        "Name",
        "OutsidePerimeter",
        "OutsidePerimeter_UseLocal",
        "PartMode",
        "PartName",
        "ProductSubType",
        "ProductType",
        "Stock_X",
        "Stock_Y",
        "Stock_Z",
        "Thickness",
        "Width",
    ],
    "nonempty_keys": [
        "CadType",
        "Category",
        "ErrorStatus",
        "FileType",
        "HadOpenContours",
        "ImageString",
        "IsLinear",
        "IsPlate",
        "ItemType",
        "Length",
        "Machine",
        "Material",
        "OutsidePerimeter_UseLocal",
        "PartMode",
        "PartName",
        "ProductSubType",
        "ProductType",
        "Stock_X",
        "Stock_Y",
        "Stock_Z",
        "Thickness",
        "Width",
    ],
    "empty_keys": [
        "InternalData",
        "InternalHTML",
        "Name",
    ],
    "wrong_productsubtype": "bar_flat",
    "internaldata_empty": True,
    "outsideperimeter_zero": True,
    "get_cad": 0,
}
