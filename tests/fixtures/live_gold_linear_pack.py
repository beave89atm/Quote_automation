"""Named persist: gold Linear pack is Saw + Saw-Setup + UnitCost + ProductID/SKU.

Gold look remains 1001898-1 a7dc46bf linear rows (readonly). Do not GET
that quote from this agent. Do not PATCH. Do not remint.

Leftover cookie HTTP POST /Quote/AddItem_Linear 302s (same class as
29340-1) and lands empty Saw OperationCostList. Gold is page orange
Long → tenant SKU picker → cut length → OnAddLinearClick / New Line
Item. List[0] already has Saw + Saw-Setup in Primary Costs, UnitCost
filled, ProductID/SKU set. Internal is empty. ItemID is empty for new
rows. Do not graft Operation→Saw. Do not enter holes on Long.

Kyle Loom Long: Product Type auto Tube, search RCT, Name = PN + SKU,
length decimal inches, qty 1, Machine already Saw. Saw 0:19 and Saw
Setup 15:00 show in Primary Costs at create — not on the main grid.
"""

from __future__ import annotations

from typing import Any

from secturafab.website import GOLD_SAW_CALCULATOR_NAMES

GOLD_QUOTE_ID = "a7dc46bf-836a-4250-b038-9331cc0595a7"
GOLD_QUOTE_NUMBER = "1001898-1"

# Existing gold_1001898_get linear UnitCost — not a new live GET.
GOLD_LIST0_PACK: dict[str, Any] = {
    "list_n": 1,
    "tag": "",
    "badge_string": "",
    "production_ready": False,
    "ocl_n": 2,
    "ocl_names": list(GOLD_SAW_CALCULATOR_NAMES),
    "unit_cost": 7.63,
    "product_id": "pid-1001880-2",
    "sku": "RT4X0.375-A519",
}

LEFTOVER_MISS: dict[str, Any] = {
    "finish_via": "cookie_http",
    "additem_linear_302": True,
    "additem_linear_status": 302,
    "cookie_302_is_logout": False,
    "ocl_n": 0,
    "ocl_names": [],
    "unit_cost": 0,
    "product_id": "",
    "sku": "",
    "long_clicked": False,
}

GOLD_LINEAR_PACK_BIND: dict[str, Any] = {
    "quote_id": GOLD_QUOTE_ID,
    "quote_number": GOLD_QUOTE_NUMBER,
    "readonly": True,
    "finish_posted": True,
    "invent_internal": False,
    "cookie_additem_linear": False,
    "graft_operation_saw": False,
    "pack_already_on_additem_list": True,
    "list_pack_keys": ("OperationCostList", "UnitCost", "ProductID", "SKU"),
    "gold_linear": {
        "ocl_names": list(GOLD_SAW_CALCULATOR_NAMES),
        "unit_cost": GOLD_LIST0_PACK["unit_cost"],
        "product_id": GOLD_LIST0_PACK["product_id"],
        "sku": GOLD_LIST0_PACK["sku"],
        "machine": "Saw",
        "internal": "",
        "item_id": "",
    },
    "leftover_miss": dict(LEFTOVER_MISS),
    "list0_pack": dict(GOLD_LIST0_PACK),
    "OnAddLinearClick": {
        "after": ("orange Long", "tenant SKU picker", "cut length"),
        "xhr": "POST /Quote/AddItem_Linear",
        "via": "page_fn",
        "internal": "",
        "itemid": "00000000-0000-0000-0000-000000000000",
        "cookie_http_fail_closed": True,
    },
}


def gold_linear_pack_bind_dump() -> dict[str, Any]:
    """Signed-off gold Linear pack vs leftover cookie 302 / empty Saw OCL."""
    return dict(GOLD_LINEAR_PACK_BIND)


def gold_linear_list0_pack_result() -> dict[str, Any]:
    """AddItem_Linear List[0] capture that is gold Saw pack."""
    return {
        "response_list_n": GOLD_LIST0_PACK["list_n"],
        "response_tag": GOLD_LIST0_PACK["tag"],
        "response_badge_string": GOLD_LIST0_PACK["badge_string"],
        "response_production_ready": GOLD_LIST0_PACK["production_ready"],
        "response_ocl_n": GOLD_LIST0_PACK["ocl_n"],
        "response_ocl_names": list(GOLD_LIST0_PACK["ocl_names"]),
        "response_unit_cost": GOLD_LIST0_PACK["unit_cost"],
        "response_product_id": GOLD_LIST0_PACK["product_id"],
        "response_sku": GOLD_LIST0_PACK["sku"],
        "long_from_page": True,
        "long_clicked": True,
        "via": "page_fn",
        "finish_fn": "OnAddLinearClick",
        "request_internal": "",
        "request_itemid": "00000000-0000-0000-0000-000000000000",
    }


def leftover_cookie_linear_302_result() -> dict[str, Any]:
    """Leftover cookie HTTP AddItem_Linear 302 / empty Saw OCL."""
    return {
        "response_list_n": 0,
        "response_tag": "",
        "response_badge_string": "",
        "response_production_ready": False,
        "response_ocl_n": 0,
        "response_ocl_names": [],
        "response_unit_cost": 0,
        "response_product_id": "",
        "response_sku": "",
        "long_from_page": False,
        "long_clicked": False,
        "via": "cookie_http",
        "finish_fn": "",
        "status": 302,
        "additem_linear_302": True,
        "cookie_302_is_logout": False,
    }


def leftover_cookie_linear_empty_saw_dump() -> dict[str, Any]:
    """Leftover: cookie AddItem_Linear 302 + empty Saw pack."""
    return {
        "readonly": True,
        "finish_via": "cookie_http",
        "live_leftover": dict(LEFTOVER_MISS),
        "list0_pack": {
            "ocl_n": 0,
            "ocl_names": [],
            "unit_cost": 0,
            "product_id": "",
            "sku": "",
        },
        "cookie_302_is_logout": False,
    }
