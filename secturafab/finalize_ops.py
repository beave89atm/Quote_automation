"""Finalize Profile / Weld / BOM qty after CAD settle, with verify retries."""

from __future__ import annotations

import time
from typing import Any

from .client import SecturaFabClient
from .imperial_ops import ensure_imperial_item_units
from .profile_ops import (
    count_profile_items,
    ensure_laser_profile_ops,
    laser_plates_missing_profile,
    wait_for_quote_settle,
)
from .qty_ops import apply_bom_quantities, bom_qty_mismatches
from .quote_update import rollup_assembly_costs
from .weld_ops import assembly_has_weld, ensure_weld_ops, resolve_weld_times


def _finish_with_imperial_and_rollup(
    client: SecturaFabClient,
    quote_id: str,
    *,
    part_key: str | None,
    bom_rows: list[dict[str, Any]] | None,
    reapply_qty: bool = False,
) -> list[str]:
    """Imperial cleanup last so delayed CAD cannot leave mm Descriptions."""
    notes: list[str] = []
    notes.extend(ensure_imperial_item_units(client, quote_id))
    if reapply_qty:
        notes.extend(
            apply_bom_quantities(
                client, quote_id, bom_rows=bom_rows, part_key=part_key
            )
        )
    notes.extend(rollup_assembly_costs(client, quote_id, part_key=part_key))
    if reapply_qty:
        # Rollup should not touch qty; verify once more and re-apply if needed.
        qty_bad = bom_qty_mismatches(
            client.get_json(f"v1/quote/{quote_id}"), bom_rows, part_key=part_key
        )
        if qty_bad:
            notes.extend(
                apply_bom_quantities(
                    client, quote_id, bom_rows=bom_rows, part_key=part_key
                )
            )
    return notes


def finalize_quote_ops(
    client: SecturaFabClient,
    quote_id: str,
    *,
    material: str,
    thickness: str,
    times: dict[str, Any] | None,
    part_key: str | None,
    bom_rows: list[dict[str, Any]] | None,
    attempts: int = 3,
) -> list[str]:
    """
    Attach/verify Profile + Weld + BOM qty until stable, then roll up assembly costs.

    Late ``UpdateItem_Part`` recalcs can wipe ops ~30–60s after HTTP 200. We wait
    after each attach before declaring success, and re-apply without UpdateItem.
    Always runs imperial cleanup on every exit so Descriptions stay inch-labeled.
    """
    notes: list[str] = []
    want_weld = resolve_weld_times(times) is not None

    for attempt in range(1, max(1, attempts) + 1):
        notes.extend(
            wait_for_quote_settle(
                client,
                quote_id,
                timeout_s=120.0 if attempt == 1 else 60.0,
                stable_s=15.0 if attempt == 1 else 10.0,
                # After first attach, delay before re-check so late CAD wipe is visible.
                min_wait_s=45.0 if attempt > 1 else 0.0,
            )
        )
        detail = client.get_json(f"v1/quote/{quote_id}")
        missing_profiles = laser_plates_missing_profile(detail)
        profiles = count_profile_items(detail)
        has_weld = assembly_has_weld(detail, part_key=part_key)
        qty_bad = bom_qty_mismatches(detail, bom_rows, part_key=part_key)

        # Any laser plate without Profile counts — not only profiles == 0.
        need_profile = bool(missing_profiles)
        need_weld = want_weld and not has_weld
        need_qty = bool(qty_bad)

        if not need_profile and not need_weld and not need_qty:
            notes.append(
                f"Verified Profile/Weld/BOM qty stable (attempt {attempt}/{attempts})"
            )
            # Still wait once more — Profile can vanish about a minute after attach.
            if attempt == 1:
                notes.append("Post-verify delay 45s to catch delayed CAD wipe…")
                time.sleep(45)
                detail = client.get_json(f"v1/quote/{quote_id}")
                missing_profiles = laser_plates_missing_profile(detail)
                profiles = count_profile_items(detail)
                has_weld = assembly_has_weld(detail, part_key=part_key)
                qty_bad = bom_qty_mismatches(detail, bom_rows, part_key=part_key)
                if missing_profiles or (want_weld and not has_weld) or qty_bad:
                    notes.append(
                        "Delayed wipe detected after verify — re-attaching"
                    )
                    # fall through to re-attach on next loop iteration logic below
                    need_profile = bool(missing_profiles)
                    need_weld = want_weld and not has_weld
                    need_qty = bool(qty_bad)
                else:
                    notes.extend(
                        _finish_with_imperial_and_rollup(
                            client,
                            quote_id,
                            part_key=part_key,
                            bom_rows=bom_rows,
                            reapply_qty=False,
                        )
                    )
                    return notes
            else:
                notes.extend(
                    _finish_with_imperial_and_rollup(
                        client,
                        quote_id,
                        part_key=part_key,
                        bom_rows=bom_rows,
                        reapply_qty=False,
                    )
                )
                return notes

        notes.append(
            f"Finalize attempt {attempt}/{attempts}: "
            f"profile={'OK' if not need_profile else f'MISSING×{len(missing_profiles)}'} "
            f"weld={'OK' if not need_weld else 'MISSING'} "
            f"bom_qty={'OK' if not need_qty else 'MISSING ' + ','.join(qty_bad)}"
        )

        # Qty first; Profile/Weld after — full quote POST for qty can race CAD.
        if need_qty:
            notes.extend(
                apply_bom_quantities(
                    client, quote_id, bom_rows=bom_rows, part_key=part_key
                )
            )
        if need_profile or need_qty:
            notes.extend(
                ensure_laser_profile_ops(
                    client, quote_id, material=material, thickness=thickness
                )
            )
        if need_weld or need_qty:
            notes.extend(
                ensure_weld_ops(
                    client,
                    quote_id,
                    times=times,
                    part_key=part_key,
                    force=True,
                )
            )

    # Final snapshot — imperial then BOM qty so Profile/Weld quote POSTs cannot
    # leave every child at Qty=1 or mm Descriptions.
    notes.extend(
        _finish_with_imperial_and_rollup(
            client,
            quote_id,
            part_key=part_key,
            bom_rows=bom_rows,
            reapply_qty=True,
        )
    )
    detail = client.get_json(f"v1/quote/{quote_id}")
    missing_profiles = laser_plates_missing_profile(detail)
    profiles = count_profile_items(detail)
    has_weld = assembly_has_weld(detail, part_key=part_key)
    qty_bad = bom_qty_mismatches(detail, bom_rows, part_key=part_key)
    if missing_profiles or (want_weld and not has_weld) or qty_bad:
        notes.append(
            f"WARNING: after {attempts} finalize attempts still "
            f"profile={profiles} missing={len(missing_profiles)} "
            f"weld={has_weld} bom_mismatch={qty_bad}"
        )
    else:
        notes.append("Verified Profile/Weld/BOM qty after finalize retries")
    return notes
