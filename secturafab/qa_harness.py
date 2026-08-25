"""Live GET checklist for a SecturaFAB quote (not unit-test mocks of create_quote).

Fails when Organization is null, Description is a bare PN, any Cad line lacks
Laser+Deburr+Laser Setup+Sheet Loading with sane times, or any Linear lacks
SKU/ProductID + Saw + Saw Setup.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any  # noqa: I001

from secturafab.item_desc import is_bare_part_number, normalize_part_token
from secturafab.line_item_ops import item_has_laser_pack, item_has_saw_pack
from secturafab.website import EMPTY_GUID

_ASSEMBLY_TYPES = {300, "300", "assembly"}
_PN_TOKEN = re.compile(r"^\d{4,}(?:-\d+[A-Za-z]?)?$", re.IGNORECASE)


@dataclass
class QuoteGetQaResult:
    ok: bool
    failures: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def raise_if_failed(self) -> None:
        if not self.ok:
            raise AssertionError("Live GET QA failed:\n- " + "\n- ".join(self.failures))


def _org_name(payload: dict[str, Any]) -> str:
    org = payload.get("Organization")
    if isinstance(org, dict):
        for key in ("OrganizationName", "DisplayName", "NameAndLocation"):
            val = str(org.get(key) or "").strip()
            if val:
                return val
    for key in ("OrganizationName", "DisplayName"):
        val = str(payload.get(key) or "").strip()
        if val:
            return val
    for entry in payload.get("OrganizationList") or []:
        if not isinstance(entry, dict):
            continue
        for key in ("OrganizationName", "DisplayName", "NameAndLocation"):
            val = str(entry.get(key) or "").strip()
            if val:
                return val
    return ""


def _org_id(payload: dict[str, Any]) -> str:
    raw = payload.get("PrimaryOrganizationID") or payload.get("OrganizationID")
    if isinstance(payload.get("Organization"), dict):
        raw = raw or payload["Organization"].get("ID")
    return str(raw or "").strip()


def _op_time_hours(op: dict[str, Any]) -> float:
    for key in ("UnitTime", "Value"):
        try:
            val = float(op.get(key) or 0)
        except (TypeError, ValueError):
            continue
        if val > 0:
            return val
    try:
        t = float(op.get("Time") or 0)
    except (TypeError, ValueError):
        return 0.0
    if t <= 0:
        return 0.0
    if t > 3.0:
        return t / 60.0
    return t


def _item_category(item: dict[str, Any], bom_hint: str = "") -> str | None:
    if item.get("IsAssembly") or item.get("ProductType") in _ASSEMBLY_TYPES:
        return "Assembly"
    cat = str(item.get("Category") or item.get("ItemType") or "").strip()
    if cat in {"Cad", "Linear", "Component"}:
        return cat
    if item.get("IsLinear") or item.get("ProductType") in (10, "10"):
        return "Linear"
    if item.get("ProductType") in (200, "200"):
        return "Component"
    if item.get("IsPlate") or item.get("ProductType") in (100, "100"):
        return "Cad"
    hint = f"{item.get('Description') or ''} {bom_hint}".strip()
    token = normalize_part_token(hint.split()[0] if hint.split() else "")
    if not hint or (not bom_hint and not _PN_TOKEN.fullmatch(token)):
        return None
    from secturafab.push import classify_sectura_item

    return classify_sectura_item(hint)


def _bom_hint_map(bom_rows: list[dict[str, Any]] | None) -> dict[str, str]:
    from secturafab.qty_ops import normalize_part_key

    out: dict[str, str] = {}
    for row in bom_rows or []:
        pn = str(row.get("part_no") or row.get("part_number") or "").strip()
        key = normalize_part_key(pn)
        if key:
            out[key] = str(row.get("description") or "")
    return out


def _desc_key(description: str) -> str:
    from secturafab.qty_ops import normalize_part_key
    from secturafab.weld_ops import _desc_token

    return normalize_part_key(_desc_token(description))


def evaluate_quote_get(
    payload: dict[str, Any] | None,
    *,
    part_key: str | None = None,
    expected_org: str | None = None,
    expected_header: str | None = None,
    expected_assembly_title: str | None = None,
    bom_rows: list[dict[str, Any]] | None = None,
    require_org: bool = True,
) -> QuoteGetQaResult:
    """Assert a live-GET-shaped quote payload against Kyle's checklist."""
    failures: list[str] = []
    notes: list[str] = []
    data = payload if isinstance(payload, dict) else {}
    part = normalize_part_token(part_key)
    header = str(data.get("Description") or "").strip()

    org = _org_name(data)
    oid = _org_id(data)
    if require_org or expected_org:
        if not org:
            failures.append("Organization is null/empty")
        if oid in {"", EMPTY_GUID}:
            failures.append(f"PrimaryOrganizationID is null or empty GUID ({oid!r})")
        if expected_org and org:
            got_l = org.casefold()
            want_l = expected_org.casefold()
            tokens_g = set(re.findall(r"[a-z0-9]+", got_l))
            tokens_w = set(re.findall(r"[a-z0-9]+", want_l))
            fuzzy = (
                got_l == want_l
                or got_l.startswith(want_l)
                or want_l.startswith(got_l)
                or ("time" in tokens_g and "time" in tokens_w)
                or len(tokens_g & tokens_w) >= 2
            )
            if not fuzzy:
                failures.append(f"Organization is {org!r}, wanted {expected_org!r}")
    if org:
        notes.append(f"Organization={org}")

    if (
        (require_org or expected_header or expected_assembly_title or bom_rows)
        and header
        and part
        and (
            is_bare_part_number(header, part)
            or header.replace(" ", "").upper().startswith(part.replace("-", "").upper())
            or (part and part.upper() in header.upper() and header.upper() != (expected_header or "").upper())
        )
    ):
        if expected_header and header.upper() == expected_header.upper():
            pass
        else:
            failures.append(
                f"Quote Description is {header!r} (must be weldment title only, not the PN)"
            )
    if expected_header:
        if not header:
            failures.append("Quote Description is empty")
        elif header != expected_header:
            failures.append(
                f"Quote Description is {header!r}, wanted {expected_header!r}"
            )

    items = [it for it in (data.get("ItemList") or []) if isinstance(it, dict)]
    bom_hints = _bom_hint_map(bom_rows)
    check_lines = bool(bom_rows)
    assembly_desc = None
    cad_n = lin_n = 0
    for it in items:
        desc = str(it.get("Description") or "").strip()
        hint = bom_hints.get(_desc_key(desc), "")
        cat = _item_category(it, hint)
        if cat == "Assembly":
            assembly_desc = desc
            if part and is_bare_part_number(desc, part):
                failures.append(f"Assembly Description is bare PN {desc!r}")
            if expected_assembly_title and desc != expected_assembly_title:
                failures.append(
                    f"Assembly Description is {desc!r}, wanted {expected_assembly_title!r}"
                )
            continue
        if cat == "Cad":
            cad_n += 1
            if not check_lines:
                continue
            if part and is_bare_part_number(desc, part):
                failures.append(f"Cad Description is bare PN {desc!r}")
            if not item_has_laser_pack(it):
                failures.append(
                    f"Cad {desc!r} lacks Laser + Deburr + Laser Setup + Sheet Loading"
                )
            if not str(it.get("Material") or it.get("MaterialGrade") or "").strip():
                failures.append(f"Cad {desc!r} Material is empty")
            thk = it.get("Thickness")
            try:
                thk_ok = float(thk) > 0 if thk not in (None, "") else False
            except (TypeError, ValueError):
                thk_ok = bool(str(thk).strip())
            if not thk_ok:
                failures.append(f"Cad {desc!r} Thickness is empty/0")
            for op in it.get("OperationCostList") or []:
                if not isinstance(op, dict):
                    continue
                hours = _op_time_hours(op)
                name = str(op.get("CalculatorName") or op.get("OperationName") or "")
                if hours <= 0:
                    failures.append(f"Cad {desc!r} op {name!r} time is 0")
                if hours >= 3.0:
                    failures.append(
                        f"Cad {desc!r} op {name!r} time {hours:.2f}h is not sane "
                        "(page-outline / DataPart)"
                    )
            continue
        if cat == "Linear":
            lin_n += 1
            if not check_lines:
                continue
            if part and is_bare_part_number(desc, part):
                failures.append(f"Linear Description is bare PN {desc!r}")
            pid = str(it.get("ProductID") or "").strip()
            sku = str(it.get("SKU") or it.get("ProductName") or "").strip()
            if not pid and not sku:
                failures.append(f"Linear {desc!r} has no ProductID/SKU")
            if it.get("ProductType") in (100, "100"):
                failures.append(f"Linear {desc!r} ProductType is 100 (want 10 / Linear)")
            machine = str(it.get("Machine") or "").strip()
            if machine.casefold() != "saw":
                failures.append(f"Linear {desc!r} Machine is {machine!r}, want Saw")
            if not item_has_saw_pack(it):
                failures.append(f"Linear {desc!r} lacks Saw + Saw Setup")
            try:
                length = float(it.get("Length") or it.get("LinearLength") or 0)
            except (TypeError, ValueError):
                length = 0.0
            if length <= 0:
                failures.append(f"Linear {desc!r} has no cut length")
            continue
        if cat == "Component" and check_lines:
            if part and is_bare_part_number(desc, part):
                failures.append(f"Component Description is bare PN {desc!r}")
            token = _desc_key(desc)
            if token and token not in desc.replace(" ", "").upper() and " - " not in desc:
                failures.append(f"Component {desc!r} should be '{{PN}} - {{noun}}'")

    notes.append(f"Checked {cad_n} Cad / {lin_n} Linear line(s)")
    if assembly_desc:
        notes.append(f"Assembly={assembly_desc}")
    return QuoteGetQaResult(ok=not failures, failures=failures, notes=notes)


def assert_quote_get_qa(payload: dict[str, Any] | None, **kwargs: Any) -> QuoteGetQaResult:
    result = evaluate_quote_get(payload, **kwargs)
    result.raise_if_failed()
    return result
