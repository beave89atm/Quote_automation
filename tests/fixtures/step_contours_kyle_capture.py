"""Exact DevTools capture Kyle must grab for STEP Finish Contours.

No live ``/part/create`` ``t.List`` has yet arrived with nonempty
InternalData **and** ImageString. Leftover STEPs (35136-1 / 28769-1 /
21785-2 / 14327-5 / 14327-8 / 14327-3 / 21841-1 / 14327-1)
were keys-present / values-empty. Q10333 / H.6.38 / b5f56ac3 is a
Contours PASS protect (Kyle Component→Cad + Finish; Laser costs filled)
— never remint / PATCH / ZZ-DEL. Kyle HAR leftover
35136-1 / 8973f890: Upload → CadImport/Data OpenContourCount=0 →
/part/create 3× bar InternalData empty → AddItem_DXFFiles InternalData
empty bar_flat. Live 14327-5 / c5cd8689 flat plate: /part/create n=1
InternalData empty, ImageString preview-only, ProductType null,
CadImport Data/CADData bindable=false, OpenContourCount empty/null.
QuoteOrderEdit ``createAllParts`` has no intervening CadImport/UI XHR.
Exact missing call: ``POST /part/create t.List InternalData+ImageString``.
Contours never filled. Alternate-path hunt (UpdateData / Data / CADData /
ConvertTo / Unfold / ``/part/PartImage`` / PDFGetData) is exhausted —
see ``step_contours_fill_hunt``. Unlock remains Kyle Contours≥1 capture
or Sectura support naming the fill. Do not invent Contours. Plate
matches bar — no silent graft.

Kyle Loom: Component→Cad on Adjust Properties is required for plate
STEP Contours (Q10333 / H.6.38 Safe Cave is the Contours PASS protect
— never remint / PATCH / ZZ-DEL). Automation sets Cad via API/kendo
ProductType=100 + SetPartMode 0, not a UI click. Still fail-close if
Contours empty.

On a **fresh unused** Time STEP whose green Finish shows Contours
(GET ``DataPartPDF.NumberOfContours`` ≥ 1), save the windows below —
key names and emptiness bools only. Never remint spent leftovers.
"""

from __future__ import annotations

from typing import Any

from secturafab.website import kyle_step_contours_devtools_capture

# Spent leftovers — do not remint / PATCH. Capture must be a new PN.
STEP_CONTOURS_CAPTURE_NEVER_REMINT = (
    "35136-1",
    "14327-5",
    "14327-8",
    "Q10329",
    "14327-3",
    "Q10330",
    "21841-1",
    "Q10331",
    "14327-1",
    "Q10332",
    "Q10333",
    "28769-1",
    "28768-1",
    "10289-4",
    "P904271-1",
    "P904272-1",
    "21785-1",
    "21785-2",
    "21785-3",
    "35145-1",
    "11796-1",
)

# Bind source we still need: POST /part/create t.List with both fields nonempty.
STEP_CONTOURS_EXPECTED_BIND = {
    "method": "POST",
    "path": "/part/create",
    "bindable_when": "InternalData nonempty AND ImageString nonempty",
}


def step_contours_kyle_capture() -> dict[str, Any]:
    """Read-only recipe. Same contract as kyle_step_contours_devtools_capture."""
    recipe = kyle_step_contours_devtools_capture()
    recipe["never_remint"] = list(STEP_CONTOURS_CAPTURE_NEVER_REMINT)
    recipe["expected_bind"] = dict(STEP_CONTOURS_EXPECTED_BIND)
    return recipe
