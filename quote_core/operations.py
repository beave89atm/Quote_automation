"""Propose fab operations + setup/run times from drawings and capabilities.

Conservative: flag unknowns. Mill/lathe is a parallel project — never invent
those times or emit mill/lathe ops. Outsourced tube laser and powder coating
always appear on the proposal.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .capabilities import load_shop_capabilities

_TUBE_RE = (
    r"\bTUBE\b|\bPIPE\b|\bHSS\b|\bDOM\b|\bROUND\s+TUBE\b|\bRECT(?:ANGULAR)?\s+TUBE\b"
    r"|\bSQUARE\s+TUBE\b"
)
_POWDER_RE = r"POWDER\s*COAT|POWDER\s*COATING|\bP\s*/\s*C\b|\bPOWDER\b"
_PAINT_RE = r"\bPAINT(?:ED|ING)?\b|\bWET\s+PAINT\b|\bE-?COAT\b"
_LASER_RE = r"\bLASER\b|\bNEST\b|\bPROFILE\b|\bFLAT\s+PATTERN\b"
_TUBE_LASER_RE = r"TUBE\s*LASER|LASER\s*TUBE|TUBE\s*CUT(?:TING)?"
_BEND_RE = r"\bBEND(?:S|ING)?\b|\bFORM(?:ED|ING)?\b|\bPRESS\s+BRAKE\b|\bBRAKE\b"
_SAW_RE = r"\bSAW\b|\bCUT\s+TO\s+LENGTH\b|\bCUTOFF\b|\bCUT[- ]OFF\b"
_ROLL_RE = r"\bROLL(?:ED|ING)?\b|\bPLATE\s+ROLL\b"
_TUBE_BEND_RE = r"TUBE\s*BEND|BEND(?:S|ING)?\s+(?:TUBE|PIPE)|PIPE\s*BEND"
_MILL_RE = r"\bMILL(?:ING)?\b|\bCNC\s+MILL\b|\bMACHIN(?:E|ING)\b|\bCOUNTERBORE\b|\bSPOTFACE\b"
_LATHE_RE = r"\bLATHE\b|\bTURN(?:ED|ING)?\b|\bCNC\s+LATHE\b|\bOD\s+TURN"
_WELD_RE = r"\bWELD(?:ING|MENT)?\b|\bFILLET\b|\bMIG\b|\bTIG\b|\bAWS\s*D1"


def _norm(text: str) -> str:
    return " ".join((text or "").upper().replace("\x00", " ").split())


def _has(blob: str, pattern: str) -> bool:
    import re

    return bool(re.search(pattern, blob, flags=re.IGNORECASE))


def _count_bends(blob: str) -> int | None:
    import re

    m = re.search(r"\b(\d{1,2})\s+BENDS?\b", blob, flags=re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None


@dataclass
class ProposedOperation:
    code: str
    name: str
    location: str  # in_house | outsourced
    detected: bool
    setup_minutes: float | None
    run_minutes: float | None
    time_status: str  # computed | placeholder | parked | confirm
    needs_review: bool
    confidence: str  # high | medium | low | n/a
    evidence: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OperationsProposal:
    operations: list[ProposedOperation] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    source: str = ""
    as_of: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "operations": [o.to_dict() for o in self.operations],
            "flags": list(self.flags),
            "source": self.source,
            "as_of": self.as_of,
        }


def _placeholders(caps: dict[str, Any]) -> dict[str, Any]:
    raw = caps.get("placeholders") or {}
    return raw if isinstance(raw, dict) else {}


def propose_operations(
    *,
    title: str = "",
    filenames: list[str] | None = None,
    pdf_notes: list[str] | None = None,
    dxf_text: str = "",
    has_pdf: bool = False,
    has_dxf: bool = False,
    has_stp: bool = False,
    weld_items: list[dict[str, Any]] | None = None,
    times: dict[str, Any] | None = None,
    stp_summary: dict[str, Any] | None = None,
    capabilities: dict[str, Any] | None = None,
    capabilities_path: Path | str | None = None,
) -> OperationsProposal:
    """
    Propose operations from drawings + the capabilities list.

    Tube laser and powder coating are always listed (outsourced). Mill/lathe
    is a parallel project — never propose those ops or invent their times.
    """
    caps = capabilities if capabilities is not None else load_shop_capabilities(capabilities_path)
    ph = _placeholders(caps)
    names = [str(n) for n in (filenames or []) if n]
    notes = [str(n) for n in (pdf_notes or []) if n]
    items = list(weld_items or [])
    times = times or {}
    stp = stp_summary or {}

    blob = _norm(
        " ".join(
            [
                title,
                " ".join(names),
                " ".join(notes),
                dxf_text,
                " ".join(str(i.get("joint_notes") or "") for i in items),
                " ".join(str(s.get("name") or "") for s in (stp.get("top_solids") or [])),
            ]
        )
    )

    weld_inches = float(times.get("total_inches") or 0) or sum(
        float(i.get("inches") or 0) for i in items
    )
    weld_minutes = float(times.get("weld_minutes") or 0)
    fitup_minutes = float(
        times.get("fitup_with_fixture_minutes")
        if times.get("fitup_with_fixture_minutes") is not None
        else 0
    )
    has_weld = weld_inches > 0 or weld_minutes > 0 or _has(blob, _WELD_RE)

    solids = list(stp.get("top_solids") or [])
    plate_like = any(
        str(s.get("kind") or "") in {"plate", "plate_member", "cover"} for s in solids
    )
    linear_like = any(
        str(s.get("kind") or "") in {"angle", "channel"}
        or _has(_norm(str(s.get("name") or "")), _TUBE_RE)
        for s in solids
    )

    ops: list[ProposedOperation] = []
    flags: list[str] = []

    # --- Laser (in-house Amada) ---
    laser_hits: list[str] = []
    if has_dxf:
        laser_hits.append("DXF attached (2D nest / profile candidate)")
    if _has(blob, _LASER_RE) and not _has(blob, _TUBE_LASER_RE):
        laser_hits.append("drawing mentions laser / nest / profile / flat pattern")
    if plate_like:
        laser_hits.append("STEP has plate-like solids")
    if has_pdf and not has_weld and not has_stp:
        laser_hits.append("PDF-only / no weld symbols — typical laser plate path")
    laser_detected = bool(laser_hits)
    ops.append(
        ProposedOperation(
            code="laser",
            name="Laser / Profile (Amada)",
            location="in_house",
            detected=laser_detected,
            setup_minutes=float(ph["laser_setup_minutes"])
            if laser_detected and ph.get("laser_setup_minutes") is not None
            else None,
            run_minutes=None,
            time_status="placeholder" if laser_detected else "n/a",
            needs_review=True,
            confidence="medium" if laser_detected else "n/a",
            evidence=laser_hits,
            notes=[
                "Cut/run time comes from SecturaFAB Profile / nest — not invented here",
                "Confirm thickness vs 18ga–3/4\" CS / 18ga–1/2\" SS-Al / 5×10 sheet",
            ]
            if laser_detected
            else ["Not indicated on these files"],
        )
    )

    # --- Bend ---
    bend_hits: list[str] = []
    if _has(blob, _BEND_RE) and not _has(blob, _TUBE_BEND_RE):
        bend_hits.append("drawing mentions bend / form / brake")
    bend_count = _count_bends(blob)
    if bend_count:
        bend_hits.append(f"bend count callout: {bend_count}")
    bend_run = None
    if bend_count and ph.get("bend_seconds_per_bend"):
        bend_run = round(bend_count * float(ph["bend_seconds_per_bend"]) / 60.0, 2)
    ops.append(
        ProposedOperation(
            code="bend",
            name="Brake / Bend",
            location="in_house",
            detected=bool(bend_hits),
            setup_minutes=float(ph["bend_setup_minutes"])
            if bend_hits and ph.get("bend_setup_minutes") is not None
            else None,
            run_minutes=bend_run,
            time_status="placeholder" if bend_hits else "n/a",
            needs_review=True,
            confidence="medium" if bend_count else ("low" if bend_hits else "n/a"),
            evidence=bend_hits,
            notes=(
                [
                    "Lesson 01: ~30 min setup; ~90 sec/bend on long parts; 2nd operator if >4 ft",
                    "Bend count from dotted flat-pattern lines still needs Kyle when not printed",
                ]
                if bend_hits
                else ["Not indicated on these files"]
            ),
        )
    )

    # --- Saw ---
    saw_hits: list[str] = []
    if _has(blob, _SAW_RE):
        saw_hits.append("drawing mentions saw / cut-to-length")
    ops.append(
        ProposedOperation(
            code="saw",
            name="Saw / cutoff",
            location="in_house",
            detected=bool(saw_hits),
            setup_minutes=float(ph["saw_setup_minutes"])
            if saw_hits and ph.get("saw_setup_minutes") is not None
            else None,
            run_minutes=None,
            time_status="placeholder" if saw_hits else "n/a",
            needs_review=True,
            confidence="low" if saw_hits else "n/a",
            evidence=saw_hits,
            notes=["Run time unknown — confirm Hyd-Mech vs shear"]
            if saw_hits
            else ["Not indicated on these files"],
        )
    )

    # --- Weld + fit-up (existing engine) ---
    weld_setup = float(ph["weld_setup_minutes"]) if ph.get("weld_setup_minutes") is not None else 15.0
    ops.append(
        ProposedOperation(
            code="weld",
            name="Manual weld",
            location="in_house",
            detected=has_weld and weld_minutes > 0,
            setup_minutes=weld_setup if (has_weld and weld_minutes > 0) else None,
            run_minutes=round(weld_minutes, 2) if weld_minutes > 0 else None,
            time_status="computed" if weld_minutes > 0 else ("n/a" if not has_weld else "confirm"),
            needs_review=has_weld and weld_minutes <= 0,
            confidence="high" if weld_minutes > 0 else ("low" if has_weld else "n/a"),
            evidence=(
                [f"{weld_inches:.2f} weld inches from takeoff"]
                if weld_inches > 0
                else (["weld keyword on drawing"] if has_weld else [])
            ),
            notes=(
                ["From shop IPM table + takeoff inches"]
                if weld_minutes > 0
                else (
                    ["Weld mentioned but inches/time are 0 — confirm symbols"]
                    if has_weld
                    else ["No weld takeoff"]
                )
            ),
        )
    )
    ops.append(
        ProposedOperation(
            code="fitup",
            name="Fit-up",
            location="in_house",
            detected=fitup_minutes > 0,
            setup_minutes=None,
            run_minutes=round(fitup_minutes, 2) if fitup_minutes > 0 else None,
            time_status="computed" if fitup_minutes > 0 else "n/a",
            needs_review=False,
            confidence="high" if fitup_minutes > 0 else "n/a",
            evidence=[f"{fitup_minutes:.1f} min with fixture"] if fitup_minutes > 0 else [],
            notes=["Per-piece weight-band minutes"] if fitup_minutes > 0 else ["No fit-up"],
        )
    )

    # --- Tube bend / roll (in-house, times unknown unless hinted) ---
    tb_hits = []
    if _has(blob, _TUBE_BEND_RE):
        tb_hits.append("tube/pipe bend mention")
    ops.append(
        ProposedOperation(
            code="tube_bend",
            name="Tube bend (manual)",
            location="in_house",
            detected=bool(tb_hits),
            setup_minutes=float(ph["tube_bend_setup_minutes"])
            if tb_hits and ph.get("tube_bend_setup_minutes") is not None
            else None,
            run_minutes=None,
            time_status="placeholder" if tb_hits else "n/a",
            needs_review=True,
            confidence="low" if tb_hits else "n/a",
            evidence=tb_hits,
            notes=["Confirm square/round/rect and bend count"]
            if tb_hits
            else ["Not indicated on these files"],
        )
    )
    roll_hits = []
    if _has(blob, _ROLL_RE):
        roll_hits.append("roll mention")
    ops.append(
        ProposedOperation(
            code="plate_roll",
            name="Plate / sheet roll",
            location="in_house",
            detected=bool(roll_hits),
            setup_minutes=float(ph["roll_setup_minutes"])
            if roll_hits and ph.get("roll_setup_minutes") is not None
            else None,
            run_minutes=None,
            time_status="placeholder" if roll_hits else "n/a",
            needs_review=True,
            confidence="low" if roll_hits else "n/a",
            evidence=roll_hits,
            notes=["Max 48\" wide × 3/16\" thick, min 4\" dia — confirm vs drawing"]
            if roll_hits
            else ["Not indicated on these files"],
        )
    )

    # Machining is a parallel project — do not propose mill/lathe ops or times.
    if _has(blob, _MILL_RE) or _has(blob, _LATHE_RE):
        flags.append(
            "Machining hinted on drawing — mill/lathe is a parallel project "
            "(PARKED). This app does not estimate those times; Kyle adds ops "
            "in SecturaFAB if needed."
        )

    # --- Outsourced: always listed ---
    tl_hits: list[str] = []
    if _has(blob, _TUBE_LASER_RE):
        tl_hits.append("tube laser / tube cutting mention")
    elif _has(blob, _TUBE_RE) and (_has(blob, _LASER_RE) or has_dxf or linear_like):
        tl_hits.append("tube/pipe + cut/laser hint — confirm if outsourced tube laser")
    ops.append(
        ProposedOperation(
            code="tube_laser",
            name="Tube laser (outsourced)",
            location="outsourced",
            detected=bool(tl_hits),
            setup_minutes=float(ph["tube_laser_setup_minutes"])
            if tl_hits and ph.get("tube_laser_setup_minutes") is not None
            else None,
            run_minutes=None,
            time_status="confirm",
            needs_review=True,
            confidence="medium" if _has(blob, _TUBE_LASER_RE) else ("low" if tl_hits else "n/a"),
            evidence=tl_hits or ["Always listed — outsourced capability"],
            notes=[
                "Vendor time is a placeholder — Kyle confirms before quoting",
                "Not cut on in-house Amada sheet lasers",
            ],
        )
    )
    pw_hits: list[str] = []
    if _has(blob, _POWDER_RE):
        pw_hits.append("powder coat mention")
    elif _has(blob, _PAINT_RE):
        pw_hits.append("paint / finish mention — confirm powder vs wet paint")
    ops.append(
        ProposedOperation(
            code="powder",
            name="Powder coating (outsourced)",
            location="outsourced",
            detected=bool(pw_hits),
            setup_minutes=float(ph["powder_setup_minutes"])
            if pw_hits and ph.get("powder_setup_minutes") is not None
            else None,
            run_minutes=None,
            time_status="confirm",
            needs_review=True,
            confidence="medium" if _has(blob, _POWDER_RE) else ("low" if pw_hits else "n/a"),
            evidence=pw_hits or ["Always listed — outsourced capability"],
            notes=[
                "Vendor time is a placeholder — Kyle confirms color/spec/price",
            ],
        )
    )

    if not any(o.detected for o in ops if o.location == "in_house"):
        flags.append(
            "No in-house cut/bend/weld ops confidently detected — review drawings in SecturaFAB"
        )
    if not (has_pdf or has_dxf or has_stp):
        flags.append("No drawing files on job — operations are placeholders only")

    return OperationsProposal(
        operations=ops,
        flags=flags,
        source=str(caps.get("source") or ""),
        as_of=str(caps.get("as_of") or ""),
    )
