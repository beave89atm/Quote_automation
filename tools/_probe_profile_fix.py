"""Find how to attach Profile ops after quickAddCAD. Cleanup test quotes after."""
from __future__ import annotations

import json
import time
from pathlib import Path

from secturafab.client import SecturaFabClient
from secturafab.push import SecturaFabPushService

c = SecturaFabClient()
s = SecturaFabPushService(c)
TEST_QUOTES: list[str] = []


def dump_item(label: str, it: dict) -> None:
    ops = it.get("OperationCostList") or []
    print(f"\n=== {label} ===")
    print(
        "desc",
        (it.get("Description") or "")[:60],
        "| Machine",
        it.get("Machine"),
        "Thk",
        it.get("Thickness"),
        "WCat",
        it.get("WeightCategory"),
        "Sub",
        it.get("ProductSubType"),
    )
    print(
        "Primary",
        it.get("PrimaryTimeDisp"),
        "NestedArea",
        it.get("NestedArea"),
        "IsPlate",
        it.get("IsPlate"),
        "IsLinear",
        it.get("IsLinear"),
    )
    print(
        "ops",
        [(o.get("OperationName"), o.get("OperationType"), o.get("CostCategory"), o.get("Cost")) for o in ops],
    )
    params = it.get("OperationParamList") or []
    print(
        "param calcs",
        [
            (
                p.get("CalcName") or (p.get("DataOperationList") or [{}])[0].get("CalcName"),
                p.get("QuoteOperationID"),
            )
            for p in params
        ],
    )


def main() -> None:
    # --- Compare good vs bad ---
    bad_q = s.find_quote_by_number("PN 73476004")
    bad = c.get_json(f"v1/quote/{bad_q['ID']}")
    bad_item = next(x for x in bad["ItemList"] if "73000567" in str(x.get("Description")))
    dump_item("BAD API 73000567", bad_item)

    good_q = s.find_quote_by_number("21678-1")
    good = c.get_json(f"v1/quote/{good_q['ID']}")
    good_item = next(
        x
        for x in good["ItemList"]
        if any((o.get("OperationName") == "Profile") for o in (x.get("OperationCostList") or []))
    )
    dump_item("GOOD UI Profile item", good_item)

    # Diff keys of interest
    keys = sorted(
        set(bad_item) | set(good_item),
        key=str,
    )
    diffs = []
    for k in keys:
        if k in {"OperationCostList", "OperationParamList", "QtyMatrixList"}:
            continue
        bv, gv = bad_item.get(k), good_item.get(k)
        if bv != gv and type(bv) is not dict:
            if isinstance(bv, (list, dict)) or isinstance(gv, (list, dict)):
                continue
            diffs.append((k, bv, gv))
    print("\nScalar diffs (bad vs good) sample:")
    for row in diffs[:40]:
        print(" ", row)

    # --- Materials / inventory lookup ---
    print("\n--- material/inventory probes ---")
    for path in (
        "v1/inventory",
        "v1/Inventory",
        "v1/material",
        "v1/materials",
        "v1/Material",
        "v1/weightCategory",
        "v1/WeightCategory",
        "v1/priceBook",
        "v1/PriceBook",
        "v1/operation",
        "v1/operations",
        "v1/Operation",
        "v1/quoteOnline/material",
    ):
        r = c.request("GET", path)
        if r.status_code != 404:
            print(path, r.status_code, r.text[:160].replace("\n", " "))

    # --- Try update WeightCategory on bad item (on a COPY quote, not production) ---
    print("\n--- create throwaway quote from STEP, then try Profile triggers ---")
    stp = Path("data/uploads/42/73476004.stp")
    if not stp.exists():
        stp = Path("data/uploads/42/73476004.STEP")
    qnum = f"KANNON-PROFILE-TEST-{int(time.time()) % 100000}"
    qid = s.create_quote(quote_number=qnum, description="", memo="")
    TEST_QUOTES.append(qid)
    print("created test quote", qnum, qid)

    # Import with explicit thickness matching Mat-MS-A36-0.25 style (use 0.25)
    with stp.open("rb") as fh:
        s.quick_add_cad(
            quote_id=qid,
            cad_files=[stp],
            material="A36",
            thickness="0.25",
            machine="Laser",
            memo="profile-test",
            qty=1,
        )
    detail = c.get_json(f"v1/quote/{qid}")
    item = next(
        (x for x in detail["ItemList"] if x.get("Machine") == "Laser" and not x.get("IsLinear")),
        detail["ItemList"][0],
    )
    dump_item("after import thickness=0.25", item)

    # Attempt WeightCategory updates + calc endpoints
    iid = item["ID"]
    attempts = [
        ("POST", "v1/quoteOnline", {"ID": iid, "QuoteID": qid, "WeightCategory": "Mat-MS-A36-0.25", "Thickness": 0.25, "Machine": "Laser", "IsPlate": True}),
        ("POST", "v1/quote", {"ID": qid, "ItemList": [{**item, "WeightCategory": "Mat-MS-A36-0.25", "IsPlate": True, "Thickness": 0.25}]}),
    ]
    for method, path, payload in attempts:
        r = c.request(method, path, json=payload)
        print("update", method, path, r.status_code, r.text[:100].replace("\n", " "))

    # API version variants for calculate
    for ver in ("1.0", "1", "2.0", "2"):
        for path in (
            f"v1/quoteOnline/{iid}/calculate",
            "v1/quoteOnline/calculate",
            f"v1/quote/{qid}/calculate",
            f"v1/Nest/quote/{qid}/0",
            f"v1/Nest/quote/{qid}/1",
            f"v1/quoteOnline/{iid}/recalculate",
            "v1/quoteOnline/Recalculate",
            "v1/quoteOnline/CalculateCost",
            "v1/quoteOnline/runPrimary",
        ):
            r = c.request(
                "POST",
                path,
                json={"ID": iid, "QuoteID": qid, "WeightCategory": "Mat-MS-A36-0.25"},
                headers={"api-version": ver},
            )
            if r.status_code not in (404, 405):
                print(f"ver={ver}", path, r.status_code, r.text[:140].replace("\n", " "))

    # Re-read after attempts
    detail2 = c.get_json(f"v1/quote/{qid}")
    item2 = next(x for x in detail2["ItemList"] if x["ID"] == iid)
    dump_item("after update attempts", item2)

    # Search openapi/swagger for profile/nest/calc terms
    print("\n--- openapi search ---")
    spec = None
    from secturafab.discover import try_fetch_openapi

    spec = try_fetch_openapi(c)
    if spec:
        text = json.dumps(spec)
        for term in ("Profile", "quickAddCAD", "WeightCategory", "calculate", "Nest", "Primary"):
            print(term, text.lower().count(term.lower()))
        # print matching paths
        paths = (spec.get("paths") or {}) if isinstance(spec, dict) else {}
        hits = [p for p in paths if any(t in p.lower() for t in ("calc", "nest", "profile", "cost", "weight", "material", "operation"))]
        print("path hits", hits[:50])
    else:
        print("no openapi")


def cleanup() -> None:
    for qid in TEST_QUOTES:
        r = c.request("DELETE", f"v1/quote/{qid}")
        print("DELETE", qid, r.status_code)


if __name__ == "__main__":
    try:
        main()
    finally:
        cleanup()
