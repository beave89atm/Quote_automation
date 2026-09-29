"""Free-tier host adapter: schedule, storage, retention, slim Cloudflare app."""

from __future__ import annotations

import asyncio
import io
import json
from datetime import datetime, timedelta, timezone
from email.message import Message
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import urllib.error
from fastapi.testclient import TestClient

from app.hosted_asgi import build_hosted_app, run_asgi
from app.hosted_platform import (
    always_on_cu_hours,
    busy_workweek_cu_hours,
    decide_poll,
    empty_backoff,
    empty_workweek_cu_hours,
    in_active_hours,
    platform_name,
    seconds_until_active,
    suggested_storage,
)
from app.hosted_queue import (
    BlobNotProvisioned,
    LocalBlobStore,
    blob_store,
    cancel_job,
    claim_next,
    complete_job,
    create_job,
    get_job,
    list_events,
    mark_loading,
    purge_expired_files,
    queue_pending,
    reset_for_tests,
    reset_queue_cache,
)
from app.hosted_storage import R2Store, SharePointStore, reset_sharepoint_cache
from app.hosted_worker import poll_tick

CHI = ZoneInfo("America/Chicago")


@pytest.fixture
def hosted_db(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'hosted.sqlite'}"
    monkeypatch.setenv("HOSTED_DATABASE_URL", url)
    monkeypatch.setenv("HOSTED_BLOB_DIR", str(tmp_path / "blobs"))
    monkeypatch.setenv("HOSTED_BLOB_PROVIDER", "local")
    monkeypatch.setenv("HOSTED_FILE_RETENTION_DAYS", "30")
    reset_for_tests(url)
    return tmp_path


def test_cu_hours_stay_inside_the_free_cap() -> None:
    assert round(always_on_cu_hours()) == 182
    assert always_on_cu_hours() > 100
    assert round(busy_workweek_cu_hours()) == 65
    assert busy_workweek_cu_hours() < 100
    assert round(empty_workweek_cu_hours()) == 22
    assert 15 < empty_workweek_cu_hours() < 30


def test_active_hours_and_backoff(monkeypatch) -> None:
    monkeypatch.delenv("HOSTED_WORKER_ACTIVE_HOURS", raising=False)
    monkeypatch.delenv("HOSTED_WORKER_TIMEZONE", raising=False)
    monkeypatch.delenv("HOSTED_WORKER_EMPTY_BACKOFF_S", raising=False)
    monkeypatch.delenv("HOSTED_WORKER_EMPTY_BACKOFF_MAX_S", raising=False)
    monkeypatch.delenv("HOSTED_WORKER_OFFHOURS_POLL_S", raising=False)
    monday_open = datetime(2026, 9, 28, 6, 0, tzinfo=CHI)
    monday_before = datetime(2026, 9, 28, 5, 59, tzinfo=CHI)
    friday_open = datetime(2026, 9, 25, 17, 59, tzinfo=CHI)
    friday_close = datetime(2026, 9, 25, 18, 0, tzinfo=CHI)
    friday_evening = datetime(2026, 9, 25, 19, 0, tzinfo=CHI)
    assert in_active_hours(monday_open) is True
    assert in_active_hours(monday_before) is False
    assert in_active_hours(friday_open) is True
    assert in_active_hours(friday_close) is False
    monday_next = datetime(2026, 9, 28, 6, 0, tzinfo=CHI)
    assert seconds_until_active(friday_evening) == (monday_next - friday_evening).total_seconds()
    assert empty_backoff(1) == 15
    assert empty_backoff(2) == 30
    assert empty_backoff(3) == 60
    assert empty_backoff(20) == 900
    assert empty_backoff(20) > 300
    closed = decide_poll(friday_evening, empty_streak=4, purged_day=None)
    assert closed["contact"] is False
    assert closed["purge"] is False
    assert float(closed["sleep_before"]) > 3600
    monkeypatch.setenv("HOSTED_WORKER_OFFHOURS_POLL_S", "120")
    slow = decide_poll(friday_evening, empty_streak=0, purged_day=None)
    assert slow["contact"] is True
    assert slow["purge"] is False
    assert slow["sleep_before"] == 120
    opened = decide_poll(monday_open, empty_streak=0, purged_day=None)
    assert opened["contact"] is True
    assert opened["purge"] is True
    assert opened["sleep_before"] == 0
    assert opened["fast_s"] == 5
    again = decide_poll(monday_open, empty_streak=1, purged_day=monday_open.date())
    assert again["purge"] is False
    assert again["sleep_before"] == 15


