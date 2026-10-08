"""Bend count from the named Bend operation, not from drawing callouts.

The count is ``NumberOfBends`` on the line's ``OperationParamList`` entry
whose ``CalcName`` is ``Bend`` (or ``CalcParamType`` is ``bend``).
``Time`` on that entry is seconds and equals ``NumberOfBends × TimePerBend``.

The ``OperationCostList`` row with ``CostCategory`` ``Bend`` is labour
(``Cost_Units`` hour). It is not the bend count.

No captured request writes ``NumberOfBends``. The reads in this repo are
``GET /Quote/QuoteItem_ReadTreeListData`` and ``GET /Quote/GetItem_AddView``.
``POST /Quote/AddOperation`` is the weld payload only (``op_weld``, weld
inches, per-unit time). A network capture of Kyle editing Number of Bends
in the UI is required before a write can be wired.
"""

from __future__ import annotations

from typing import Any

# Read field. Not written by any endpoint captured in this repo.
BEND_COUNT_FIELD = "NumberOfBends"
BEND_COUNT_WRITE_ENDPOINT = None
BEND_COUNT_NOT_SET = "Bend op Number of Bends not set"
BEND_COUNT_TIME_MISMATCH = "Bend op Time is not NumberOfBends × TimePerBend"
BEND_COUNT_DRAWING_MISMATCH = (
    "Bend op Number of Bends does not match the drawing count"
)
BEND_COUNT_WRITE_GAP_NOTE = (
    "No captured request writes NumberOfBends. "
    "Reads are /Quote/QuoteItem_ReadTreeListData and /Quote/GetItem_AddView. "
    "POST /Quote/AddOperation is the weld payload only. "
    "A network capture of Kyle editing Number of Bends in the UI is needed."
)


def _param_lists(item: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(item, dict):
        return []
    rows = item.get("OperationParamList") or []
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def bend_param_entries(item: dict[str, Any] | None) -> list[dict[str, Any]]:
    """DataOperationList rows for the operation named Bend."""
    found: list[dict[str, Any]] = []
    for row in _param_lists(item):
        data = row.get("DataOperationList") or []
        if not isinstance(data, list):
            continue
        for entry in data:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("CalcName") or "")
            kind = str(entry.get("CalcParamType") or "")
            if name == "Bend" or kind.casefold() == "bend":
                found.append(entry)
    return found


def _whole_number(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def line_bend_count(
    item: dict[str, Any] | None,
    *,
    formed: bool,
    expected: int | None = None,
) -> tuple[int, str | None]:
    """Line bend count, or ``(0, flag)`` when a formed line is not gold.

    A flat part (no bend signals) is count 0 and does not need a Bend op.
    A formed part needs one Bend param, ``NumberOfBends`` equal to the
    drawing count when that count is known, and
    ``Time == NumberOfBends × TimePerBend``.
    """
    if not formed:
        return 0, None
    entries = bend_param_entries(item)
    if len(entries) != 1:
        return 0, BEND_COUNT_NOT_SET
    entry = entries[0]
    count = _whole_number(entry.get(BEND_COUNT_FIELD))
    if count is None or count < 1:
        return 0, BEND_COUNT_NOT_SET
    per_bend = _whole_number(entry.get("TimePerBend"))
    total = _whole_number(entry.get("Time"))
    units = str(entry.get("Time_Units") or "second").casefold()
    if per_bend is None or total is None or units != "second" or total != count * per_bend:
        return 0, BEND_COUNT_TIME_MISMATCH
    if expected is not None and count != expected:
        return 0, BEND_COUNT_DRAWING_MISMATCH
    return count, None
