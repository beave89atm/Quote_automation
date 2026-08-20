"""Confirm a PDF BOM takeoff against STEP assembly part counts.

STP is a check only: never overwrite or pad PDF BOM rows from the STEP.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from quote_core.weld.takeoff import _normalize_step_part_no


def _row_part_no(row: Any) -> str | None:
    if isinstance(row, dict):
        raw = row.get("part_no") or row.get("part_number")
    else:
        raw = getattr(row, "part_no", None)
    return _normalize_step_part_no(str(raw) if raw else None)


def _row_qty(row: Any) -> int:
    if isinstance(row, dict):
        raw = row.get("qty")
    else:
        raw = getattr(row, "qty", 1)
    try:
        return max(0, int(raw or 0))
    except (TypeError, ValueError):
        return 0


def pdf_bom_qty_map(rows: list[Any] | None) -> dict[str, int]:
    """Sum qty by normalized PN. Does not invent rows."""
    counts: Counter[str] = Counter()
    for row in rows or []:
        pn = _row_part_no(row)
        if not pn:
            continue
        qty = _row_qty(row)
        if qty <= 0:
            continue
        counts[pn] += qty
    return dict(counts)


def _counts_from_stp_payload(stp_counts: dict[str, Any] | None) -> dict[str, int]:
    if not stp_counts:
        return {}
    raw = stp_counts.get("counts") if "counts" in stp_counts else stp_counts
    if not isinstance(raw, dict):
        return {}
    out: dict[str, int] = {}
    for key, val in raw.items():
        pn = _normalize_step_part_no(str(key))
        if not pn:
            continue
        try:
            qty = int(val or 0)
        except (TypeError, ValueError):
            continue
        if qty <= 0:
            continue
        out[pn] = out.get(pn, 0) + qty
    return out


def skipped_stp_bom_confirm(reason: str) -> dict[str, Any]:
    return {
        "skipped": True,
        "reason": reason,
        "matched": [],
        "pdf_only": [],
        "stp_only": [],
        "qty_mismatches": [],
        "pdf_piece_count": 0,
        "stp_piece_count": 0,
        "pdf_unique_pn_count": 0,
        "stp_unique_pn_count": 0,
        "piece_count_agree": False,
        "unique_pn_count_agree": False,
        "mismatch": False,
    }


def confirm_flag_text(confirm: dict[str, Any]) -> str | None:
    if not confirm or confirm.get("skipped"):
        return None
    pdf_n = int(confirm.get("pdf_unique_pn_count") or 0)
    stp_n = int(confirm.get("stp_unique_pn_count") or 0)
    pdf_pcs = int(confirm.get("pdf_piece_count") or 0)
    stp_pcs = int(confirm.get("stp_piece_count") or 0)
    if confirm.get("mismatch"):
        bits: list[str] = []
        pdf_only = [str(r.get("part_no")) for r in confirm.get("pdf_only") or []]
        stp_only = [str(r.get("part_no")) for r in confirm.get("stp_only") or []]
        qty_bad = [
            f"{r.get('part_no')} PDF {r.get('pdf_qty')} vs STP {r.get('stp_qty')}"
            for r in confirm.get("qty_mismatches") or []
        ]
        if pdf_only:
            bits.append("PDF-only " + ", ".join(pdf_only[:8]))
        if stp_only:
            bits.append("STP-only " + ", ".join(stp_only[:8]))
        if qty_bad:
            bits.append("qty " + "; ".join(qty_bad[:6]))
        extra = f" ({'; '.join(bits)})" if bits else ""
        return (
            f"STP/PDF BOM mismatch — review: {pdf_n} PDF PNs / {stp_n} STP PNs, "
            f"{pdf_pcs} vs {stp_pcs} pieces{extra}"
        )
    return (
        f"STP confirms PDF BOM ({pdf_n} PNs, {pdf_pcs} pieces)"
    )


def confirm_pdf_bom_against_stp(
    pdf_rows: list[Any] | None,
    stp_counts: dict[str, Any] | None,
    *,
    assembly_pn: str | None = None,
    stp_notes: list[str] | None = None,
) -> dict[str, Any]:
    """
    Compare PDF BOM item/qty/part_no to STEP instance counts.

    Returns matched / PDF-only / STP-only PNs and whether piece and unique
    PN counts agree. Does not mutate ``pdf_rows``.
    """
    pdf_map = pdf_bom_qty_map(pdf_rows)
    stp_map = _counts_from_stp_payload(stp_counts)
    if assembly_pn:
        asm = _normalize_step_part_no(assembly_pn)
        if asm:
            stp_map.pop(asm, None)

    all_pns = sorted(set(pdf_map) | set(stp_map))
    matched: list[dict[str, Any]] = []
    pdf_only: list[dict[str, Any]] = []
    stp_only: list[dict[str, Any]] = []
    qty_mismatches: list[dict[str, Any]] = []

    for pn in all_pns:
        pdf_qty = int(pdf_map.get(pn) or 0)
        stp_qty = int(stp_map.get(pn) or 0)
        if pdf_qty and stp_qty:
            row = {"part_no": pn, "pdf_qty": pdf_qty, "stp_qty": stp_qty}
            matched.append(row)
            if pdf_qty != stp_qty:
                qty_mismatches.append(row)
        elif pdf_qty:
            pdf_only.append({"part_no": pn, "qty": pdf_qty})
        elif stp_qty:
            stp_only.append({"part_no": pn, "qty": stp_qty})

    pdf_piece = sum(pdf_map.values())
    stp_piece = sum(stp_map.values())
    piece_agree = pdf_piece == stp_piece
    unique_agree = len(pdf_map) == len(stp_map)
    mismatch = bool(pdf_only or stp_only or qty_mismatches or not piece_agree or not unique_agree)

    notes = list(stp_notes or [])
    if isinstance(stp_counts, dict):
        for n in stp_counts.get("notes") or []:
            if n and n not in notes:
                notes.append(n)
    if not pdf_map and stp_map:
        notes.append(
            f"PDF BOM empty — STP listed {len(stp_map)} PN(s) (not applied to the drawing BOM)"
        )
    elif pdf_map and not stp_map:
        notes.append("STEP assembly listed no child part numbers")

    return {
        "skipped": False,
        "reason": None,
        "matched": matched,
        "pdf_only": pdf_only,
        "stp_only": stp_only,
        "qty_mismatches": qty_mismatches,
        "pdf_piece_count": pdf_piece,
        "stp_piece_count": stp_piece,
        "pdf_unique_pn_count": len(pdf_map),
        "stp_unique_pn_count": len(stp_map),
        "piece_count_agree": piece_agree,
        "unique_pn_count_agree": unique_agree,
        "mismatch": mismatch,
        "notes": notes,
        "stp_method": (stp_counts or {}).get("method") if isinstance(stp_counts, dict) else None,
    }