def test_offhours_does_not_call_the_api(monkeypatch) -> None:
    monkeypatch.setenv("HOSTED_WORKER_OFFHOURS_POLL_S", "0")

    def urlopen(req, timeout=30):
        del req, timeout
        raise AssertionError("api called")

    monkeypatch.setattr("app.hosted_worker.urllib.request.urlopen", urlopen)
    slept: list[float] = []
    moment = datetime(2026, 9, 25, 19, 0, tzinfo=CHI)
    streak, purged = poll_tick(
        "https://queue.example",
        "tok",
        moment=moment,
        streak=3,
        purged_day=None,
        sleeper=slept.append,
    )
    assert streak == 0
    assert purged is None
    assert slept and slept[0] > 3600


def test_empty_pending_skips_claim_and_purges_once(monkeypatch) -> None:
    urls: list[str] = []

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
        urls.append(req.full_url)
        if req.full_url.endswith("/pending"):
            return _Resp({"pending": False, "cached": False})
        if req.full_url.endswith("/purge"):
            return _Resp({"purged": 0})
        raise AssertionError(req.full_url)

    monkeypatch.setattr("app.hosted_worker.urllib.request.urlopen", urlopen)
    moment = datetime(2026, 9, 28, 6, 0, tzinfo=CHI)
    slept: list[float] = []
    streak, purged = poll_tick(
        "https://queue.example",
        "tok",
        moment=moment,
        streak=0,
        purged_day=None,
        sleeper=slept.append,
    )
    assert streak == 1
    assert purged == moment.date()
    assert urls == [
        "https://queue.example/api/hosted/worker/purge",
        "https://queue.example/api/hosted/worker/pending",
    ]
    assert slept == []
    urls.clear()
    streak, purged = poll_tick(
        "https://queue.example",
        "tok",
        moment=moment,
        streak=1,
        purged_day=purged,
        sleeper=slept.append,
    )
    assert streak == 2
    assert urls == ["https://queue.example/api/hosted/worker/pending"]
    assert slept == [15]


def test_empty_cache_skips_the_second_query(monkeypatch) -> None:
    reset_queue_cache()
    calls = {"n": 0}

    def fake() -> bool:
        calls["n"] += 1
        return False

    monkeypatch.setattr("app.hosted_queue._queued_row_exists", fake)
    assert queue_pending() == (False, False)
    assert queue_pending() == (False, True)
    assert calls["n"] == 1
    reset_queue_cache()

    def pending() -> bool:
        calls["n"] += 1
        return True

    calls["n"] = 0
    monkeypatch.setattr("app.hosted_queue._queued_row_exists", pending)
    assert queue_pending() == (True, False)
    assert queue_pending() == (True, False)
    assert calls["n"] == 2
    reset_queue_cache()


def test_busy_claim_does_not_cache_empty(hosted_db) -> None:
    del hosted_db
    first = create_job(submitted_by="a@kannonmfg.com", customer="Acme", scope="fab-only", files=[{"name": "a.step"}])
    assert claim_next("box-worker")["id"] == first["id"]
    create_job(submitted_by="a@kannonmfg.com", customer="Acme", scope="fab-only", files=[{"name": "b.step"}])
    assert claim_next("box-worker") is None
    pending, cached = queue_pending()
    assert pending is True
    assert cached is False


