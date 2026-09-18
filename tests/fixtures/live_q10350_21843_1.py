"""Q10350 / eb6c48b8 — Time Waco Long/Linear PASS leftover.

  Q10350 / eb6c48b8-36b5-4f8d-85b2-ce964fd9e8f4
  Time Manufacturing Waco / 21843-1
  Hot Rolled Round Bar Ø0.625 × 28.0843 Finish

Bar / Linear path. Not a Contours leftover. invent=false — do
not invent Contours / InternalData / SKU / unit cost / machine /
unstated live GET fields.

Forever-protect; never remint / PATCH.
"""

from __future__ import annotations

from typing import Any

Q10350_21843_1_PASS: dict[str, Any] = {
    "quote_id": "eb6c48b8-36b5-4f8d-85b2-ce964fd9e8f4",
    "quote_id_prefix": "eb6c48b8",
    "quote_number": "Q10350",
    "part_number": "21843-1",
    "customer": "Time Manufacturing Waco",
    "piece": "21843-1",
    "description": "Hot Rolled Round Bar Ø0.625 × 28.0843 Finish",
    "shape": "Hot Rolled Round Bar",
    "diameter_in": 0.625,
    "length_in": 28.0843,
    "path": "long_linear",
    "is_linear": True,
    "is_bar": True,
    "contours_leftover": False,
    "id_unknown": False,
    "pass": True,
    "linear_pass": True,
    "invent": False,
    "invent_contours": False,
    "invent_internaldata": False,
    "zz_del": False,
    "zz_del_number": None,
    "protect": True,
    "readonly": True,
    "do_not_remint": True,
    "do_not_patch": True,
}


def q10350_21843_1_pass_dump() -> dict[str, Any]:
    """Read-only Time Waco Long/Linear PASS leftover. Never remint / PATCH."""
    return dict(Q10350_21843_1_PASS)
