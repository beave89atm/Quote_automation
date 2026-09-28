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


def _tree_shape(tree: dict) -> tuple[str, list[dict]] | None:
    """Live GET is ``{Data: [...]}``. The p5 snapshot is ``{rows: [...]}``."""
    data = tree.get("Data")
    if isinstance(data, list):
        return "live", [row for row in data if isinstance(row, dict)]
    rows = tree.get("rows")
    if isinstance(rows, list):
        return "snapshot", [row for row in rows if isinstance(row, dict)]
    return None


def _row_name(row: dict, shape: str) -> str:
    if shape == "snapshot":
        raw = row.get("N") if "N" in row else ""
        return "" if _blank(raw) else str(raw).strip()
    if "ItemNumber" in row and not _blank(row.get("ItemNumber")):
        return str(row["ItemNumber"]).strip()
    desc = row.get("Description") if "Description" in row else None
    if isinstance(desc, str) and desc.strip():
        return desc.strip().split()[0]
    return ""


def _product_type(row: dict, shape: str) -> Any:
    key = "PT" if shape == "snapshot" else "ProductType"
    if key in row:
        return row.get(key)
    alt = "ProductType" if shape == "snapshot" else "PT"
    if alt in row:
        return row.get(alt)
    return None


def _is_assembly(pt: Any) -> bool:
    return pt == 300 or pt == "300"


def _is_component(row: dict, pt: Any) -> bool:
    if pt == 200 or pt == "200" or str(pt or "").strip().casefold() == "component":
        return True
    return row.get("IsComponent") is True


def _parent_link_blank(row: dict, shape: str) -> bool:
    if shape == "snapshot":
        return "AID" not in row or _blank(row.get("AID"))
    # ParentID is the quote id on every live row. The assembly link is
    # AssemblyName / AssemblyID (null on the assembly row itself).
    named = "AssemblyName" in row and not _blank(row.get("AssemblyName"))
    linked = "AssemblyID" in row and not _blank(row.get("AssemblyID"))
    return not (named or linked)


def _op_names(
    row: dict, shape: str, grid_ops: dict[str, str], name: str
) -> list[str] | None:
    if shape == "snapshot":
        if name not in grid_ops:
            return []
        return [grid_ops[name]]
    if "OperationCostList" not in row or not isinstance(row.get("OperationCostList"), list):
        return None
    names: list[str] = []
    for op in row["OperationCostList"]:
        if isinstance(op, dict) and not _blank(op.get("OperationName")):
            names.append(str(op["OperationName"]))
        elif isinstance(op, str) and op.strip():
            names.append(op.strip())
    return names


def _is_laser(op_names: list[str] | None, row: dict, shape: str) -> bool:
    for op in op_names or []:
        token = str(op)
        if token.startswith(_LASER_PREFIX) or token.casefold().startswith("profile"):
            return True
    if shape == "live" and isinstance(row.get("Machine"), str):
        if "laser" in row["Machine"].casefold():
            return True
    return False


def _has_bend(op_names: list[str] | None) -> bool:
    return any("Bend" in str(op) for op in (op_names or []))


def _has_weld(op_names: list[str] | None) -> bool:
    return any("weld" in str(op).casefold() for op in (op_names or []))


def _child_price_sum(kids: list[dict], price_key: str, qty_key: str) -> float | None:
    """Sum of child unit price × qty. None when any price or qty is unproved."""
    total = 0.0
    for row in kids:
        if price_key not in row or qty_key not in row:
            return None
        price = _num(row.get(price_key))
        qty = _qty(row.get(qty_key))
        if price is None or qty is None:
            return None
        total += price * qty
    return total


