"""Website organization picker: exact name, known id, no Add Organization."""

from __future__ import annotations

import json
import shutil
import subprocess

from secturafab.chrome_cdp import _BIND_ORG_DETAIL_JS
from secturafab.org_ops import TIME_WACO_ORG_ID, TIME_WACO_ORG_NAME

_TIME = TIME_WACO_ORG_ID


def _run(tmp_path, items, org_name, org_id=""):
    node = shutil.which("node")
    assert node
    harness = (
        r"""
const spec = """
        + json.dumps({"orgName": org_name, "orgId": org_id})
        + r""";
const items = """
        + json.dumps(items)
        + r""";
const clicks = [];
const rows = items.map((row) => {
  const el = {
    textContent: row.text,
    value: row.text,
    getAttribute(name) {
      if (name === "data-id" || name === "data-organization-id") return row.id || "";
      return "";
    },
    click() {
      clicks.push(row.text);
      landed = row.id || "";
      jQuery.ajax({url: "/Quote/OrganizationDetail"});
    },
  };
  return el;
});
const addButton = {
  textContent: "Add Organization",
  value: "Add Organization",
  click() { clicks.push("Add Organization"); },
};
let landed = "";
function collection(list) {
  const out = list.slice();
  out.length = list.length;
  return out;
}
const jQuery = function(sel) {
  const key = String(sel || "");
  if (key === "#Organization_OrganizationName") {
    return {
      length: 1,
      val(v) { return ""; },
      trigger() { return this; },
      data(name) {
        if (name !== "kendoAutoComplete") return null;
        return { search() {}, dataItem(el) { return {ID: el && el.getAttribute && el.getAttribute("data-id")}; } };
      },
    };
  }
  if (key === "#PrimaryOrganizationID") {
    return { length: 1, val() { return landed; } };
  }
  if (key.indexOf("li") >= 0 || key.indexOf("k-list") >= 0) return collection(rows);
  return { length: 0, val() { return ""; }, data() { return null; } };
};
jQuery.ajax = function() { return {apply() {}}; };
global.jQuery = jQuery;
global.window = global;
const apply = 
"""
        + _BIND_ORG_DETAIL_JS
        + r"""
;
Promise.resolve(apply(spec)).then((value) => {
  process.stdout.write(JSON.stringify({value, clicks, addClicks: clicks.filter((t) => /add\\s+organ/i.test(t)).length}));
}).catch((err) => {
  process.stderr.write(String(err && err.stack || err));
  process.exit(1);
});
"""
    )
    script = tmp_path / "org_picker.js"
    script.write_text(harness)
    proc = subprocess.run(
        [node, str(script)],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_picker_clicks_only_the_exact_name(tmp_path):
    out = _run(
        tmp_path,
        [
            {"text": "Time Manufacturing Waco", "id": "11111111-1111-4111-8111-111111111111"},
            {"text": TIME_WACO_ORG_NAME, "id": _TIME},
            {"text": "Add Organization", "id": ""},
        ],
        TIME_WACO_ORG_NAME,
        _TIME,
    )
    assert out["clicks"] == [TIME_WACO_ORG_NAME]
    assert out["addClicks"] == 0
    assert out["value"]["ok"] is True
    assert out["value"]["org_id"] == _TIME
    assert out["value"]["add_organization_clicked"] is False
    assert "indexOf(orgName.toLowerCase())" not in _BIND_ORG_DETAIL_JS


def test_picker_does_not_click_add_organization_on_a_miss(tmp_path):
    out = _run(
        tmp_path,
        [
            {"text": "Time Manufacturing Waco", "id": "11111111-1111-4111-8111-111111111111"},
            {"text": "Add Organization", "id": ""},
        ],
        TIME_WACO_ORG_NAME,
        _TIME,
    )
    assert out["clicks"] == []
    assert out["addClicks"] == 0
    assert out["value"]["ok"] is False
    assert out["value"]["why"] == "org_lookup_miss"
    assert "exact Sectura organization name" in out["value"]["flag"]
    assert "Not creating an organization" in out["value"]["flag"]


def test_picker_does_not_take_the_first_substring_or_an_ambiguous_list(tmp_path):
    substring = _run(
        tmp_path,
        [
            {"text": "Time Manufacturing Waco", "id": "11111111-1111-4111-8111-111111111111"},
            {"text": "Something Else", "id": "22222222-2222-4222-8222-222222222222"},
        ],
        "Time Manufacturing",
        _TIME,
    )
    assert substring["clicks"] == []
    assert substring["value"]["ok"] is False

    ambiguous = _run(
        tmp_path,
        [
            {"text": TIME_WACO_ORG_NAME, "id": _TIME},
            {"text": TIME_WACO_ORG_NAME, "id": "33333333-3333-4333-8333-333333333333"},
        ],
        TIME_WACO_ORG_NAME,
        _TIME,
    )
    assert ambiguous["clicks"] == []
    assert ambiguous["value"]["why"] == "org_lookup_ambiguous"

    mismatch = _run(
        tmp_path,
        [{"text": TIME_WACO_ORG_NAME, "id": "33333333-3333-4333-8333-333333333333"}],
        TIME_WACO_ORG_NAME,
        _TIME,
    )
    assert mismatch["clicks"] == []
    assert mismatch["value"]["why"] == "org_id_mismatch"