def test_retention_purges_only_old_terminal_files(hosted_db) -> None:
    root = hosted_db
    store = blob_store()
    old_file = store.put("old.step", b"ISO-10303-21;")
    recent_file = store.put("new.step", b"ISO-10303-21;")
    queued_file = store.put("wait.step", b"ISO-10303-21;")
    old_job = create_job(
        submitted_by="a@kannonmfg.com", customer="Acme", scope="fab-only", files=[old_file]
    )
    assert claim_next("box-worker")["id"] == old_job["id"]
    assert mark_loading(old_job["id"], "box-worker") is not None
    finished = complete_job(
        old_job["id"],
        "box-worker",
        status="done",
        now=datetime.now(timezone.utc) - timedelta(days=31),
    )
    assert finished is not None and finished["finished_at"]
    recent = create_job(
        submitted_by="a@kannonmfg.com", customer="Acme", scope="fab-only", files=[recent_file]
    )
    assert claim_next("box-worker")["id"] == recent["id"]
    assert mark_loading(recent["id"], "box-worker") is not None
    assert complete_job(
        recent["id"],
        "box-worker",
        status="done",
        now=datetime.now(timezone.utc) - timedelta(days=1),
    )
    queued = create_job(
        submitted_by="a@kannonmfg.com", customer="Acme", scope="fab-only", files=[queued_file]
    )
    assert purge_expired_files() == {"purged": 1}
    assert get_job(old_job["id"])["files"] == []
    assert get_job(recent["id"])["files"]
    assert get_job(queued["id"])["files"]
    assert not (root / "blobs" / old_file["blob_key"]).is_file()
    assert (root / "blobs" / recent_file["blob_key"]).is_file()
    assert "files_purged" in [row["note"] for row in list_events(old_job["id"])]
    cancelled = create_job(
        submitted_by="a@kannonmfg.com", customer="Acme", scope="fab-only", files=[queued_file]
    )
    assert cancel_job(cancelled["id"], "a@kannonmfg.com")["finished_at"]


def test_retention_keeps_files_when_delete_fails_or_disabled(hosted_db, monkeypatch) -> None:
    store = blob_store()
    saved = store.put("old.step", b"ISO-10303-21;")
    job = create_job(submitted_by="a@kannonmfg.com", customer="Acme", scope="fab-only", files=[saved])
    assert claim_next("box-worker")["id"] == job["id"]
    assert mark_loading(job["id"], "box-worker") is not None
    complete_job(job["id"], "box-worker", status="failed", now=datetime.now(timezone.utc) - timedelta(days=40))

    def boom(self, blob_key: str, *, url: str = "") -> None:
        del self, blob_key, url
        raise OSError("disk")

    monkeypatch.setattr(LocalBlobStore, "delete", boom)
    assert purge_expired_files()["purged"] == 0
    assert get_job(job["id"])["files"]
    monkeypatch.setenv("HOSTED_FILE_RETENTION_DAYS", "0")
    assert purge_expired_files() == {"purged": 0}
    assert get_job(job["id"])["files"]


