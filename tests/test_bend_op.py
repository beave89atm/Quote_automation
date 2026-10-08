"""Line bend count is the Bend operation's NumberOfBends. Offline reads only."""

from __future__ import annotations

import json
from pathlib import Path

from secturafab.bend_op import (
    BEND_COUNT_NOT_SET,
    BEND_COUNT_TIME_MISMATCH,
    BEND_COUNT_WRITE_ENDPOINT,
    line_bend_count,
)

_Q10504 = Path("tests/fixtures/q10504_after_finish_tree.json")
_Q10368 = Path("tests/fixtures/q10368_bend_param.json")


def _q10504_item() -> dict:
    tree = json.loads(_Q10504.read_text(encoding="utf-8"))
    return tree["Data"][0]


def _q10368_item() -> dict:
    return json.loads(_Q10368.read_text(encoding="utf-8"))


def test_q10504_number_of_bends_is_3_and_time_matches():
    count, flag = line_bend_count(_q10504_item(), formed=True)
    assert flag is None
    assert count == 3


def test_q10368_number_of_bends_is_2_and_time_is_60():
    count, flag = line_bend_count(_q10368_item(), formed=True)
    assert flag is None
    assert count == 2


def test_flat_part_count_is_zero_without_a_bend_op():
    count, flag = line_bend_count({"OperationParamList": []}, formed=False)
    assert count == 0
    assert flag is None


def test_formed_part_without_bend_param_is_not_gold():
    item = {
        "OperationCostList": [
            {
                "OperationName": "Bend",
                "CostCategory": "Bend",
                "Description": "Auto Bend",
                "Cost_Units": "hour",
                "Value": 0.025,
            }
        ],
        "OperationParamList": [],
    }
    count, flag = line_bend_count(item, formed=True)
    assert count == 0
    assert flag == BEND_COUNT_NOT_SET


def test_number_of_bends_zero_is_not_gold():
    item = _q10368_item()
    item["OperationParamList"][0]["DataOperationList"][0]["NumberOfBends"] = 0
    item["OperationParamList"][0]["DataOperationList"][0]["Time"] = 0
    _count, flag = line_bend_count(item, formed=True)
    assert flag == BEND_COUNT_NOT_SET


def test_time_must_equal_bends_times_time_per_bend():
    item = _q10368_item()
    item["OperationParamList"][0]["DataOperationList"][0]["Time"] = 90
    _count, flag = line_bend_count(item, formed=True)
    assert flag == BEND_COUNT_TIME_MISMATCH


def test_no_captured_endpoint_writes_number_of_bends():
    assert BEND_COUNT_WRITE_ENDPOINT is None
