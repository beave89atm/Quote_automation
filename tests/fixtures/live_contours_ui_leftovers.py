"""Spent Contours UI leftovers — Adjust Properties Contours column absent.

Unfinished UI leftovers. Finish was never clicked. invented=false.
Do not remint / PATCH. Do not invent Contours / InternalData.

    75f07c2b / Q10329 / ZZ-DEL-Q10329-14327-3-contours-ui
      14327-3 L-angle — Contours column absent; Finish never
    aed89628 / Q10330 / ZZ-DEL-Q10330-21841-1-contours-ui
      21841-1 angle/channel — Contours column absent; Finish never
    5e72fe39 / Q10331 / ZZ-DEL-Q10331-14327-1-contours-ui
      14327-1 flat-looking — Contours column absent; Finish never

Q10333 / b5f56ac3 / H.6.38 Safe Cave is NOT this class. It is a
Contours PASS protect (Cad / Contours=1 / 8 bends + Profile /
Laser Bay1 / UC 176.96). See ``live_q10333_h638``. Q10336 /
f73dd116 is a Cad+Laser Finish leftover (finished
NumberOfContours=1 matches Q10333; OCC=0 expected) — Finish was
posted; not this unfinished-UI class. Q10344 / 55f12530 is the
Kyle UI control leftover (Cad + 0.1875 inch → Contours fill →
Finish) — not this class. Q10346 / B80510901 Sprout main plate is
a Contours PASS outside H.6.38 — not this unfinished-UI class.
Q10348 / 1defeed8 / H.16.70 Safe Cave Contours PASS (Cad + 0.1875
inch → Contours fill → Finish) — not this unfinished-UI class.
Q10349 / c4394006 / D.H.30.96 Safe Cave Contours PASS (Cad + 0.1875
inch → Contours fill → Finish) — not this unfinished-UI class.
Q10351 / 0c62fce9 / H.8.38 Safe Cave Contours PASS (Cad + inches
→ Contours fill → Finish) — not this unfinished-UI class.
Q10354 / 7881d4b3 / D.H.38.96 Safe Cave Contours FAIL leftover
(Cad + 0.1875 in, finished ProductType part; NumberOfContours
unavailable) — empty-InternalData Contours-FAIL class, not PASS
and not this unfinished-UI class. Q10356 / 05bee105 / V.20.78
Safe Cave Contours FAIL leftover (Cad + 0.1875 in, finished
ProductType part; NumberOfContours missing) — same Contours-FAIL
class as Q10354, not PASS and not this unfinished-UI class.
Never remint / PATCH / ZZ-DEL. Tip 0759273 ZZ-DEL-fail narrative
is reversed.

Wrong-org Time mint (not a Contours leftover; ID unknown):
    Q10332 / ZZ-DEL-wrong-org-Time — quote ID not restated in
    recent notes; description-only forbid.

Keep existing forever-forbids for 8973f890 / 35136-1,
14327-5 / c5cd8689, 14327-8 / 1cd941c6, Q10329-31,
H638-CADPLATE / 5e7bfc0b, Q10334 / e2683a3f, and Q10335 / bcff1a24.
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
