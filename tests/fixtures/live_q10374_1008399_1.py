"""Q10374 / 1008399-1 coverage remint — FAIL-CLOSE leftover.

Live tip e604229: coverage remint FAIL-CLOSE. STEP uploaded.
Plate 1008400 gauge unverified (no local drawing / SharePoint
unreachable). invent=false stop before Contours. Complete Quote
NOT DONE.

Stated only. Do not invent Contours / InternalData / gauge.

Never remint / PATCH Q10374. Do not forbid 1008399-1 (PN remint).
"""

from __future__ import annotations

from typing import Any

Q10374_QUOTE_ID = "beb20d22-173a-4b0d-be8d-c1263538cdb5"
Q10374_QUOTE_ID_PREFIX = "beb20d22"

Q10374_1008399_1_COVERAGE_FAIL: dict[str, Any] = {
    "quote_number": "Q10374",
    "quote_id": Q10374_QUOTE_ID,
    "part_number": "1008399-1",
    "live_probe_tip": "e604229",
    "coverage_remint": True,
    "fail_close": True,
    "step_uploaded": True,
    "complete_quote_done": False,
    "stopped_before_contours": True,
    "kids": (
        {
            "name": "1008400",
            "is_plate": True,
            "gauge_verified": False,
            "gauge_unverified_reason": (
                "no local drawing / SharePoint unreachable"
            ),
        },
    ),
    "invent": False,
    "invent_contours": False,
    "invent_internaldata": False,
    "invent_gauge": False,
    "do_not_remint_quote_number": True,
    "do_not_forbid_part_number": True,
    "do_not_patch": True,
}


def q10374_1008399_1_coverage_fail() -> dict[str, Any]:
    """Read-only Q10374 coverage remint leftover. No invented Contours."""
    out = dict(Q10374_1008399_1_COVERAGE_FAIL)
    out["kids"] = [dict(row) for row in Q10374_1008399_1_COVERAGE_FAIL["kids"]]
    return out
