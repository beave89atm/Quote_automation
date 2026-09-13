"""Spent Contours UI leftovers — Adjust Properties Contours column absent.

Unfinished UI leftovers. Finish was never clicked. invented=false.
Do not remint / PATCH. Do not invent Contours / InternalData.

    75f07c2b / Q10329 / ZZ-DEL-Q10329-14327-3-contours-ui
      14327-3 L-angle — Contours column absent; Finish never
    aed89628 / Q10330 / ZZ-DEL-Q10330-21841-1-contours-ui
      21841-1 angle/channel — Contours column absent; Finish never
    5e72fe39 / Q10331 / ZZ-DEL-Q10331-14327-1-contours-ui
      14327-1 flat-looking — Contours column absent; Finish never
    b5f56ac3 / Q10333 / ZZ-DEL-Q10333-H638-SafeCave-contours
      Safe Cave / H.6.38 Onshape STEP — leftover captured Contours
      column absent / HadOpenContours=false. Kyle later proved
      Component→Cad on Adjust Properties unlocks Contours (human
      Finish OK). Do not remint / PATCH. Documentary unlock proof.

Wrong-org Time mint (not a Contours leftover; ID unknown):
    Q10332 / ZZ-DEL-wrong-org-Time — quote ID not restated in
    recent notes; description-only forbid.

Keep existing forever-forbids for 8973f890 / 35136-1,
14327-5 / c5cd8689, 14327-8 / 1cd941c6, and Q10329-31.
Fail-close stays locked. Capture must be a new PN.
"""

from __future__ import annotations

from typing import Any

LEFTOVER_CONTOURS_UI: tuple[dict[str, Any], ...] = (
    {
        "quote_id": "75f07c2b-b000-47f4-9caa-c14520e2b068",
        "quote_id_prefix": "75f07c2b",
        "quote_number": "Q10329",
        "part_number": "14327-3",
        "zz_del_number": "ZZ-DEL-Q10329-14327-3-contours-ui",
        "shape": "L-angle",
        "contours_column_absent": True,
        "finish_clicked": False,
        "finish_posted": False,
        "invent": False,
        "unlocks_contours_fill": False,
        "fail_close": True,
        "readonly": True,
        "zz_del": True,
    },
    {
        "quote_id": "aed89628-b018-4b11-852f-bfed5bf8b964",
        "quote_id_prefix": "aed89628",
        "quote_number": "Q10330",
        "part_number": "21841-1",
        "zz_del_number": "ZZ-DEL-Q10330-21841-1-contours-ui",
        "shape": "angle/channel",
        "contours_column_absent": True,
        "finish_clicked": False,
        "finish_posted": False,
        "invent": False,
        "unlocks_contours_fill": False,
        "fail_close": True,
        "readonly": True,
        "zz_del": True,
    },
    {
        "quote_id": "5e72fe39-edc1-467c-925d-f1c8d74cc5d3",
        "quote_id_prefix": "5e72fe39",
        "quote_number": "Q10331",
        "part_number": "14327-1",
        "zz_del_number": "ZZ-DEL-Q10331-14327-1-contours-ui",
        "shape": "flat-looking",
        "contours_column_absent": True,
        "finish_clicked": False,
        "finish_posted": False,
        "invent": False,
        "unlocks_contours_fill": False,
        "fail_close": True,
        "readonly": True,
        "zz_del": True,
    },
    {
        "quote_id": "b5f56ac3-326d-48e9-b82d-1e09a7897107",
        "quote_id_prefix": "b5f56ac3",
        "quote_number": "Q10333",
        "part_number": "H.6.38",
        "customer": "Safe Cave",
        "source": "Onshape STEP",
        "zz_del_number": "ZZ-DEL-Q10333-H638-SafeCave-contours",
        "shape": "Onshape STEP",
        "contours_column_absent": True,
        "had_open_contours": False,
        "finish_clicked": False,
        "finish_posted": False,
        "invent": False,
        "unlocks_contours_fill": False,
        "component_to_cad_contours_proof": True,
        "kyle_loom_component_to_cad": True,
        "human_finish_ok_for_capture": True,
        "cad_set_via": "adjust_properties_dropdown_human",
        "fail_close": True,
        "readonly": True,
        "zz_del": True,
    },
)

# Quote ID was not restated in repo / PR 18 / prior leftover transcript /
# Dropbox. Forbid the Q number only — do not invent an ID.
WRONG_ORG_TIME_Q10332: dict[str, Any] = {
    "quote_id": None,
    "quote_id_prefix": None,
    "quote_number": "Q10332",
    "zz_del_number": "ZZ-DEL-wrong-org-Time",
    "why": "wrong-org Time mint",
    "id_unknown": True,
    "id_source": "not restated in recent notes",
    "invent": False,
    "readonly": True,
    "zz_del": True,
}


def leftover_contours_ui_dumps() -> list[dict[str, Any]]:
    """Read-only Contours UI leftovers. Does not unlock Contours fill."""
    return [dict(row) for row in LEFTOVER_CONTOURS_UI]


def wrong_org_time_q10332_dump() -> dict[str, Any]:
    """Read-only Q10332 note. Description-only; ID unknown."""
    return dict(WRONG_ORG_TIME_Q10332)
