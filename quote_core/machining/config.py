from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MACHINES_PATH = ROOT / "config" / "machines.yaml"
DEFAULT_MACHINING_PATH = ROOT / "config" / "machining.yaml"


@dataclass
class Envelope:
    # Lathe
    min_diameter_in: float | None = None
    max_diameter_in: float | None = None
    max_length_in: float | None = None
    max_chuck_diameter_in: float | None = None
    # Mill
    x_in: float | None = None
    y_in: float | None = None
    z_in: float | None = None
    fourth_axis_diameter_in: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "min_diameter_in": self.min_diameter_in,
            "max_diameter_in": self.max_diameter_in,
            "max_length_in": self.max_length_in,
            "max_chuck_diameter_in": self.max_chuck_diameter_in,
            "x_in": self.x_in,
            "y_in": self.y_in,
            "z_in": self.z_in,
            "fourth_axis_diameter_in": self.fourth_axis_diameter_in,
        }


@dataclass
class Machine:
    id: str
    oem: str
    model: str
    class_name: str  # cnc_lathe | manual_lathe | cnc_mill | manual_mill
    subclass: str
    count_group: str
    taper: str | None
    horsepower: float | None
    max_rpm: float | None
    live_tooling: bool
    fourth_axis: bool
    envelope: Envelope
    tooling: list[dict[str, Any]]
    notes: str
    spindle_nose: str = ""

    @property
    def kind(self) -> str:
        if "lathe" in self.class_name:
            return "lathe"
        return "mill"

    @property
    def display_name(self) -> str:
        model = (self.model or "").strip()
        if model:
            return f"{self.oem} {model}".strip()
        return f"{self.oem} {self.class_name.replace('_', ' ')}".strip()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "oem": self.oem,
            "model": self.model,
            "class": self.class_name,
            "subclass": self.subclass,
            "count_group": self.count_group,
            "taper": self.taper,
            "horsepower": self.horsepower,
            "max_rpm": self.max_rpm,
            "live_tooling": self.live_tooling,
            "fourth_axis": self.fourth_axis,
            "envelope": self.envelope.to_dict(),
            "tooling": self.tooling,
            "notes": self.notes,
            "spindle_nose": self.spindle_nose,
            "display_name": self.display_name,
            "kind": self.kind,
        }


@dataclass
class MaterialCutData:
    key: str
    label: str
    aliases: list[str]
    mill_sfm: float
    mill_sfm_min: float | None
    mill_sfm_max: float | None
    mill_source: str
    ipt_by_diameter_in: dict[float, float]
    lathe_sfm: float
    lathe_source: str
    rough_ipr: float
    finish_ipr: float
    drill_sfm: float
    drill_ipr: float
    drill_source: str


@dataclass
class MachineRoster:
    source: str
    source_status: str
    notes: list[str]
    shop_envelopes: dict[str, Envelope]
    machines: list[Machine]
    raw: dict[str, Any] = field(default_factory=dict)

    def lathes(self) -> list[Machine]:
        return [m for m in self.machines if m.kind == "lathe"]

    def mills(self) -> list[Machine]:
        return [m for m in self.machines if m.kind == "mill"]

    def cnc_lathes(self) -> list[Machine]:
        return [m for m in self.lathes() if m.class_name == "cnc_lathe"]

    def cnc_mills(self) -> list[Machine]:
        return [m for m in self.mills() if m.class_name == "cnc_mill"]

    def by_id(self, machine_id: str) -> Machine | None:
        for m in self.machines:
            if m.id == machine_id:
                return m
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "source_status": self.source_status,
            "notes": self.notes,
            "shop_envelopes": {k: v.to_dict() for k, v in self.shop_envelopes.items()},
            "counts": {
                "cnc_lathes": len(self.cnc_lathes()),
                "cnc_mills": len(self.cnc_mills()),
                "manual_lathes": sum(1 for m in self.lathes() if m.class_name == "manual_lathe"),
                "manual_mills": sum(1 for m in self.mills() if m.class_name == "manual_mill"),
                "total": len(self.machines),
            },
            "lathes": [m.to_dict() for m in self.lathes()],
            "mills": [m.to_dict() for m in self.mills()],
        }


@dataclass
class MachiningConfig:
    placeholder: bool
    notes: list[str]
    formulas: dict[str, str]
    sources: list[dict[str, Any]]
    defaults: dict[str, Any]
    setup_minutes: dict[str, Any]
    non_cutting_factor: float
    non_cutting_placeholder: bool
    materials: dict[str, MaterialCutData]
    tooling: dict[str, Any]
    coating: dict[str, Any]
    raw: dict[str, Any] = field(default_factory=dict)

    def resolve_material(self, name: str | None) -> MaterialCutData:
        if not name:
            return self.materials["carbon_steel"]
        key = str(name).strip().lower().replace(" ", "_").replace("-", "_")
        if key in self.materials:
            return self.materials[key]
        for mat in self.materials.values():
            aliases = [a.lower().replace(" ", "_").replace("-", "_") for a in mat.aliases]
            if key in aliases:
                return mat
        # Prefer alloy before carbon when both list a514-style aliases.
        for preferred in ("alloy_steel", "stainless", "aluminum", "cast_iron", "carbon_steel"):
            mat = self.materials.get(preferred)
            if not mat:
                continue
            aliases = [a.lower().replace(" ", "_").replace("-", "_") for a in mat.aliases]
            if key in aliases:
                return mat
        raise KeyError(f"Unknown machining material: {name}")

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "placeholder": self.placeholder,
            "notes": self.notes,
            "formulas": self.formulas,
            "sources": self.sources,
            "defaults": self.defaults,
            "setup_minutes": self.setup_minutes,
            "non_cutting_factor": {
                "value": self.non_cutting_factor,
                "placeholder": self.non_cutting_placeholder,
            },
            "materials": {
                k: {
                    "key": v.key,
                    "label": v.label,
                    "aliases": v.aliases,
                    "mill_sfm": v.mill_sfm,
                    "mill_sfm_range": [v.mill_sfm_min, v.mill_sfm_max],
                    "mill_source": v.mill_source,
                    "lathe_sfm": v.lathe_sfm,
                    "lathe_source": v.lathe_source,
                    "rough_ipr": v.rough_ipr,
                    "finish_ipr": v.finish_ipr,
                    "drill_sfm": v.drill_sfm,
                    "drill_ipr": v.drill_ipr,
                }
                for k, v in self.materials.items()
            },
            "tooling": self.tooling,
            "coating": self.coating,
        }


