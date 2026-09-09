"""Live page ``POST /Quote/AddItem_DXFFiles`` FileList shape.

Kyle green Finish after Part Mode posts the EDIT ``#gridDXFParts``
row as FileList. Persist **key names** and which fields were nonempty
from a live page hit. Never contour JSON, InternalData values, or
invented CadType/Stock.

Live **10289-4** / **1004f017** @ ``2320c6d`` skipped page Finish
(``filelist_cad_payload_empty``) so it did not post a FileList body.
``None`` until ops captures a real page OnAddDXFClick POST.
"""

from __future__ import annotations

from typing import Any

# First live page OnAddDXFClick FileList row: keys + nonempty_keys +
# empty_keys only. Leftover reconstructed 200 / GET 0 is not this.
LIVE_ADDITEM_DXF_FILELIST_POST: dict[str, Any] | None = None