def _within_one_cent(left: float, right: float) -> bool:
    return abs(round(left * 100.0) - round(right * 100.0)) <= 1


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
    parsed = _tree_shape(tree) if isinstance(tree, dict) else None
    if parsed is None or not parsed[1]:
        return QcReport(
            label=label or "quote",
            status="FLAG",
            flags=["no lines"],
            summary="n/a",
        )
    shape, rows = parsed
    if isinstance(tree, dict) and "Errors" in tree:
        envelope = tree.get("Errors")
        if envelope not in (None, [], "", {}):
            flags.append(f"tree Errors present: {envelope}")
    qty_key = "Q" if shape == "snapshot" else "Quantity"
    unit_key = "U" if shape == "snapshot" else "Length_Units"
    len_key = "Len" if shape == "snapshot" else "Length"
    wid_key = "W" if shape == "snapshot" else "Width"
    contour_key = "C" if shape == "snapshot" else "NumberOfContours"
    err_key = "Err" if shape == "snapshot" else "ErrorCount"
    cost_key = "UC" if shape == "snapshot" else "UnitCost"
    price_key = "UP" if shape == "snapshot" else "UnitPrice"
    ops = parse_grid_ops(tree.get("grid")) if shape == "snapshot" else {}
    if shape == "snapshot" and (
        "grid" not in tree or not isinstance(tree.get("grid"), list)
    ):
        flags.append("grid missing")
    parents = [r for r in rows if _is_assembly(_product_type(r, shape))]
    kids = [r for r in rows if not _is_assembly(_product_type(r, shape))]
    got: dict[str, int] = {}
    qty_missing = False
    for row in kids:
        name = _row_name(row, shape)
        qty = _qty(row.get(qty_key)) if qty_key in row else None
        if not name or qty is None:
            qty_missing = True
            if name:
                flags.append(f"{name}: qty missing")
            continue
        got[name] = qty
    if qty_missing or got != expected:
        flags.append(f"part list mismatch: expected {expected} got {got}")
    names = [_row_name(r, shape) for r in rows]
    dups = sorted({n for n in names if n and names.count(n) > 1})
    if dups:
        flags.append(f"duplicate lines: {dups}")
    if parents:
        loose = [
            _row_name(r, shape) for r in kids if _parent_link_blank(r, shape)
        ]
        loose = [n for n in loose if n]
        if loose:
            flags.append(f"loose top-level lines with assembly present: {loose}")
    all_inch = True
    contours_ok = True
    err_ok = True
    for row in kids:
        name = _row_name(row, shape)
        if not name:
            flags.append("part name missing")
            all_inch = False
            contours_ok = False
            err_ok = False
            continue
        if shape == "live" or "Material" in row or "Thickness" in row:
            if "Material" not in row or _blank(row.get("Material")):
                flags.append(f"{name}: material missing")
            thick = _num(row.get("Thickness")) if "Thickness" in row else None
            if "Thickness" not in row or thick is None or thick <= 0:
                flags.append(f"{name}: thickness missing")
            elif "Thickness_Units" not in row or _blank(row.get("Thickness_Units")):
                flags.append(f"{name}: thickness missing")
            elif str(row.get("Thickness_Units")) != "inch":
                flags.append(
                    f"{name}: thickness units {row.get('Thickness_Units')} not inch"
                )
                all_inch = False
        else:
            desc = row.get("Desc")
            if not isinstance(desc, str) or not desc.strip():
                flags.append(f"{name}: thickness missing")
                flags.append(f"{name}: material missing")
            else:
                if not _THICKNESS_RE.search(desc):
                    flags.append(f"{name}: thickness missing")
                if not _MATERIAL_RE.search(desc):
                    flags.append(f"{name}: material missing")
        pt = _product_type(row, shape)
        if _is_component(row, pt):
            flags.append(f"{name}: producttype_still_component")
        for key, label_s in ((cost_key, "cost"), (price_key, "price")):
            if key not in row or row.get(key) is None:
                flags.append(f"{name}: {label_s} missing")
                continue
            num = _num(row.get(key))
            if num is None or num <= 0:
                flags.append(f"{name}: zero cost/price")
        if unit_key not in row or _blank(row.get(unit_key)):
            flags.append(f"{name}: units missing")
            all_inch = False
        elif str(row.get(unit_key)) != "inch":
            flags.append(f"{name}: units {row.get(unit_key)} not inch")
            all_inch = False
        length = _num(row.get(len_key)) if len_key in row else None
        width = _num(row.get(wid_key)) if wid_key in row else None
        if len_key not in row or wid_key not in row or length is None or width is None:
            flags.append(f"{name}: dims missing")
        elif not (0 < length <= 240 and 0 < width <= 120):
            flags.append(f"{name}: implausible dims L={length} W={width}")
        row_ops = _op_names(row, shape, ops, name)
        if shape == "snapshot" and tree.get("grid") is not None and name not in ops:
            flags.append(f"{name}: grid op missing")
        if shape == "live" and row_ops is None:
            flags.append(f"{name}: operations missing")
        if _is_laser(row_ops, row, shape):
            if contour_key not in row or row.get(contour_key) is None:
                flags.append(f"{name}: Contours missing")
                contours_ok = False
            else:
                contours = _num(row.get(contour_key))
                if contours is None or contours < 1:
                    shown = row.get(contour_key)
                    flags.append(f"{name}: Contours {shown} < 1")
                    contours_ok = False
            if "InternalData" in row and _blank(row.get("InternalData")):
                flags.append(f"{name}: InternalData empty")
                contours_ok = False
        if err_key not in row or row.get(err_key) is None:
            flags.append(f"{name}: ErrorStatus missing")
            err_ok = False
        else:
            err = _num(row.get(err_key))
            if err is None or err != 0:
                flags.append(f"{name}: ErrorStatus {row.get(err_key)}")
                err_ok = False
    parent_price: float | None = None
    for parent in parents:
        name = _row_name(parent, shape)
        if price_key not in parent or parent.get(price_key) is None:
            flags.append(f"{name}: price missing")
        else:
            price = _num(parent.get(price_key))
            if price is None or price <= 0:
                flags.append(f"{name}: zero-price parent")
            elif parent_price is None:
                parent_price = price
        parent_ops = _op_names(parent, shape, ops, name)
        if not _has_weld(parent_ops):
            flags.append(
                f"{name}: weld labor not on parent (waiting on Kyle; not guessed)"
            )
    if len(parents) == 1:
        parent = parents[0]
        name = _row_name(parent, shape)
        child_sum = _child_price_sum(kids, price_key, qty_key)
        proved_parent = _num(parent.get(price_key)) if price_key in parent else None
        if proved_parent is None or child_sum is None:
            flags.append(f"{name}: parent price rollup unproved")
        elif not _within_one_cent(proved_parent, child_sum):
            flags.append(
                f"{name}: parent unit price {_money(proved_parent)} "
                f"is outside $0.01 of child sum {_money(child_sum)}"
            )
    elif len(parents) > 1:
        flags.append("parent price rollup unproved")
    bend_have = 0
    bend_need = 0
    if formed is None:
        flags.append("formed list missing")
    else:
        bend_need = len(formed)
        by_name = {_row_name(row, shape): row for row in rows}
        for name in formed:
            row = by_name.get(name, {})
            if _has_bend(_op_names(row, shape, ops, name)):
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
    """In-page tree read. The page session is used. Cookies are not read."""
    from .chrome_cdp import SessionDeadError, abort_if_session_dead, page_jquery_ajax

    try:
        result = page_jquery_ajax(
            url=TREE_PATH,
            method="GET",
            data={"ParentID": str(quote_id)},
            quote_id=str(quote_id),
        )
    except SessionDeadError:
        raise
    except Exception as exc:
        abort_if_session_dead(body=str(exc), url=str(getattr(exc, "body", "") or ""))
        raise
    body = result.get("body") if isinstance(result, dict) else None
    if isinstance(body, str):
        abort_if_session_dead(body=body, url=body)
    if isinstance(result, dict) and result.get("ok") and isinstance(body, (dict, list)):
        return body
    why = result.get("why") if isinstance(result, dict) else "empty"
    abort_if_session_dead(body=str(body or ""), url=str(why or ""))
    raise RuntimeError(f"in-page tree read failed ({why})")


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
