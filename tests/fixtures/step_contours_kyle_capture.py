"""Exact DevTools capture Kyle must grab for STEP Finish Contours.

No live ``/part/create`` ``t.List`` has yet arrived with nonempty
InternalData **and** ImageString. Leftover STEPs (28769-1 / 21785-2 / …)
were keys-present / values-empty. QuoteOrderEdit classify→Finish has no
named fill XHR. Do not invent Contours.

On a **fresh unused** Time STEP whose green Finish shows Contours
(GET ``DataPartPDF.NumberOfContours`` ≥ 1), save the windows below —
key names and emptiness bools only. Never remint spent leftovers.
"""

from __future__ import annotations

from typing import Any

from secturafab.website import kyle_step_contours_devtools_capture

# Spent leftovers — do not remint / PATCH. Capture must be a new PN.
STEP_CONTOURS_CAPTURE_NEVER_REMINT = (
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
