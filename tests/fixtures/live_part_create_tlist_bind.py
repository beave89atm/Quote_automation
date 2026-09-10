"""Live ``/part/create`` ``t.List`` bind source for ``#gridDXFParts``.

QuoteOrderEdit ``DoCreateDXFParts`` success binds ``t.List`` as-is:

    i.dataSource.data().toJSON().push(t.List[e])

``slim_filelist_row`` then copies that CadImport / ``#gridDXFParts`` row into
``AddItem_DXFFiles`` FileList. A bind source is a ``t.List`` row that already
has **both** ``InternalData`` and ``ImageString`` nonempty — the shape
Finish can POST without inventing contours.

No live capture yet. Leftover explodes (SC0600, FA Assembly, Skin Assembly,
10098-1, **21785-2** ImageString 13/13 preview, **35136-1** 3× bar
InternalData empty / OpenContourCount=0, **14327-5** flat plate
InternalData empty 1/1 / OpenContourCount empty/null / ProductType null)
returned empty ``InternalData`` on every row. Gold leftover ``a7d6ca50`` ItemList has no
``InternalData`` field (FileList-at-Finish only). Do **not** invent a gold
``t.List`` body. Ops persists the first live nonempty ``t.List`` response
shape here (key names only, never contour JSON).
"""

from __future__ import annotations

from typing import Any

# First live ``/part/create`` ``t.List`` whose Cad rows already have
# nonempty InternalData **and** ImageString. ``None`` until ops captures
# one. Leftover empty explodes are **not** this fixture.
LIVE_PART_CREATE_TLIST_BIND: dict[str, Any] | None = None
