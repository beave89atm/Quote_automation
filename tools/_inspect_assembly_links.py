"""Read-only: compare assembly hierarchy fields UI vs API quotes."""
from __future__ import annotations

import json

from secturafab.client import SecturaFabClient
from secturafab.push import SecturaFabPushService

c = SecturaFabClient()
s = SecturaFabPushService(c)

KEYS = [
    "ID",
    "Description",
    "ProductType",
    "ParentID",
    "AssemblyID",
    "AssemblyLevel",
    "AssemblyName",
    "AssemblyQty",
    "isAssemblyItem",
    "IsAssembly",
    "Quantity",
]


def show(label: str, quote_number: str) -> None:
    q = s.find_quote_by_number(quote_number)
    if not q:
        # try by scanning recent
        print(label, "not found by number", quote_number)
        return
    d = c.get_json(f"v1/quote/{q['ID']}")
    print(f"\n=== {label} {d.get('QuoteNumber')} quoteID={q['ID'][:8]} items={len(d.get('ItemList') or [])} ===")
    for it in d.get("ItemList") or []:
        row = {k: it.get(k) for k in KEYS}
        print(json.dumps(row, default=str))


def show_by_id(label: str, qid: str) -> None:
    d = c.get_json(f"v1/quote/{qid}")
    print(f"\n=== {label} {d.get('QuoteNumber')} quoteID={qid[:8]} items={len(d.get('ItemList') or [])} ===")
    for it in d.get("ItemList") or []:
        row = {k: it.get(k) for k in KEYS}
        print(json.dumps(row, default=str))


show("Kyle UI", "Q9836")

# job 43 recorded quote if still exists
from app.db import SessionLocal, Job

j = SessionLocal().get(Job, 43)
sf = ((j.takeoff() or {}).get("secturafab") if j else None) or {}
if sf.get("quote_id"):
    show_by_id("Job43 API", sf["quote_id"])

# newest PN 73476004
q = s.find_quote_by_number("PN 73476004")
if q:
    show_by_id("find PN 73476004", q["ID"])
