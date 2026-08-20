"""Machine-class suggestion and envelope flags. Does not invent times."""

from __future__ import annotations

from typing import Any

from .config import Envelope, Machine, MachineRoster


def _flag(code: str, message: str, *, blocking: bool = True) -> dict[str, Any]:
    return {"code": code, "message": message, "blocking": blocking}


def _pick(machine_val: float | None, shop_val: float | None) -> float | None:
    return machine_val if machine_val is not None else shop_val


def envelope_with_shop(
    machine_env: Envelope,
    shop: Envelope,
    *,
    inherit_fourth_axis: bool = False,
) -> Envelope:
    """Fill empty per-machine travels from shop gates. Does not invent numbers."""
    return Envelope(
        min_diameter_in=_pick(machine_env.min_diameter_in, shop.min_diameter_in),
        max_diameter_in=_pick(machine_env.max_diameter_in, shop.max_diameter_in),
        max_length_in=_pick(machine_env.max_length_in, shop.max_length_in),
        max_chuck_diameter_in=_pick(
            machine_env.max_chuck_diameter_in, shop.max_chuck_diameter_in
        ),
        x_in=_pick(machine_env.x_in, shop.x_in),
        y_in=_pick(machine_env.y_in, shop.y_in),
        z_in=_pick(machine_env.z_in, shop.z_in),
        fourth_axis_diameter_in=(
            _pick(machine_env.fourth_axis_diameter_in, shop.fourth_axis_diameter_in)
            if inherit_fourth_axis
            else machine_env.fourth_axis_diameter_in
        ),
    )


def lathe_envelope_flags(
    *,
    diameter_in: float,
    length_in: float,
    envelope: Envelope,
) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    min_d = envelope.min_diameter_in
    max_d = envelope.max_diameter_in
    chuck = envelope.max_chuck_diameter_in
    max_l = envelope.max_length_in

    if min_d is not None and diameter_in < min_d:
        flags.append(
            _flag(
                "LATHE_BELOW_MIN_DIAMETER",
                f"Diameter {diameter_in:.3f}\" is below typical chucker min {min_d:.3f}\" "
                "(July list: 3/8\"). Review collet / bar work.",
                blocking=False,
            )
        )
    if chuck is not None and diameter_in > chuck:
        flags.append(
            _flag(
                "LATHE_OVER_CHUCK",
                f"Diameter {diameter_in:.3f}\" exceeds max chuck {chuck:.3f}\". "
                "Cannot hold on Kannon lathes in the July list.",
            )
        )
    elif max_d is not None and diameter_in > max_d:
        flags.append(
            _flag(
                "LATHE_OVER_TYPICAL_DIAMETER",
                f"Diameter {diameter_in:.3f}\" is over the typical turning envelope "
                f"({max_d:.3f}\"). Chucks go to {chuck}\" — review, do not silent-quote.",
            )
        )
    if max_l is not None and length_in > max_l:
        flags.append(
            _flag(
                "LATHE_OVER_LENGTH",
                f"Length {length_in:.3f}\" exceeds typical chucker length {max_l:.3f}\" "
                "(July list: 12–14\"). Do not silent-quote.",
            )
        )
    return flags


def mill_envelope_flags(
    *,
    length_in: float,
    width_in: float,
    height_in: float,
    envelope: Envelope,
    needs_4th_axis: bool = False,
    fourth_axis_diameter_in: float | None = None,
) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    dims = sorted(
        [float(length_in), float(width_in), float(height_in)],
        reverse=True,
    )
    table_long = envelope.x_in
    table_short = envelope.y_in
    z_travel = envelope.z_in

    if table_long is not None and table_short is not None:
        if dims[0] > table_long or dims[1] > table_short:
            flags.append(
                _flag(
                    "MILL_OVER_TABLE",
                    f"Part envelope {dims[0]:.2f}\" × {dims[1]:.2f}\" does not fit the "
                    f"shop cube {table_long:.0f}\" × {table_short:.0f}\" (July list). "
                    "Do not silent-quote.",
                )
            )
    if z_travel is not None and dims[2] > z_travel:
        flags.append(
            _flag(
                "MILL_OVER_Z",
                f"Shortest part dim {dims[2]:.2f}\" exceeds assumed Z travel {z_travel:.0f}\". "
                "Review fixture height / confirm machine travel.",
            )
        )
    if needs_4th_axis:
        limit = envelope.fourth_axis_diameter_in
        dia = fourth_axis_diameter_in
        if dia is None:
            dia = min(width_in, height_in)
        if limit is None:
            flags.append(
                _flag(
                    "MILL_4TH_AXIS_NOT_ON_MACHINE",
                    "4th-axis work requested but this machine class has no 4th-axis envelope.",
                )
            )
        elif dia > limit:
            flags.append(
                _flag(
                    "MILL_4TH_AXIS_OVER_DIAMETER",
                    f"4th-axis diameter {dia:.2f}\" exceeds shop limit {limit:.0f}\" "
                    "(July list: full 4th-axis up to 20\").",
                )
            )
    return flags


def _score_lathe(machine: Machine, needs_live_tooling: bool, flags: list[dict[str, Any]]) -> int:
    score = 0
    if machine.class_name == "cnc_lathe":
        score += 20
    if needs_live_tooling and machine.live_tooling:
        score += 30
    if needs_live_tooling and not machine.live_tooling:
        score -= 40
    if any(f["blocking"] for f in flags):
        score -= 100
    return score


