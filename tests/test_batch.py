"""Batch upload pairing, no-weld zeros, and POST /api/jobs/batch."""

from __future__ import annotations

import importlib
import io
import os
import sys
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.batch import pair_upload_files
from quote_core.config import load_shop_rates
from quote_core.time_engine import compute_weld_times
from quote_core.weld.takeoff import _build_items_from_signals

_RELOAD_MODULES = (
    "app.paths",
    "app.db",
    "app.auth",
    "app.services",
    "app.main",
)


def _reload_app_modules() -> None:
    for mod_name in _RELOAD_MODULES:
        if mod_name in sys.modules:
            importlib.reload(sys.modules[mod_name])
        else:
            importlib.import_module(mod_name)


def test_pair_upload_files_by_stem():
    files = [
        ("80341687.pdf", b"%PDF-a"),
        ("80341687.stp", b"ISO-10303"),
        ("LaserOnly.PDF", b"%PDF-b"),
        ("orphan.STEP", b"ISO-orphan"),
        ("notes.txt", b"nope"),
        ("DUP.pdf", b"%PDF-1"),
        ("dup.STP", b"stp-first"),
        ("dup.step", b"stp-last"),
    ]
    paired, skipped = pair_upload_files(files)
    by_stem = {p.stem.lower(): p for p in paired}
    assert set(by_stem) == {"80341687", "laseronly", "dup", "orphan"}
    assert by_stem["80341687"].stp_name == "80341687.stp"
    assert by_stem["laseronly"].stp_name is None
    assert by_stem["dup"].stp_bytes == b"stp-last"
    assert by_stem["orphan"].stp_name == "orphan.STEP"
    assert by_stem["orphan"].pdf_name is None
    assert any("notes.txt" in s for s in skipped)


def test_pair_upload_files_dxf_only_and_mixed():
    files = [
        ("flat.dxf", b"0\nSECTION\n"),
        ("assy.pdf", b"%PDF"),
        ("assy.dxf", b"0\nTEXT\n1\nPOWDER\n"),
        ("assy.stp", b"ISO"),
    ]
    paired, skipped = pair_upload_files(files)
    assert skipped == []
    by_stem = {p.stem.lower(): p for p in paired}
    assert set(by_stem) == {"flat", "assy"}
    assert by_stem["flat"].dxf_name == "flat.dxf"
    assert by_stem["flat"].pdf_name is None
    assert by_stem["assy"].pdf_name == "assy.pdf"
    assert by_stem["assy"].dxf_name == "assy.dxf"
    assert by_stem["assy"].stp_name == "assy.stp"


def test_no_weld_symbols_empty_items_and_zero_fitup():
    items, flags = _build_items_from_signals(
        sizes=[],
        notes=["SOME FAB NOTE"],
        page_hits=[],
        stp_summary={"solid_count": 2, "solids": []},
        pdf_name="laser.pdf",
        pdf_dimensions=[12.0, 24.0, 36.0],
    )
    assert items == []
    assert any("No weld symbols" in f for f in flags)

    rates = load_shop_rates()
    times = compute_weld_times(
        items,
        rates,
        efficiency_pct=100,
        part_count=0,
        component_weights_lb=[],
    )
    assert times.total_inches == 0.0
    assert times.weld_minutes == 0.0
    assert times.fitup_with_fixture_minutes == 0.0
    assert times.fitup_no_fixture_minutes == 0.0


@pytest.fixture()
def batch_client(tmp_path):
    previous = os.environ.get("KANNON_DATA_DIR")
    os.environ["KANNON_DATA_DIR"] = str(tmp_path)
    _reload_app_modules()
    from app.main import app

    with TestClient(app) as c:
        yield c

    if previous is None:
        os.environ.pop("KANNON_DATA_DIR", None)
    else:
        os.environ["KANNON_DATA_DIR"] = previous
    _reload_app_modules()


@pytest.fixture()
def batch_token(batch_client: TestClient) -> str | None:
    from app.paths import RATES_PATH
    from quote_core.config import load_shop_rates

    rates = load_shop_rates(RATES_PATH)
    password = rates.shared_password or ""
    if not password:
        return None
    res = batch_client.post("/api/login", json={"password": password})
    assert res.status_code == 200
    return str(res.json()["token"])


