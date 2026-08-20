"""Load Kannon shop capabilities (in-house + outsourced)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CAPABILITIES_PATH = ROOT / "config" / "shop_capabilities.yaml"


def load_shop_capabilities(path: Path | str | None = None) -> dict[str, Any]:
    cap_path = Path(path) if path else DEFAULT_CAPABILITIES_PATH
    with cap_path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    if not isinstance(raw, dict):
        return {}
    return raw
