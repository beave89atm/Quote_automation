"""Verify children get AssemblyID after ensure_assembly_root. Leaves throwaway quote."""
from __future__ import annotations

import time
from pathlib import Path

from secturafab.assembly_ops import ensure_assembly_root
from secturafab.client import SecturaFabClient
from secturafab.push import SecturaFabPushService

c = SecturaFabClient()
s = SecturaFabPushService(c)
qnum = f"KANNON-ASM-LINK-{int(time.time()) % 100000}"
r = c.request(
    "POST",
    "v1/quote",
    json={"QuoteNumber": qnum, "RevNumber": str(int(time.time())), "QuoteStatus": "OPEN-DRAFT"},
)
qid = c._parse_or_raise(r)
print("created", qnum, qid)

stp = Path("data/uploads/43/73476004.stp")
if not stp.exists():
    stp = Path("data/uploads/42/73476004.stp")
s.quick_add_cad(
    quote_id=qid,
    cad_files=[stp],
    material="A36",
    thickness="0.188",
    machine="Laser",
    memo="asm-link-verify",
    qty=1,
)

notes = ensure_assembly_root(c, qid, part_key="73476004")
print("notes", notes)

detail = c.get_json(f"v1/quote/{qid}")
root = next(it for it in detail["ItemList"] if it.get("ProductType") in (300, "assembly", "300"))
rid = root["ID"]
children = [it for it in detail["ItemList"] if it["ID"] != rid]
linked = [it for it in children if it.get("AssemblyID") == rid]
print(
    "root",
    root.get("Description"),
    "level",
    root.get("AssemblyLevel"),
    "children",
    len(children),
    "linked",
    len(linked),
)
for it in children[:3]:
    print(
        " ",
        (it.get("Description") or "")[:40],
        "AssemblyID",
        (it.get("AssemblyID") or "")[:8],
        "Level",
        it.get("AssemblyLevel"),
        "Name",
        it.get("AssemblyName"),
        "AsmQty",
        it.get("AssemblyQty"),
        "isAsmItem",
        it.get("isAssemblyItem"),
    )
assert len(linked) == len(children), "all children should link to assembly"
print("OK — left throwaway:", qnum, qid)
