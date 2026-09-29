"""Pick the existing push path from the files on a hosted job.

Unknown mixes fail closed. This module does not invent a part list, a
weld rate, or a quote description. Sectura is contacted only by the
search and push callables, which tests replace.
"""

from __future__ import annotations

import os
import re
import zipfile
from pathlib import Path
from typing import Any, Callable

from secturafab.push import PushResult, classify_sectura_item
from secturafab.step_classify import (
    STOCK_BAR_KINDS,
    STOCK_OTHER,
    STOCK_STRONG_PLATE,
    classify_step_file,
)

_WELD_NAME = re.compile(r"(?i)weldment|assembly|\bassy\b|\bformed\b|\bplate\b")
_STEP = {".step", ".stp"}
_DRAWING = {".pdf"}
_DXF = {".dxf"}


class SecturaSearchError(RuntimeError):
    pass


def classify_hosted_files(paths: list[Path]) -> tuple[str, str]:
    """Return ``(path_name, "")`` or ``("", reason)``.

    ``step_page_native`` is the weldment/formed STEP page path.
    ``pdf_image_files`` is Image Files plus Long.
    ``linear`` is the Long path. Anything else is a reason, not a guess.
    """
    if not paths:
        return "", "files_missing"
    steps = [p for p in paths if p.suffix.lower() in _STEP]
    pdfs = [p for p in paths if p.suffix.lower() in _DRAWING]
    dxfs = [p for p in paths if p.suffix.lower() in _DXF]
    other = [
        p
        for p in paths
        if p.suffix.lower() not in _STEP | _DRAWING | _DXF
    ]
    if other or (steps and dxfs) or len(steps) > 1 or len(pdfs) > 1 or len(dxfs) > 1:
        return "", "unknown_file_mix"
    if steps and len(pdfs) > 1:
        return "", "unknown_file_mix"
    if dxfs and pdfs:
        return "", "unknown_file_mix"
    if dxfs:
        return "", "unknown_file_mix"
    if steps:
        return _classify_step(steps[0], pdfs)
    if pdfs:
        return "pdf_image_files", ""
    return "", "unknown_file_mix"


def _classify_step(step: Path, pdfs: list[Path]) -> tuple[str, str]:
    del pdfs
    stock = classify_step_file(step)
    if not stock:
        return "", "step_unreadable"
    kind = str(stock.get("kind") or "")
    name = step.stem
    named_weld = bool(_WELD_NAME.search(name))
    named_linear = classify_sectura_item(name) == "Linear"
    if kind == STOCK_STRONG_PLATE and named_linear:
        return "", "unknown_file_mix"
    if kind in STOCK_BAR_KINDS and named_weld:
        return "", "unknown_file_mix"
    if kind == STOCK_STRONG_PLATE or (named_weld and kind != STOCK_OTHER):
        return "step_page_native", ""
    if named_weld and kind == STOCK_OTHER:
        return "", "ambiguous_step_stock"
    if kind in STOCK_BAR_KINDS:
        if not named_linear:
            return "", "linear_name_missing"
        return "linear", ""
    return "", "ambiguous_step_stock"


def expand_zip_files(paths: list[Path], dest: Path) -> tuple[list[Path], str]:
    dest.mkdir(parents=True, exist_ok=True)
    out: list[Path] = []
    for path in paths:
        if path.suffix.lower() != ".zip":
            out.append(path)
            continue
        if not zipfile.is_zipfile(path):
            return [], "unknown_file_mix"
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                name = Path(info.filename).name
                if not name or name.startswith("."):
                    continue
                if Path(name).suffix.lower() == ".zip":
                    return [], "unknown_file_mix"
                target = dest / name
                if not target.resolve().is_relative_to(dest.resolve()):
                    return [], "unknown_file_mix"
                target.write_bytes(archive.read(info))
                out.append(target)
    return out, ""


def quote_keys(paths: list[Path], job: dict[str, Any]) -> tuple[str, str]:
    """QuoteNumber from the part key. Description only when a title block says so."""
    from secturafab.push import _resolve_part_key

    pdf = next((p for p in paths if p.suffix.lower() == ".pdf" and p.is_file()), None)
    title = ""
    for path in paths:
        if path.suffix.lower() in _STEP | _DRAWING | _DXF:
            title = path.stem
            break
    number = _resolve_part_key(
        title=title,
        pdf_filename=pdf.name if pdf else None,
        library={},
        pdf_path=pdf,
    )
    description = ""
    if pdf is not None:
        from quote_core.drawing_title import extract_assembly_description

        found = extract_assembly_description(part_key=number or title, pdf_path=pdf)
        description = str(found or "").strip()
    del job
    return str(number or "").strip(), description


