"""Printable shop quote for weld + fit-up labor (no SecturaFAB required)."""

from __future__ import annotations

import html
from typing import Any


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _money(value: Any) -> str:
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "—"


def _hours(value: Any) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "—"


def _minutes(value: Any) -> str:
    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return "—"


def render_quote_html(data: dict[str, Any]) -> str:
    """Build a print-ready HTML quote from a Job.to_dict() payload."""
    times = data.get("times") or {}
    takeoff = data.get("takeoff") or {}
    items = takeoff.get("items") or []
    flags = list(data.get("flags") or [])
    title = data.get("title") or f"Job {data.get('id')}"
    status = data.get("status") or ""
    job_id = data.get("id")
    efficiency = data.get("efficiency_pct")
    pdf_name = data.get("pdf_filename") or ""
    stp_name = data.get("stp_filename") or ""
    bom = data.get("bom_config") or ""
    created = (data.get("created_at") or "")[:10]
    rate = times.get("labor_rate_per_hour")
    placeholder = bool(times.get("labor_placeholder"))
    labor_notes = ""
    # Prefer live shop-rate note when present on times; flags cover takeoff caveats.
    if placeholder:
        labor_notes = (
            "Shop labor rate is a placeholder in config/shop_rates.yaml. "
            "Confirm the $/hr before sending this to a customer."
        )

    rows = []
    for line in times.get("by_size") or []:
        rows.append(
            "<tr>"
            f"<td>{_esc(line.get('size'))}</td>"
            f"<td class='num'>{_esc(line.get('inches'))}</td>"
            f"<td class='num'>{_esc(line.get('ipm'))}</td>"
            f"<td class='num'>{_minutes(line.get('weld_minutes'))}</td>"
            "</tr>"
        )
    if not rows:
        rows.append('<tr><td colspan="4">No weld inches on this quote.</td></tr>')

    takeoff_rows = []
    for item in items:
        takeoff_rows.append(
            "<tr>"
            f"<td>{_esc(item.get('size'))}</td>"
            f"<td class='num'>{_esc(item.get('inches'))}</td>"
            f"<td>{_esc(item.get('joint_notes') or '')}</td>"
            f"<td>{_esc(item.get('confidence') or '')}</td>"
            "</tr>"
        )
    if not takeoff_rows:
        takeoff_rows.append('<tr><td colspan="4">No takeoff lines — add them in the app and Recalculate.</td></tr>')

    flag_items = "".join(f"<li>{_esc(f)}</li>" for f in flags) or "<li>None</li>"

    banner = ""
    if placeholder:
        banner = f'<p class="banner">{_esc(labor_notes)}</p>'

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Quote — {_esc(title)}</title>
<style>
  :root {{ color-scheme: light; }}
  body {{ font-family: "Segoe UI", system-ui, sans-serif; margin: 1.5rem auto; max-width: 820px; color: #1c2430; }}
  h1 {{ margin: 0 0 0.25rem; font-size: 1.6rem; }}
  h2 {{ margin: 1.4rem 0 0.4rem; font-size: 1.1rem; }}
  .meta, .muted {{ color: #5b6b7c; }}
  .brand {{ font-weight: 700; letter-spacing: 0.02em; color: #0f3d5c; }}
  table {{ border-collapse: collapse; width: 100%; margin: 0.5rem 0 0; }}
  th, td {{ border: 1px solid #c5d0db; padding: 0.45rem 0.55rem; text-align: left; }}
  th {{ background: #eef3f7; font-size: 0.85rem; }}
  td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .totals {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-top: 0.75rem; }}
  .card {{ border: 1px solid #c5d0db; border-radius: 8px; padding: 0.75rem 0.9rem; }}
  .card strong {{ display: block; font-size: 1.25rem; margin-top: 0.2rem; }}
  .banner {{ background: #fff3d6; border: 1px solid #e6c97a; padding: 0.65rem 0.8rem; border-radius: 8px; }}
  .disclaimer {{ font-size: 0.9rem; color: #5b6b7c; }}
  .no-print {{ margin: 0 0 1rem; }}
  @media print {{
    body {{ margin: 0.6in; }}
    .no-print {{ display: none; }}
    a {{ color: inherit; text-decoration: none; }}
  }}
</style>
</head>
<body>
  <p class="no-print"><button type="button" onclick="window.print()">Print / save PDF</button></p>
  <p class="brand">Kannon Manufacturing</p>
  <h1>{_esc(title)}</h1>
  <p class="meta">
    Job #{_esc(job_id)} · {_esc(status)} · {_esc(created)}
    {f" · {_esc(pdf_name)}" if pdf_name else ""}
    {f" · {_esc(stp_name)}" if stp_name else ""}
    {f" · BOM -{_esc(str(bom).lstrip('-'))}" if bom else ""}
    {f" · Efficiency {_esc(efficiency)}%" if efficiency is not None else ""}
  </p>
  {banner}
  <h2>Weld inches by size</h2>
  <table>
    <thead><tr><th>Size</th><th class="num">Inches</th><th class="num">IPM</th><th class="num">Weld min</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>

  <h2>Shop labor quote</h2>
  <div class="totals">
    <div class="card">
      No fixture
      <strong>{_hours(times.get("quoted_no_fixture_hours"))} hr · {_money(times.get("quoted_no_fixture_labor"))}</strong>
      <span class="muted">includes {_minutes(times.get("fitup_no_fixture_minutes"))} min fit-up</span>
    </div>
    <div class="card">
      With fixture
      <strong>{_hours(times.get("quoted_with_fixture_hours"))} hr · {_money(times.get("quoted_with_fixture_labor"))}</strong>
      <span class="muted">includes {_minutes(times.get("fitup_with_fixture_minutes"))} min fit-up</span>
    </div>
  </div>
  <p class="muted">
    Total weld inches: {_esc(times.get("total_inches", 0))} ·
    Weld minutes: {_minutes(times.get("weld_minutes"))} ·
    Shop rate: {_money(rate)}/hr
  </p>

  <h2>Takeoff lines</h2>
  <table>
    <thead><tr><th>Size</th><th class="num">Inches</th><th>Notes</th><th>Confidence</th></tr></thead>
    <tbody>{''.join(takeoff_rows)}</tbody>
  </table>

  <h2>Review flags</h2>
  <ul>{flag_items}</ul>

  <p class="disclaimer">
    This is a weld + fit-up shop-labor quote from Quote Automation.
    Laser cutting, nesting, material, bend, and purchased hardware are
    <strong>not</strong> included here. Use SecturaFAB push when API keys are
    configured if you need the full shop quote.
  </p>
</body>
</html>"""