def _num(value: Any) -> float | None:
    if value in (None, "", "null"):
        return None
    return float(value)


def _envelope_from(raw: dict[str, Any] | None) -> Envelope:
    raw = raw or {}
    return Envelope(
        min_diameter_in=_num(raw.get("min_diameter_in")),
        max_diameter_in=_num(raw.get("max_diameter_in")),
        max_length_in=_num(raw.get("max_length_in")),
        max_chuck_diameter_in=_num(raw.get("max_chuck_diameter_in")),
        x_in=_num(raw.get("x_in")),
        y_in=_num(raw.get("y_in")),
        z_in=_num(raw.get("z_in")),
        fourth_axis_diameter_in=_num(raw.get("fourth_axis_diameter_in")),
    )


def _machine_from(raw: dict[str, Any]) -> Machine:
    return Machine(
        id=str(raw.get("id") or ""),
        oem=str(raw.get("oem") or ""),
        model=str(raw.get("model") or ""),
        class_name=str(raw.get("class") or ""),
        subclass=str(raw.get("subclass") or ""),
        count_group=str(raw.get("count_group") or ""),
        taper=(str(raw["taper"]) if raw.get("taper") not in (None, "") else None),
        horsepower=_num(raw.get("horsepower")),
        max_rpm=_num(raw.get("max_rpm")),
        live_tooling=bool(raw.get("live_tooling")),
        fourth_axis=bool(raw.get("fourth_axis")),
        envelope=_envelope_from(raw.get("envelope")),
        tooling=list(raw.get("tooling") or []),
        notes=str(raw.get("notes") or ""),
        spindle_nose=str(raw.get("spindle_nose") or ""),
    )


def load_machine_roster(path: Path | str | None = None) -> MachineRoster:
    machines_path = Path(path) if path else DEFAULT_MACHINES_PATH
    with machines_path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    shop_raw = raw.get("shop_envelopes") or {}
    shop = {str(k): _envelope_from(v) for k, v in shop_raw.items()}
    machines = [_machine_from(row) for row in (raw.get("lathes") or [])]
    machines.extend(_machine_from(row) for row in (raw.get("mills") or []))
    return MachineRoster(
        source=str(raw.get("source") or ""),
        source_status=str(raw.get("source_status") or ""),
        notes=list(raw.get("notes") or []),
        shop_envelopes=shop,
        machines=machines,
        raw=raw,
    )


def _material_from(key: str, raw: dict[str, Any]) -> MaterialCutData:
    mill = raw.get("mill") or {}
    lathe = raw.get("lathe") or {}
    drill = raw.get("drill") or {}
    ipt_raw = mill.get("ipt_by_diameter_in") or {}
    ipt = {float(k): float(v) for k, v in ipt_raw.items()}
    return MaterialCutData(
        key=key,
        label=str(raw.get("label") or key),
        aliases=[str(a) for a in (raw.get("aliases") or [])],
        mill_sfm=float(mill.get("sfm") or 0),
        mill_sfm_min=_num(mill.get("sfm_min")),
        mill_sfm_max=_num(mill.get("sfm_max")),
        mill_source=str(mill.get("source") or "placeholder_catalog"),
        ipt_by_diameter_in=ipt,
        lathe_sfm=float(lathe.get("sfm") or 0),
        lathe_source=str(lathe.get("source") or "placeholder_catalog"),
        rough_ipr=float(lathe.get("rough_ipr") or 0.010),
        finish_ipr=float(lathe.get("finish_ipr") or 0.005),
        drill_sfm=float(drill.get("sfm") or 0),
        drill_ipr=float(drill.get("ipr") or 0.005),
        drill_source=str(drill.get("source") or "placeholder_catalog"),
    )


def load_machining_config(path: Path | str | None = None) -> MachiningConfig:
    cfg_path = Path(path) if path else DEFAULT_MACHINING_PATH
    with cfg_path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    mats = {
        str(k): _material_from(str(k), v)
        for k, v in (raw.get("materials") or {}).items()
    }
    ncf = raw.get("non_cutting_factor") or {}
    return MachiningConfig(
        placeholder=bool(raw.get("placeholder", True)),
        notes=list(raw.get("notes") or []),
        formulas=dict(raw.get("formulas") or {}),
        sources=list(raw.get("sources") or []),
        defaults=dict(raw.get("defaults") or {}),
        setup_minutes=dict(raw.get("setup_minutes") or {}),
        non_cutting_factor=float(ncf.get("value", 1.20)),
        non_cutting_placeholder=bool(ncf.get("placeholder", True)),
        materials=mats,
        tooling=dict(raw.get("tooling") or {}),
        coating=dict(raw.get("coating") or {}),
        raw=raw,
    )
