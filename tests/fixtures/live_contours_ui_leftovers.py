"""Spent Contours UI leftovers — Adjust Properties Contours column absent.

Unfinished UI leftovers. Finish was never clicked. invented=false.
Do not remint / PATCH. Do not invent Contours / InternalData.

    75f07c2b / Q10329 / ZZ-DEL-Q10329-14327-3-contours-ui
      14327-3 L-angle — Contours column absent; Finish never
    aed89628 / Q10330 / ZZ-DEL-Q10330-21841-1-contours-ui
      21841-1 angle/channel — Contours column absent; Finish never
    5e72fe39 / Q10331 / ZZ-DEL-Q10331-14327-1-contours-ui
      14327-1 flat-looking — Contours column absent; Finish never

Keep existing forever-forbids for 14327-5 / c5cd8689 and
14327-8 / 1cd941c6. Fail-close stays locked. Capture must be a new PN.
"""

from __future__ import annotations

from typing import Any

LEFTOVER_CONTOURS_UI: tuple[dict[str, Any], ...] = (
    {
        "quote_id": "75f07c2b-b000-47f4-9caa-c14520e2b068",
        "quote_id_prefix": "75f07c2b",
        "quote_number": "Q10329",
        "part_number": "14327-3",
        "zz_del_number": "ZZ-DEL-Q10329-14327-3-contours-ui",
        "shape": "L-angle",
        "contours_column_absent": True,
        "finish_clicked": False,
        "finish_posted": False,
        "invent": False,
        "unlocks_contours_fill": False,
        "fail_close": True,
        "readonly": True,
        "zz_del": True,
    },
    {
        "quote_id": "aed89628-b018-4b11-852f-bfed5bf8b964",
        "quote_id_prefix": "aed89628",
        "quote_number": "Q10330",
        "part_number": "21841-1",
        "zz_del_number": "ZZ-DEL-Q10330-21841-1-contours-ui",
        "shape": "angle/channel",
        "contours_column_absent": True,
        "finish_clicked": False,
        "finish_posted": False,
        "invent": False,
        "unlocks_contours_fill": False,
        "fail_close": True,
        "readonly": True,
        "zz_del": True,
    },
    {
        "quote_id": "5e72fe39-edc1-467c-925d-f1c8d74cc5d3",
        "quote_id_prefix": "5e72fe39",
        "quote_number": "Q10331",
        "part_number": "14327-1",
        "zz_del_number": "ZZ-DEL-Q10331-14327-1-contours-ui",
        "shape": "flat-looking",
        "contours_column_absent": True,
        "finish_clicked": False,
        "finish_posted": False,
        "invent": False,
        "unlocks_contours_fill": False,
        "fail_close": True,
        "readonly": True,
        "zz_del": True,
    },
)


def leftover_contours_ui_dumps() -> list[dict[str, Any]]:
    """Read-only Contours UI leftovers. Does not unlock Contours fill."""
    return [dict(row) for row in LEFTOVER_CONTOURS_UI]
