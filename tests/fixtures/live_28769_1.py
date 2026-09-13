"""Spent 28769-1 — ZZ-DEL leftover c146ce6d after empty explode InternalData.

Live unused Time STEP: DoCreateDXFParts t.List had InternalData keys
present and values empty (ImageString preview-only). Optional GET
/CadImport/Data and GET /CadImport/CADData after explode were also
empty — not bindable. Finish correctly refused
(cad_internaldata_empty_after_explode /
step_explode_no_internaldata). Do not invent Contours/InternalData.

Do not remint 28769-1 / c146ce6d. Sibling spent STEPs stay forbidden
(35136-1 / 8973f890, 14327-5 / c5cd8689, 14327-8 / 1cd941c6,
14327-3 / Q10329 / 75f07c2b, 21841-1 / Q10330 / aed89628,
14327-1 / Q10331 / 5e72fe39, Q10332 / ZZ-DEL-wrong-org-Time
(ID unknown). Q10333 / H.6.38 / b5f56ac3 is a Contours PASS
protect (Cad / Contours=1 / 8 bends + Profile / Laser Bay1 /
UC 176.96) — never remint / PATCH / ZZ-DEL. Also 28768-1, 10289-4,
P904271-1, P904272-1, 21785-1/2/3, 35145-1, 11796-1).
"""

from __future__ import annotations

from typing import Any

CAPTURE_COMMIT = "ce1da5a"
SPENT_QUOTE_ID_PREFIX = "c146ce6d"
SPENT_QUOTE_NUMBER = "28769-1"

# Leftover empty explode + CadImport GET shape — key names / emptiness
# only. Never contour JSON or InternalData values.
LIVE_28769_1_CADIMPORT_EMPTY: dict[str, Any] = {
    "quote_id_prefix": SPENT_QUOTE_ID_PREFIX,
    "quote_number": SPENT_QUOTE_NUMBER,
    "readonly": True,
    "zz_del": True,
    "finish_posted": False,
    "finish_refused": True,
    "finish_why": "cad_internaldata_empty_after_explode",
    "step_explode_no_internaldata": True,
    "tlist_bind_source": False,
    "imagestring_without_internaldata": True,
    "internaldata_empty": True,
    "internaldata_empty_n": 1,
    "internaldata_nonempty_n": 0,
    "imagestring_nonempty_n": 1,
    "contours_empty": True,
    "routes": {
        "POST /part/create": {
            "tlist_bind_source": False,
            "internaldata_empty": True,
            "bindable": False,
            "keys_present_values_empty": ("InternalData",),
        },
        "GET /CadImport/Data": {
            "internaldata_empty": True,
            "contours_empty": True,
            "bindable": False,
        },
        "GET /CadImport/CADData": {
            "internaldata_empty": True,
            "contours_empty": True,
            "bindable": False,
            "editor_preview": True,
        },
    },
    "not_fill_xhr": (
        "ConvertTo",
        "UpdateData",
        "UpdateDataNext",
        "Detect*",
        "Remove*",
        "GetDXFData",
        "PartImage",
        "Quote/DXFInternal",
        "GetPerimeterAndWeight",
        "CADData editor preview",
    ),
}


def live_28769_1_cadimport_empty() -> dict[str, Any]:
    """Read-only 28769-1 leftover empty explode/CadImport shape."""
    return dict(LIVE_28769_1_CADIMPORT_EMPTY)