def test_batch_create_returns_n_jobs(batch_client: TestClient, batch_token: str | None):
    headers = {"X-App-Token": batch_token} if batch_token else {}
    files = [
        ("files", ("part-a.pdf", io.BytesIO(b"%PDF-1"), "application/pdf")),
        ("files", ("part-a.stp", io.BytesIO(b"ISO-A"), "application/octet-stream")),
        ("files", ("part-b.pdf", io.BytesIO(b"%PDF-2"), "application/pdf")),
        ("files", ("orphan.stp", io.BytesIO(b"ISO-O"), "application/octet-stream")),
    ]
    with patch("app.main.process_job"):
        res = batch_client.post("/api/jobs/batch", files=files, headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["created_count"] == 3
    assert len(body["jobs"]) == 3
    titles = {j["title"] for j in body["jobs"]}
    assert "part-a" in titles
    assert "part-b" in titles
    assert "orphan" in titles

    jobs_a = [j for j in body["jobs"] if j["title"] == "part-a"][0]
    assert jobs_a.get("stp_filename") == "part-a.stp"
    jobs_b = [j for j in body["jobs"] if j["title"] == "part-b"][0]
    assert not jobs_b.get("stp_filename")
    jobs_o = [j for j in body["jobs"] if j["title"] == "orphan"][0]
    assert jobs_o.get("stp_filename") == "orphan.stp"
    assert not jobs_o.get("pdf_filename")


def test_batch_push_rejects_processing(batch_client: TestClient, batch_token: str | None):
    headers = {"X-App-Token": batch_token} if batch_token else {}
    files = [("files", ("wait.pdf", io.BytesIO(b"%PDF-w"), "application/pdf"))]
    with patch("app.main.process_job"):
        created = batch_client.post("/api/jobs/batch", files=files, headers=headers)
    assert created.status_code == 200
    job_id = created.json()["jobs"][0]["id"]

    # Leave status as uploaded/processing-equivalent
    with patch("secturafab.config.SecturaFabConfig.require_credentials"):
        res = batch_client.post(
            "/api/jobs/batch-push",
            headers=headers,
            json={"job_ids": [job_id]},
        )
    assert res.status_code == 200
    body = res.json()
    assert body["queued_count"] == 0
    assert body["rejected"]
    assert body["rejected"][0]["reason"] == "takeoff still running"


def test_batch_push_queues_pdf_only_without_library(
    batch_client: TestClient, batch_token: str | None
):
    from app.db import Job, SessionLocal

    headers = {"X-App-Token": batch_token} if batch_token else {}
    files = [("files", ("lonely.pdf", io.BytesIO(b"%PDF-l"), "application/pdf"))]
    with patch("app.main.process_job"):
        created = batch_client.post("/api/jobs/batch", files=files, headers=headers)
    assert created.status_code == 200
    job_id = created.json()["jobs"][0]["id"]

    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        assert job
        job.status = "review"
        job.set_takeoff({"library": {}, "total_inches": 0})
        db.commit()
    finally:
        db.close()

    with patch("app.main.push_jobs_secturafab_batch"), patch(
        "secturafab.config.SecturaFabConfig.require_credentials"
    ):
        res = batch_client.post(
            "/api/jobs/batch-push",
            headers=headers,
            json={"job_ids": [job_id]},
        )
    assert res.status_code == 200
    body = res.json()
    assert body["queued_count"] == 1
    assert job_id in body["queued"]


def test_batch_creates_dxf_only_job(batch_client: TestClient, batch_token: str | None):
    headers = {"X-App-Token": batch_token} if batch_token else {}
    files = [("files", ("nest.dxf", io.BytesIO(b"0\nSECTION\n"), "application/dxf"))]
    with patch("app.main.process_job"):
        res = batch_client.post("/api/jobs/batch", files=files, headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["created_count"] == 1
    job = body["jobs"][0]
    assert job["title"] == "nest"
    assert job.get("dxf_filename") == "nest.dxf"
    assert not job.get("pdf_filename")


def test_create_job_stp_only(batch_client: TestClient, batch_token: str | None):
    headers = {"X-App-Token": batch_token} if batch_token else {}
    files = {"stp": ("solo.step", io.BytesIO(b"ISO-10303"), "application/octet-stream")}
    with patch("app.main.process_job"):
        res = batch_client.post("/api/jobs", files=files, headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body.get("stp_filename") == "solo.step"
    assert not body.get("pdf_filename")


def test_batch_push_without_keys_fails_clearly(
    batch_client: TestClient, batch_token: str | None
):
    headers = {"X-App-Token": batch_token} if batch_token else {}
    res = batch_client.post(
        "/api/jobs/batch-push",
        headers=headers,
        json={"job_ids": [1]},
    )
    assert res.status_code == 400
    assert "SECTURAFAB_CLIENT_ID" in res.text
