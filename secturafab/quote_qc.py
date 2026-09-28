"""Read-only pre-handoff check for one Sectura quote.

Reads ``/Quote/QuoteItem_ReadTreeListData?ParentID=<id>`` plus an
expected LOM/STEP part list and prints PASS or FLAG. Writes nothing.
Unknown or missing fields FLAG. Never fills L/W, Contours, InternalData,
or weld minutes. invent=false.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

TREE_PATH = "/Quote/QuoteItem_ReadTreeListData"
_LASER_PREFIX = "PR"
_MATERIAL_RE = re.compile(
    r"\b(A36|304|316|5052|6061|A1011|A572|HRPO|CRS|GALV)\b"
)
_THICKNESS_RE = re.compile(r"(\d+\s*Ga|\d+/\d+\"|\d*\.\d+\")")
_GRID_RE = re.compile(r"\d+\s+\d+\s+\d+\s+(\S+)\s+(.*)")
_OP_RE = re.compile(r"\sin\s+(\S+)\s+(part|assembly)\b")


@dataclass
class QcReport:
    label: str
    status: str
    flags: list[str] = field(default_factory=list)
    summary: str = ""

    def text(self) -> str:
        lines = [f"{self.label} — {self.status}"]
        for item in self.flags:
            lines.append(f" - {item}")
        if self.summary:
            lines.append(self.summary)
        return "\n".join(lines)


def _blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not str(value).strip())


def _qty(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    text = str(value).strip()
    if text.isdigit():
        return int(text)
    return None


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _money(value: float) -> str:
    return f"${value:,.2f}"


def parse_grid_ops(grid: Any) -> dict[str, str]:
    ops: dict[str, str] = {}
    if not isinstance(grid, list):
        return ops
    for line in grid:
        match = _GRID_RE.match(str(line))
        if not match:
            continue
        name, rest = match.groups()
        op_match = _OP_RE.search(rest)
        ops[name] = op_match.group(1) if op_match else ""
    return ops


def load_expected(path: str | Path) -> tuple[dict[str, int], list[str] | None, str]:
    """Expected LOM/STEP list.

    JSON object of name → qty, or ``{"parts": {...}, "formed": [...], "label": "..."}``.
    A missing ``formed`` key stays unknown (FLAG). An empty list means
    the caller proved there are no formed parts.
    """
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("expected file must be a JSON object")
    label = ""
    formed: list[str] | None
    if "parts" in raw:
        parts_raw = raw.get("parts")
        label = str(raw.get("label") or "")
        if "formed" not in raw or raw.get("formed") is None:
            formed = None
        elif isinstance(raw.get("formed"), list):
            formed = [str(name) for name in raw["formed"]]
        else:
            raise ValueError("formed must be a list of part names")
    else:
        parts_raw = raw
        formed = None
    if not isinstance(parts_raw, dict) or not parts_raw:
        raise ValueError("expected part list is empty")
    parts: dict[str, int] = {}
    for name, qty in parts_raw.items():
        parsed = _qty(qty)
        if parsed is None:
            raise ValueError(f"expected qty for {name} is missing")
        parts[str(name)] = parsed
    return parts, formed, label


def check_tree(
    tree: Any,
    expected: dict[str, int],
    *,
    formed: list[str] | None = None,
    label: str = "",
) -> QcReport:
    """FLAG unless the tree proves every §12 check. Never default a field."""
    flags: list[str] = []
    if not isinstance(tree, dict) or not isinstance(tree.get("rows"), list):
        return QcReport(
            label=label or "quote",
            status="FLAG",
            flags=["tree rows missing"],
            summary="part list mismatch · units not all inch · Contours not ok · formed unknown · Err not 0 · price missing",
        )
    rows = [r for r in tree["rows"] if isinstance(r, dict)]
    ops = parse_grid_ops(tree.get("grid"))
    if "grid" not in tree or not isinstance(tree.get("grid"), list):
        flags.append("grid missing")
    parents = [r for r in rows if r.get("PT") == 300]
    kids = [r for r in rows if r.get("PT") != 300]
    got: dict[str, int] = {}
    qty_missing = False
    for row in kids:
        name = str(row.get("N") or "")
        qty = _qty(row.get("Q")) if "Q" in row else None
        if not name or qty is None:
            qty_missing = True
            if name:
                flags.append(f"{name}: qty missing")
            continue
        got[name] = qty
    if qty_missing or got != expected:
        flags.append(f"part list mismatch: expected {expected} got {got}")
    names = [str(r.get("N") or "") for r in rows]
    dups = sorted({n for n in names if n and names.count(n) > 1})
    if dups:
        flags.append(f"duplicate lines: {dups}")
    if parents:
        loose = [
            str(r.get("N") or "")
            for r in kids
            if "AID" not in r or _blank(r.get("AID"))
        ]
        loose = [n for n in loose if n]
        if loose:
            flags.append(f"loose top-level lines with assembly present: {loose}")
    all_inch = True
    contours_ok = True
    err_ok = True
    for row in kids:
        name = str(row.get("N") or "")
        if not name:
            flags.append("part name missing")
            all_inch = False
            contours_ok = False
            err_ok = False
            continue
        desc = row.get("Desc")
        if not isinstance(desc, str) or not desc.strip():
            flags.append(f"{name}: thickness missing")
            flags.append(f"{name}: material missing")
        else:
            if not _THICKNESS_RE.search(desc):
                flags.append(f"{name}: thickness missing")
            if not _MATERIAL_RE.search(desc):
                flags.append(f"{name}: material missing")
        pt = row.get("PT")
        if pt == 200 or pt == "200" or str(pt or "").strip().casefold() == "component":
            flags.append(f"{name}: producttype_still_component")
        for key, label_s in (("UC", "cost"), ("UP", "price")):
            if key not in row or row.get(key) is None:
                flags.append(f"{name}: {label_s} missing")
                continue
            num = _num(row.get(key))
            if num is None or num <= 0:
                flags.append(f"{name}: zero cost/price")
        if "U" not in row or _blank(row.get("U")):
            flags.append(f"{name}: units missing")
            all_inch = False
        elif str(row.get("U")) != "inch":
            flags.append(f"{name}: units {row.get('U')} not inch")
            all_inch = False
        length = _num(row.get("Len")) if "Len" in row else None
        width = _num(row.get("W")) if "W" in row else None
        if "Len" not in row or "W" not in row or length is None or width is None:
            flags.append(f"{name}: dims missing")
        elif not (0 < length <= 240 and 0 < width <= 120):
            flags.append(f"{name}: implausible dims L={length} W={width}")
        op = ops.get(name, "")
        if tree.get("grid") is not None and name not in ops:
            flags.append(f"{name}: grid op missing")
        if str(op).startswith(_LASER_PREFIX):
            if "C" not in row or row.get("C") is None:
                flags.append(f"{name}: Contours missing")
                contours_ok = False
            else:
                contours = _num(row.get("C"))
                if contours is None or contours < 1:
                    shown = row.get("C")
                    flags.append(f"{name}: Contours {shown} < 1")
                    contours_ok = False
            if "InternalData" in row and _blank(row.get("InternalData")):
                flags.append(f"{name}: InternalData empty")
                contours_ok = False
        if "Err" not in row or row.get("Err") is None:
            flags.append(f"{name}: ErrorStatus missing")
            err_ok = False
        else:
            err = _num(row.get("Err"))
            if err is None or err != 0:
                flags.append(f"{name}: ErrorStatus {row.get('Err')}")
                err_ok = False
    parent_price: float | None = None
    for parent in parents:
        name = str(parent.get("N") or "")
        if "UP" not in parent or parent.get("UP") is None:
            flags.append(f"{name}: price missing")
        else:
            price = _num(parent.get("UP"))
            if price is None or price <= 0:
                flags.append(f"{name}: zero-price parent")
            elif parent_price is None:
                parent_price = price
        op = ops.get(name, "")
        if "weld" not in str(op).lower():
            flags.append(
                f"{name}: weld labor not on parent (waiting on Kyle; not guessed)"
            )
    if not parents:
        flags.append("weld labor not on parent (waiting on Kyle; not guessed)")
    bend_have = 0
    bend_need = 0
    if formed is None:
        flags.append("formed list missing")
    else:
        bend_need = len(formed)
        for name in formed:
            op = ops.get(name, "")
            if "Bend" in op:
                bend_have += 1
            else:
                flags.append(f"{name}: formed part has no Bend op")
    pcs: int | None = None
    if not qty_missing and got:
        pcs = sum(got.values())
    match = (not qty_missing) and got == expected
    if match and pcs is not None:
        head = f"{len(got)} parts / {pcs} pcs match LOM"
    else:
        head = "part list mismatch"
    if formed is None:
        bends = "formed unknown"
    else:
        bends = f"{bend_have}/{bend_need} formed have Bend"
    price_s = _money(parent_price) if parent_price is not None else "price missing"
    summary = " · ".join(
        [
            head,
            "all inch" if all_inch else "units not all inch",
            "Contours ok" if contours_ok else "Contours not ok",
            bends,
            "Err 0" if err_ok else "Err not 0",
            price_s,
        ]
    )
    status = "PASS" if not flags else "FLAG"
    return QcReport(label=label or "quote", status=status, flags=flags, summary=summary)


def fetch_tree(quote_id: str, *, reader: Callable[[str], Any]) -> Any:
    """Read the quote tree through a caller-supplied reader. Does not write."""
    return reader(str(quote_id))


def _default_reader(quote_id: str) -> Any:
    from .chrome_cdp import SessionDeadError, abort_if_session_dead
    from .client import SecturaFabClient

    client = SecturaFabClient()
    try:
        data = client.quote_item_read_treelist(str(quote_id))
    except SessionDeadError:
        raise
    except Exception as exc:
        abort_if_session_dead(body=str(exc), url=str(getattr(exc, "body", "") or ""))
        raise
    if isinstance(data, str):
        abort_if_session_dead(body=data, url=data)
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m secturafab.quote_qc",
        description=(
            "Read-only pre-handoff check. "
            f"Reads {TREE_PATH}?ParentID=<id> and writes nothing."
        ),
    )
    parser.add_argument("--quote", required=True, help="Quote id (ParentID)")
    parser.add_argument(
        "--expected",
        required=True,
        help="JSON LOM/STEP part list (name → qty), optional formed and label",
    )
    parser.add_argument(
        "--tree",
        default="",
        help="Offline tree snapshot. Skips the live read.",
    )
    parser.add_argument("--label", default="", help="Report title")
    args = parser.parse_args(argv)
    parts, formed, file_label = load_expected(args.expected)
    label = str(args.label or file_label or args.quote)
    try:
        if args.tree:
            tree = json.loads(Path(args.tree).read_text(encoding="utf-8"))
        else:
            tree = fetch_tree(args.quote, reader=_default_reader)
    except Exception as exc:
        reason = getattr(exc, "reason", "")
        from .chrome_cdp import SessionDeadError

        if isinstance(exc, SessionDeadError) or reason:
            print(f"{label} — FLAG")
            print(f" - session dead ({reason or exc})")
            return 2
        raise
    report = check_tree(tree, parts, formed=formed, label=label)
    print(report.text())
    return 0 if report.status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