def test_unknown_provider_fails_closed_and_platform_does_not_switch_dev_storage(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HOSTED_BLOB_DIR", str(tmp_path / "blobs"))
    monkeypatch.setenv("HOSTED_BLOB_PROVIDER", "s3")
    with pytest.raises(BlobNotProvisioned, match="unknown_blob_provider"):
        blob_store()
    monkeypatch.delenv("HOSTED_BLOB_PROVIDER", raising=False)
    monkeypatch.setenv("HOSTED_PLATFORM", "cloudflare")
    assert platform_name() == "cloudflare"
    assert suggested_storage() == "r2"
    assert isinstance(blob_store(), LocalBlobStore)
    monkeypatch.setenv("HOSTED_PLATFORM", "vercel")
    assert suggested_storage() == "vercel"
    monkeypatch.setenv("HOSTED_BLOB_PROVIDER", "sharepoint")
    assert suggested_storage() == "sharepoint"


def test_r2_put_signs_without_leaking_the_secret(monkeypatch) -> None:
    monkeypatch.setenv("R2_ACCOUNT_ID", "account-1")
    monkeypatch.setenv("R2_BUCKET", "quote-bucket")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "access-key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "super-secret-value")
    seen: list[dict] = []

    class _Resp:
        def read(self) -> bytes:
            return b""

        def __enter__(self):
            return self

        def __exit__(self, *args) -> bool:
            return False

    def urlopen(req, timeout=60):
        del timeout
        headers = {key.lower(): value for key, value in req.header_items()}
        seen.append({"url": req.full_url, "method": req.method, "headers": headers})
        return _Resp()

    monkeypatch.setattr("app.hosted_storage.urllib.request.urlopen", urlopen)
    stored = R2Store().put("a.step", b"ISO-10303-21;")
    assert stored["url"].startswith("https://account-1.r2.cloudflarestorage.com/quote-bucket/")
    assert "super-secret-value" not in stored["url"]
    auth = seen[0]["headers"]["authorization"]
    assert auth.startswith("AWS4-HMAC-SHA256 ")
    assert "access-key" in auth
    assert "super-secret-value" not in auth
    assert seen[0]["headers"]["x-amz-content-sha256"] == "UNSIGNED-PAYLOAD"
    assert seen[0]["method"] == "PUT"
    monkeypatch.delenv("R2_BUCKET", raising=False)
    with pytest.raises(BlobNotProvisioned, match="r2_not_configured") as exc:
        R2Store().put("a.step", b"abc")
    assert "super-secret-value" not in str(exc.value)


def test_sharepoint_put_uses_graph_and_hides_the_secret(monkeypatch) -> None:
    reset_sharepoint_cache()
    monkeypatch.setenv("HOSTED_AUTH_TENANT_ID", "tenant-kannon")
    monkeypatch.setenv("HOSTED_ENTRA_TENANT_ID", "tenant-kannon")
    monkeypatch.setenv("HOSTED_ENTRA_CLIENT_ID", "client-id")
    monkeypatch.setenv("HOSTED_ENTRA_CLIENT_SECRET", "graph-secret-value")
    monkeypatch.setenv("HOSTED_SHAREPOINT_DRIVE_ID", "drive-1")
    monkeypatch.delenv("HOSTED_SHAREPOINT_FOLDER", raising=False)
    seen: list[dict] = []

    class _Resp:
        def __init__(self, raw: bytes) -> None:
            self._raw = raw

        def read(self) -> bytes:
            return self._raw

        def __enter__(self):
            return self

        def __exit__(self, *args) -> bool:
            return False

    def urlopen(req, timeout=60):
        del timeout
        headers = {key.lower(): value for key, value in req.header_items()}
        body = req.data.decode("utf-8") if req.data else ""
        seen.append({"url": req.full_url, "method": req.method, "headers": headers, "body": body})
        if "oauth2/v2.0/token" in req.full_url:
            assert "graph-secret-value" in body
            return _Resp(b'{"access_token":"graph-token","expires_in":3600}')
        return _Resp(b"{}")

    monkeypatch.setattr("app.hosted_storage.urllib.request.urlopen", urlopen)
    stored = SharePointStore().put("a.step", b"ISO-10303-21;")
    assert "graph.microsoft.com" in stored["url"]
    assert "/drives/drive-1/root:/" in stored["url"]
    assert "QuoteQueue" in stored["url"]
    assert stored["url"].endswith(":/content")
    assert "graph-secret-value" not in stored["url"]
    assert seen[0]["method"] == "POST"
    assert seen[1]["method"] == "PUT"
    assert seen[1]["headers"]["authorization"] == "Bearer graph-token"
    reset_sharepoint_cache()

    def reject(req, timeout=60):
        del timeout
        raise urllib.error.HTTPError(
            req.full_url,
            401,
            "unauthorized",
            Message(),
            io.BytesIO(b"graph-secret-value"),
        )

    monkeypatch.setattr("app.hosted_storage.urllib.request.urlopen", reject)
    with pytest.raises(BlobNotProvisioned, match="graph_http_401") as exc:
        SharePointStore().put("a.step", b"ISO-10303-21;")
    assert "graph-secret-value" not in str(exc.value)
    monkeypatch.delenv("HOSTED_SHAREPOINT_DRIVE_ID", raising=False)
    with pytest.raises(BlobNotProvisioned, match="sharepoint_not_configured") as missing:
        SharePointStore().put("a.step", b"abc")
    assert "graph-secret-value" not in str(missing.value)


def test_slim_app_serves_hosted_routes_without_the_full_app() -> None:
    app = build_hosted_app()
    paths = app.openapi()["paths"]
    assert "/api/hosted/jobs" in paths
    assert "/api/health" in paths
    status, _headers, body = asyncio.run(
        run_asgi(app, method="GET", url="https://quote.example/api/health", headers=[], body=b"")
    )
    assert status == 200
    payload = json.loads(body)
    assert payload["status"] == "ok"
    assert payload["platform"] in {"vercel", "cloudflare"}
    with TestClient(app) as client:
        platform = client.get("/api/hosted/platform")
        assert platform.status_code == 200
        assert "suggested_storage" in platform.json()
    worker = Path("cloudflare/worker.py").read_text(encoding="utf-8")
    assert "app.main" not in worker
    assert "def on_fetch" in worker
    assert "from workers import Response" in worker
    wrangler = Path("wrangler.toml").read_text(encoding="utf-8")
    assert "python_workers" in wrangler
    assert 'directory = "./frontend/dist"' in wrangler
    assert '"/api/*"' in wrangler
    assert "TOKEN" not in wrangler
    assert "SECRET" not in wrangler
