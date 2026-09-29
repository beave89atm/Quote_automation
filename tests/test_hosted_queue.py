"""Hosted queue: one claim at a time, auth gate, audit, retry rules.

No Sectura calls. SQLite stands in for the Postgres SKIP LOCKED claim.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.hosted_auth import (
    authorize_claims,
    reset_verifier_for_tests,
    set_verifier_for_tests,
)
from app.hosted_queue import (
    POSTGRES_CLAIM_JOB_SQL,
    VercelBlobStore,
    claim_next,
    create_job,
    hosted_engine,
    list_events,
    reset_for_tests,
)
from app.hosted_worker import default_lookup, default_runner, poll_once, run_once


@pytest.fixture
def hosted_db(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'hosted.sqlite'}"
    monkeypatch.setenv("HOSTED_DATABASE_URL", url)
    monkeypatch.setenv("HOSTED_BLOB_DIR", str(tmp_path / "blobs"))
    monkeypatch.setenv("HOSTED_BLOB_PROVIDER", "local")
    monkeypatch.setenv("HOSTED_WORKER_TOKEN", "worker-test-token")
    monkeypatch.setenv("HOSTED_AUTH_PROVIDER", "local")
    monkeypatch.setenv("HOSTED_AUTH_DOMAIN", "kannonmfg.com")
    monkeypatch.setenv("HOSTED_AUTH_TENANT_ID", "tenant-kannon")
    monkeypatch.setenv("HOSTED_AUTH_ADMINS", "kyle@kannonmfg.com")
    monkeypatch.setenv("HOSTED_AUTH_USERS", "pat@kannonmfg.com")
    reset_verifier_for_tests()
    reset_for_tests(url)
    yield url
    reset_verifier_for_tests()


@pytest.fixture
def client(hosted_db):
    del hosted_db
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


def _login(client: TestClient, monkeypatch, email: str) -> str:
    monkeypatch.setattr("app.hosted_routes.check_local_password", lambda password: password == "shop")
    response = client.post("/api/hosted/login", json={"email": email, "password": "shop"})
    assert response.status_code == 200, response.text
    return response.json()["token"]


def _submit(client: TestClient, token: str, customer: str = "Acme") -> dict:
    response = client.post(
        "/api/hosted/jobs",
        data={"customer": customer, "scope": "fab-only", "notes": "see pdf", "due_date": "2026-10-01"},
        files=[("files", ("bracket.step", b"ISO-10303-21;", "application/octet-stream"))],
        headers={"X-Hosted-Token": token},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_postgres_claim_sql_skips_locked() -> None:
    assert "FOR UPDATE SKIP LOCKED" in POSTGRES_CLAIM_JOB_SQL


def test_two_claims_one_winner(hosted_db) -> None:
    del hosted_db
    create_job(
        submitted_by="pat@kannonmfg.com",
        customer="Acme",
        scope="full-assembly",
        files=[{"name": "a.step", "blob_key": "k", "size": 3}],
    )
    barrier = threading.Barrier(2)
    results: list = []

    def grab() -> None:
        barrier.wait()
        results.append(claim_next("worker-a"))

    threads = [threading.Thread(target=grab) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    winners = [row for row in results if row is not None]
    assert len(winners) == 1
    assert winners[0]["status"] == "claimed"
    assert claim_next("worker-b") is None


def test_single_flight_blocks_second_queued_job(hosted_db) -> None:
    del hosted_db
    first = create_job(
        submitted_by="pat@kannonmfg.com",
        customer="Acme",
        scope="fab-only",
        files=[{"name": "a.pdf", "blob_key": "a", "size": 1}],
    )
    second = create_job(
        submitted_by="pat@kannonmfg.com",
        customer="Acme",
        scope="fab-only",
        files=[{"name": "b.pdf", "blob_key": "b", "size": 1}],
    )
    claimed = claim_next("box")
    assert claimed is not None
    assert claimed["id"] == first["id"]
    assert claim_next("other") is None
    from app.hosted_queue import mark_loading

    loading = mark_loading(claimed["id"], "box")
    assert loading is not None and loading["status"] == "loading"
    assert claim_next("other") is None
    assert second["status"] == "queued"


def test_stale_requeue_once_then_fail(hosted_db) -> None:
    del hosted_db
    job = create_job(
        submitted_by="pat@kannonmfg.com",
        customer="Acme",
        scope="fab-only",
        files=[{"name": "a.dxf", "blob_key": "a", "size": 1}],
    )
    start = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)
    claimed = claim_next("box", now=start, stale_after_s=90)
    assert claimed is not None
    again = claim_next("box", now=start + timedelta(seconds=120), stale_after_s=90)
    assert again is not None
    assert again["id"] == job["id"]
    assert again["requeues"] == 1
    assert again["status"] == "claimed"
    missed = claim_next("box", now=start + timedelta(seconds=400), stale_after_s=90)
    assert missed is None
    from app.hosted_queue import get_job

    failed = get_job(job["id"])
    assert failed is not None
    assert failed["status"] == "failed"
    assert failed["error"] == "stale_heartbeat"
    notes = [row["note"] for row in list_events(job["id"])]
    assert "requeue_once" in notes
    assert "stale_heartbeat" in notes


def test_stale_with_quote_does_not_requeue(hosted_db) -> None:
    del hosted_db
    job = create_job(
        submitted_by="pat@kannonmfg.com",
        customer="Acme",
        scope="fab-only",
        files=[{"name": "a.zip", "blob_key": "a", "size": 1}],
    )
    start = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)
    claimed = claim_next("box", now=start)
    assert claimed is not None
    with hosted_engine().begin() as conn:
        conn.execute(
            text("UPDATE hosted_jobs SET sectura_quote_id = :quote WHERE id = :id"),
            {"quote": "quote-1", "id": job["id"]},
        )
    assert claim_next("box", now=start + timedelta(seconds=200), stale_after_s=90) is None
    from app.hosted_queue import get_job

    failed = get_job(job["id"])
    assert failed is not None
    assert failed["status"] == "failed"
    assert failed["error"] == "existing_sectura_quote"


def test_run_once_skips_push_when_lookup_finds_quote(hosted_db) -> None:
    del hosted_db
    create_job(
        submitted_by="pat@kannonmfg.com",
        customer="Acme",
        scope="fab-only",
        files=[{"name": "a.stp", "blob_key": "a", "size": 1}],
    )
    pushed: list = []
    result = run_once(runner=lambda job: pushed.append(job) or {"status": "done"}, lookup=lambda job: True)
    assert pushed == []
    assert result is not None
    assert result["status"] == "failed"
    assert result["error"] == "existing_sectura_quote"
    assert default_lookup({}) is False
    with pytest.raises(RuntimeError, match="hosted_runner_not_configured"):
        default_runner({})


def test_weld_labor_forces_qc_flag(hosted_db) -> None:
    del hosted_db
    create_job(
        submitted_by="pat@kannonmfg.com",
        customer="Acme",
        scope="full-assembly",
        files=[{"name": "a.step", "blob_key": "a", "size": 1}],
    )
    result = run_once(
        runner=lambda job: {
            "status": "done",
            "sectura_quote_number": "Q9",
            "qc_report": {"flags": ["Weld labor on A-1"]},
        }
    )
    assert result is not None
    assert result["status"] == "qc_flagged"
    assert result["sectura_quote_number"] == "Q9"
    assert "weld labor" in result["qc_report"]["flags"][0].lower()


def test_auth_rejects_wrong_tenant_domain_and_outsider(monkeypatch) -> None:
    monkeypatch.setenv("HOSTED_AUTH_PROVIDER", "entra")
    monkeypatch.setenv("HOSTED_AUTH_DOMAIN", "kannonmfg.com")
    monkeypatch.setenv("HOSTED_AUTH_TENANT_ID", "tenant-kannon")
    monkeypatch.setenv("HOSTED_AUTH_ADMINS", "kyle@kannonmfg.com")
    monkeypatch.setenv("HOSTED_AUTH_USERS", "pat@kannonmfg.com")
    with pytest.raises(Exception) as missing:
        authorize_claims({"email": "sam@kannonmfg.com", "tid": "tenant-kannon"})
    assert missing.value.code == "not_allow_listed"
    with pytest.raises(Exception) as domain:
        authorize_claims({"email": "pat@example.com", "tid": "tenant-kannon"})
    assert domain.value.code == "wrong_domain"
    with pytest.raises(Exception) as tenant:
        authorize_claims({"email": "pat@kannonmfg.com", "tid": "other-tenant"})
    assert tenant.value.code == "wrong_tenant"
    monkeypatch.setenv("HOSTED_AUTH_TENANT_ID", "")
    with pytest.raises(Exception) as unset:
        authorize_claims({"email": "pat@kannonmfg.com", "tid": ""})
    assert unset.value.code == "tenant_not_configured"
    allowed = authorize_claims({"email": "kyle@kannonmfg.com", "tid": "tenant-kannon"}, provider="local")
    assert allowed.role == "admin"


def test_callback_fail_closed_without_verifier(client, monkeypatch) -> None:
    monkeypatch.setenv("HOSTED_AUTH_PROVIDER", "entra")
    response = client.post("/api/hosted/auth/callback", json={"id_token": "unsigned"})
    assert response.status_code == 403
    assert response.json()["detail"] == "verifier_not_configured"


def test_callback_rejects_wrong_tenant(client, monkeypatch) -> None:
    monkeypatch.setenv("HOSTED_AUTH_PROVIDER", "clerk")
    set_verifier_for_tests(lambda token: {"email": "pat@kannonmfg.com", "tid": "other"})
    response = client.post("/api/hosted/auth/callback", json={"id_token": "signed"})
    assert response.status_code == 403
    assert response.json()["detail"] == "wrong_tenant"


def test_user_visibility_audit_and_worker(client, monkeypatch) -> None:
    kyle = _login(client, monkeypatch, "kyle@kannonmfg.com")
    pat = _login(client, monkeypatch, "pat@kannonmfg.com")
    outsider = client.post(
        "/api/hosted/login",
        json={"email": "sam@kannonmfg.com", "password": "shop"},
    )
    assert outsider.status_code == 403
    assert outsider.json()["detail"] == "not_allow_listed"
    job = _submit(client, pat, "Pat Co")
    events = list_events(job["id"])
    assert events[0]["to_status"] == "queued"
    assert events[0]["actor"] == "pat@kannonmfg.com"
    mine = client.get("/api/hosted/jobs", headers={"X-Hosted-Token": pat})
    assert mine.status_code == 200
    assert [row["id"] for row in mine.json()] == [job["id"]]
    kyle_jobs = client.get("/api/hosted/jobs", headers={"X-Hosted-Token": kyle})
    assert kyle_jobs.json() == []
    everyone = client.get("/api/hosted/jobs?scope=all", headers={"X-Hosted-Token": pat})
    assert everyone.json()[0]["submitted_by"] == "pat@kannonmfg.com"
    admin_view = client.get(f"/api/hosted/jobs/{job['id']}", headers={"X-Hosted-Token": kyle})
    assert admin_view.status_code == 200
    stranger_token = _login_as_second_user(client, monkeypatch)
    hidden = client.get(f"/api/hosted/jobs/{job['id']}", headers={"X-Hosted-Token": stranger_token})
    assert hidden.status_code == 404
    denied = client.post(f"/api/hosted/jobs/{job['id']}/cancel", headers={"X-Hosted-Token": "nope"})
    assert denied.status_code == 401
    forbidden = client.post(
        f"/api/hosted/jobs/{job['id']}/cancel",
        headers={"X-Hosted-Token": stranger_token},
    )
    assert forbidden.status_code == 403
    bad_file = client.post(
        "/api/hosted/jobs",
        data={"customer": "Acme", "scope": "fab-only"},
        files=[("files", ("notes.txt", b"nope", "text/plain"))],
        headers={"X-Hosted-Token": pat},
    )
    assert bad_file.status_code == 400
    assert bad_file.json()["detail"] == "bad_file_type"
    no_worker = client.post("/api/hosted/worker/claim")
    assert no_worker.status_code == 401
    claimed = client.post(
        "/api/hosted/worker/claim",
        headers={"X-Worker-Token": "worker-test-token"},
    )
    assert claimed.status_code == 200
    assert claimed.json()["job"]["id"] == job["id"]
    claim_events = list_events(job["id"])
    assert claim_events[-1]["actor"] == "box-worker"
    assert claim_events[-1]["to_status"] == "claimed"
    second = client.post(
        "/api/hosted/worker/claim",
        headers={"X-Worker-Token": "worker-test-token"},
    )
    assert second.json()["job"] is None


def _login_as_second_user(client: TestClient, monkeypatch) -> str:
    monkeypatch.setenv("HOSTED_AUTH_USERS", "pat@kannonmfg.com,sam@kannonmfg.com")
    return _login(client, monkeypatch, "sam@kannonmfg.com")


def test_password_login_disabled_for_entra(client, monkeypatch) -> None:
    monkeypatch.setenv("HOSTED_AUTH_PROVIDER", "entra")
    response = client.post(
        "/api/hosted/login",
        json={"email": "kyle@kannonmfg.com", "password": "shop"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "password_login_disabled"


def test_vercel_blob_is_not_called(monkeypatch) -> None:
    monkeypatch.delenv("BLOB_READ_WRITE_TOKEN", raising=False)
    store = VercelBlobStore()
    with pytest.raises(Exception, match="BLOB_READ_WRITE_TOKEN"):
        store.put("a.step", b"abc")
    monkeypatch.setenv("BLOB_READ_WRITE_TOKEN", "present-but-unused")
    with pytest.raises(Exception, match="vercel_blob_not_called"):
        store.put("a.step", b"abc")


def test_poll_once_completes_over_http(monkeypatch) -> None:
    calls: list[str] = []

    class _Resp:
        def __init__(self, payload: dict) -> None:
            self._raw = json.dumps(payload).encode("utf-8")

        def read(self) -> bytes:
            return self._raw

        def __enter__(self):
            return self

        def __exit__(self, *args) -> bool:
            return False

    def urlopen(req, timeout=30):
        del timeout
        calls.append(req.full_url)
        if req.full_url.endswith("/claim"):
            return _Resp({"job": {"id": "job-1", "sectura_quote_id": "", "sectura_quote_number": ""}})
        if req.full_url.endswith("/loading"):
            return _Resp({"id": "job-1", "status": "loading"})
        if "complete?job_id=job-1" in req.full_url:
            body = json.loads(req.data.decode("utf-8"))
            assert body["sectura_quote_number"] == "Q1"
            assert body["qc_report"]["flags"] == ["Weld labor on A-1"]
            return _Resp({"id": "job-1", "status": "qc_flagged"})
        raise AssertionError(req.full_url)

    monkeypatch.setattr("app.hosted_worker.urllib.request.urlopen", urlopen)
    result = poll_once(
        "https://queue.example",
        "tok",
        runner=lambda job: {
            "status": "done",
            "sectura_quote_number": "Q1",
            "qc_report": {"flags": ["Weld labor on A-1"]},
        },
    )
    assert result is not None and result["status"] == "qc_flagged"
    assert any(url.endswith("/api/hosted/worker/claim") for url in calls)