def live_search(number: str, description: str) -> dict[str, str] | None:
    """Read-only QuoteNumber lookup, then Description on the quote list."""
    from secturafab.push import SecturaFabPushService

    service = SecturaFabPushService()
    if number:
        try:
            found = service.find_quote_by_number(number)
        except Exception as exc:
            raise SecturaSearchError("sectura_search_failed") from exc
        if isinstance(found, dict) and (found.get("ID") or found.get("QuoteID")):
            return _hit(found, number)
    if description:
        return _search_description(service.client, description)
    return None


def _hit(row: dict[str, Any], number: str) -> dict[str, str]:
    return {
        "id": str(row.get("ID") or row.get("QuoteID") or "").strip(),
        "number": str(row.get("QuoteNumber") or number or "").strip(),
        "description": str(row.get("Description") or "").strip(),
    }


def _search_description(client: Any, description: str) -> dict[str, str] | None:
    want = description.strip().casefold()
    for page in range(1, 6):
        try:
            response = client.request(
                "GET",
                "v1/quote",
                params={"pageNumber": page, "pageSize": 50},
            )
        except Exception as exc:
            raise SecturaSearchError("sectura_search_failed") from exc
        if getattr(response, "status_code", 500) >= 400:
            raise SecturaSearchError("sectura_search_failed")
        try:
            payload = client._parse_or_raise(response)
        except Exception as exc:
            raise SecturaSearchError("sectura_search_failed") from exc
        rows = _list_rows(payload)
        if rows is None:
            raise SecturaSearchError("sectura_search_failed")
        if not rows:
            return None
        for row in rows:
            if str(row.get("Description") or "").strip().casefold() == want:
                return _hit(row, "")
    return None


def _list_rows(payload: Any) -> list[dict[str, Any]] | None:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("Data", "data", "items", "value"):
            rows = payload.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
    return None


def push_selected(kind: str, paths: list[Path], job: dict[str, Any]) -> PushResult:
    """Call the existing ``push_job`` entry for the path ``kind`` names."""
    from secturafab.push import SecturaFabPushService

    pdf = next((p for p in paths if p.suffix.lower() == ".pdf"), None)
    step = next((p for p in paths if p.suffix.lower() in _STEP), None)
    number, description = quote_keys(paths, job)
    title = number or (step.stem if step else "") or (pdf.stem if pdf else "") or str(job.get("customer") or "")
    stp_path = step if kind == "step_page_native" else None
    if kind == "linear":
        title = (step or pdf or paths[0]).stem
        stp_path = None
    service = SecturaFabPushService()
    return service.push_job(
        title=title,
        pdf_filename=pdf.name if pdf else None,
        pdf_path=pdf,
        stp_path=stp_path,
        takeoff={"library": {}},
        times=None,
        job_id=None,
    )


def materialize_files(job: dict[str, Any], dest: Path) -> list[Path]:
    dest.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    files = job.get("files") or []
    if not isinstance(files, list) or not files:
        return paths
    base = (os.getenv("HOSTED_API_BASE") or "").strip()
    token = (os.getenv("HOSTED_WORKER_TOKEN") or "").strip()
    use_api = bool(base and token and not all(isinstance(item, dict) and item.get("local_path") for item in files))
    for item in files:
        if not isinstance(item, dict):
            continue
        local = str(item.get("local_path") or "").strip()
        if local:
            paths.append(Path(local))
            continue
        name = Path(str(item.get("name") or "file")).name
        target = dest / name
        if use_api:
            target.write_bytes(_download_api(base, token, str(job.get("id") or ""), item))
        else:
            from .hosted_queue import blob_store

            target.write_bytes(
                blob_store().get(str(item.get("blob_key") or ""), url=str(item.get("url") or ""))
            )
        paths.append(target)
    return paths


