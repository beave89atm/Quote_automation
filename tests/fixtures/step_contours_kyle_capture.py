"""Exact DevTools capture Kyle must grab for STEP Finish Contours.

No live ``/part/create`` ``t.List`` has yet arrived with nonempty
InternalData **and** ImageString. Leftover STEPs (35136-1 / 28769-1 /
21785-2 / …) were keys-present / values-empty. Kyle HAR leftover
35136-1 / 8973f890: Upload → CadImport/Data OpenContourCount=0 →
/part/create 3× bar InternalData empty → AddItem_DXFFiles InternalData
empty bar_flat. Contours never filled. That confirms fail-close; it
does **not** unlock Contours fill. QuoteOrderEdit classify→Finish has
no named fill XHR. Do not invent Contours. Follow-up only: bar_flat
STEP explode vs plate Contours — no silent graft.

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