def _score_mill(
    machine: Machine,
    *,
    needs_4th_axis: bool,
    length_in: float,
    width_in: float,
    height_in: float,
    flags: list[dict[str, Any]],
) -> int:
    score = 0
    if machine.class_name == "cnc_mill":
        score += 20
    if machine.subclass == "horizontal":
        score += 4
    if machine.taper and "50" in str(machine.taper):
        score += 6
    if machine.subclass == "vertical_high_speed":
        max_dim = max(length_in, width_in, height_in)
        if max_dim <= 12:
            score += 12
        else:
            score -= 8
    if needs_4th_axis:
        if machine.fourth_axis or machine.subclass == "horizontal":
            score += 20
        else:
            score -= 30
    if any(f["blocking"] for f in flags):
        score -= 100
    return score


def suggest_lathe(
    roster: MachineRoster,
    *,
    diameter_in: float,
    length_in: float,
    needs_live_tooling: bool = False,
) -> dict[str, Any]:
    shop_env = roster.shop_envelopes.get("cnc_lathe") or Envelope()
    shop_flags = lathe_envelope_flags(
        diameter_in=diameter_in, length_in=length_in, envelope=shop_env
    )
    ranked: list[dict[str, Any]] = []
    for machine in roster.lathes():
        shop_for_machine = roster.shop_envelopes.get(machine.class_name) or shop_env
        env_flags = lathe_envelope_flags(
            diameter_in=diameter_in,
            length_in=length_in,
            envelope=envelope_with_shop(machine.envelope, shop_for_machine),
        )
        if needs_live_tooling and not machine.live_tooling:
            env_flags.append(
                _flag(
                    "LATHE_NO_LIVE_TOOLING",
                    f"{machine.display_name} has no live tooling.",
                    blocking=machine.class_name == "cnc_lathe",
                )
            )
        score = _score_lathe(machine, needs_live_tooling, env_flags)
        ranked.append(
            {
                "machine": machine.to_dict(),
                "score": score,
                "flags": env_flags,
                "fits": not any(f["blocking"] for f in env_flags),
            }
        )
    ranked.sort(key=lambda r: (-r["score"], r["machine"]["id"]))
    capable = [r for r in ranked if r["fits"] and r["machine"]["class"] == "cnc_lathe"]
    suggested_class = "cnc_lathe_live_tooling" if needs_live_tooling else "cnc_lathe"
    if needs_live_tooling and not any(r["machine"]["live_tooling"] and r["fits"] for r in ranked):
        shop_flags.append(
            _flag(
                "LATHE_LIVE_TOOLING_REQUIRED",
                "Live tooling requested; only the Puma GT3100LM is listed with live tooling. "
                "If that machine is out of envelope, do not silent-quote.",
            )
        )
    pick = next((r for r in capable if (not needs_live_tooling) or r["machine"]["live_tooling"]), None)
    if pick is None:
        pick = next((r for r in ranked if r["machine"]["class"] == "cnc_lathe"), None)
    return {
        "suggested_class": suggested_class,
        "suggested_machine": None if pick is None else pick["machine"],
        "candidates": ranked,
        "shop_flags": shop_flags,
        "outside_envelope": any(f["blocking"] for f in shop_flags),
    }


def suggest_mill(
    roster: MachineRoster,
    *,
    length_in: float,
    width_in: float,
    height_in: float,
    needs_4th_axis: bool = False,
    fourth_axis_diameter_in: float | None = None,
) -> dict[str, Any]:
    shop_env = roster.shop_envelopes.get("cnc_mill") or Envelope()
    shop_flags = mill_envelope_flags(
        length_in=length_in,
        width_in=width_in,
        height_in=height_in,
        envelope=shop_env,
        needs_4th_axis=needs_4th_axis,
        fourth_axis_diameter_in=fourth_axis_diameter_in,
    )
    ranked: list[dict[str, Any]] = []
    for machine in roster.mills():
        shop_for_machine = roster.shop_envelopes.get(machine.class_name) or shop_env
        env_flags = mill_envelope_flags(
            length_in=length_in,
            width_in=width_in,
            height_in=height_in,
            envelope=envelope_with_shop(
                machine.envelope,
                shop_for_machine,
                inherit_fourth_axis=machine.fourth_axis or machine.subclass == "horizontal",
            ),
            needs_4th_axis=needs_4th_axis,
            fourth_axis_diameter_in=fourth_axis_diameter_in,
        )
        score = _score_mill(
            machine,
            needs_4th_axis=needs_4th_axis,
            length_in=length_in,
            width_in=width_in,
            height_in=height_in,
            flags=env_flags,
        )
        ranked.append(
            {
                "machine": machine.to_dict(),
                "score": score,
                "flags": env_flags,
                "fits": not any(f["blocking"] for f in env_flags),
            }
        )
    ranked.sort(key=lambda r: (-r["score"], r["machine"]["id"]))
    capable = [r for r in ranked if r["fits"] and r["machine"]["class"] == "cnc_mill"]
    pick = capable[0] if capable else next(
        (r for r in ranked if r["machine"]["class"] == "cnc_mill"), None
    )
    suggested_class = "cnc_mill"
    if pick and pick["machine"]["subclass"] == "horizontal":
        suggested_class = "cnc_mill_horizontal"
    elif pick and pick["machine"]["subclass"] == "vertical_high_speed":
        suggested_class = "robodrill"
    elif needs_4th_axis:
        suggested_class = "cnc_mill_4axis"
    else:
        suggested_class = "cnc_mill_3axis"
    return {
        "suggested_class": suggested_class,
        "suggested_machine": None if pick is None else pick["machine"],
        "candidates": ranked,
        "shop_flags": shop_flags,
        "outside_envelope": any(f["blocking"] for f in shop_flags),
    }