def _download_api(base: str, token: str, job_id: str, item: dict[str, Any]) -> bytes:
    import urllib.parse
    import urllib.request

    query = urllib.parse.urlencode(
        {"job_id": job_id, "key": str(item.get("blob_key") or "")}
    )
    req = urllib.request.Request(
        base.rstrip("/") + "/api/hosted/worker/file?" + query,
        headers={"X-Worker-Token": token, "Accept": "application/octet-stream"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = resp.read()
    if not body:
        raise ValueError("blob_missing")
    return body


def _qc_report(
    tree: Any,
    *,
    path_name: str,
    label: str,
    expected: dict[str, int] | None,
) -> dict[str, Any]:
    from secturafab.quote_qc import (
        _is_assembly,
        _product_type,
        _qty,
        _row_name,
        _tree_shape,
        check_tree,
    )

    flags = ["expected part list missing"] if not expected else []
    if tree is None:
        flags.append("tree_read_failed")
        return {"path": path_name, "status": "FLAG", "flags": flags, "summary": "", "tree": None}
    parts = expected
    if parts is None:
        parsed = _tree_shape(tree) if isinstance(tree, dict) else None
        parts = {}
        if parsed is not None:
            shape, rows = parsed
            qty_key = "Q" if shape == "snapshot" else "Quantity"
            for row in rows:
                if _is_assembly(_product_type(row, shape)):
                    continue
                name = _row_name(row, shape)
                qty = _qty(row.get(qty_key)) if qty_key in row else None
                if name and qty is not None:
                    parts[name] = qty
    if not parts:
        flags.append("no lines")
        return {"path": path_name, "status": "FLAG", "flags": flags, "summary": "", "tree": tree}
    report = check_tree(tree, parts, formed=None, label=label or path_name)
    merged = list(flags)
    merged.extend(report.flags)
    return {
        "path": path_name,
        "status": "FLAG" if merged else report.status,
        "flags": merged,
        "summary": report.summary,
        "tree": tree,
    }


def execute_hosted_job(
    job: dict[str, Any],
    *,
    search: Callable[[str, str], dict[str, str] | None] | None = None,
    push: Callable[[str, list[Path], dict[str, Any]], PushResult] | None = None,
    read_tree: Callable[[str], Any] | None = None,
    workdir: Path | None = None,
) -> dict[str, Any]:
    """Search, then push the selected path, then QC. No live call until search/push."""
    if str(job.get("sectura_quote_id") or "").strip() or str(job.get("sectura_quote_number") or "").strip():
        return {
            "status": "failed",
            "error": "existing_sectura_quote",
            "sectura_quote_number": str(job.get("sectura_quote_number") or ""),
            "sectura_quote_id": str(job.get("sectura_quote_id") or ""),
            "qc_report": {"path": "", "status": "FLAG", "flags": ["existing_sectura_quote"], "tree": None},
        }
    import tempfile

    root = workdir or Path(tempfile.mkdtemp(prefix="hosted-job-"))
    try:
        staged = materialize_files(job, root / "in")
    except Exception:
        return _failed("blob_missing")
    expanded, zip_reason = expand_zip_files(staged, root / "zip")
    if zip_reason:
        return _failed(zip_reason)
    kind, reason = classify_hosted_files(expanded)
    if not kind:
        return _failed(reason)
    number, description = quote_keys(expanded, job)
    if not number and not description:
        return _failed("quote_key_missing")
    finder = search or live_search
    try:
        existing = finder(number, description)
    except SecturaSearchError:
        return _failed("sectura_search_failed")
    if existing:
        return {
            "status": "failed",
            "error": "existing_sectura_quote",
            "sectura_quote_number": existing.get("number") or number,
            "sectura_quote_id": existing.get("id") or "",
            "qc_report": {
                "path": kind,
                "status": "FLAG",
                "flags": ["existing_sectura_quote"],
                "tree": None,
            },
        }
    runner = push or push_selected
    try:
        result = runner(kind, expanded, job)
    except Exception:
        return _failed("push_failed", path_name=kind)
    if not isinstance(result, PushResult):
        return _failed("push_failed", path_name=kind)
    quote_id = str(result.quote_id or "").strip()
    quote_number = str(result.quote_number or "").strip()
    if not result.ok:
        report = _qc_report(None, path_name=kind, label=quote_number, expected=_expected(job))
        if result.error:
            report["flags"] = [str(result.error)] + list(report["flags"])
        return {
            "status": "failed",
            "error": str(result.error or result.last_error or "push_failed"),
            "sectura_quote_number": quote_number,
            "sectura_quote_id": quote_id,
            "qc_report": report,
        }
    reader = read_tree or _live_tree
    try:
        tree = reader(quote_id) if quote_id else None
    except Exception:
        tree = None
    report = _qc_report(tree, path_name=kind, label=quote_number, expected=_expected(job))
    status = "qc_flagged" if report["flags"] else "done"
    return {
        "status": status,
        "error": "",
        "sectura_quote_number": quote_number,
        "sectura_quote_id": quote_id,
        "qc_report": report,
    }


def _expected(job: dict[str, Any]) -> dict[str, int] | None:
    raw = job.get("expected_parts")
    if not isinstance(raw, dict) or not raw:
        return None
    out: dict[str, int] = {}
    for name, qty in raw.items():
        try:
            out[str(name)] = int(qty)
        except (TypeError, ValueError):
            return None
    return out or None


def _live_tree(quote_id: str) -> Any:
    from secturafab.quote_qc import _default_reader, fetch_tree

    return fetch_tree(quote_id, reader=_default_reader)


def _failed(reason: str, *, path_name: str = "") -> dict[str, Any]:
    return {
        "status": "failed",
        "error": reason,
        "sectura_quote_number": "",
        "sectura_quote_id": "",
        "qc_report": {"path": path_name, "status": "FLAG", "flags": [reason], "summary": "", "tree": None},
    }
