"""Printable shop-labor quote and fail-clear SecturaFAB without keys."""

from __future__ import annotations

import importlib
import io
import os
import sys
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.quote_html import render_quote_html
from secturafab.config import SecturaFabConfig

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


@pytest.fixture()
def quote_client(tmp_path):
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
def quote_token(quote_client: TestClient) -> str | None:
    from app.paths import RATES_PATH
    from quote_core.config import load_shop_rates

    rates = load_shop_rates(RATES_PATH)
    password = rates.shared_password or ""
    if not password:
        return None
    res = quote_client.post("/api/login", json={"password": password})
    assert res.status_code == 200
    return str(res.json()["token"])


def _headers(token: str | None) -> dict[str, str]:
    return {"X-App-Token": token} if token else {}


def test_render_quote_html_includes_labor_not_raw_dump():
    html = render_quote_html(
        {
            "id": 7,
            "title": "28106-1 Lower Boom",
            "status": "accepted",
            "efficiency_pct": 85,
            "pdf_filename": "28106-1.pdf",
            "created_at": "2026-08-20T12:00:00+00:00",
            "takeoff": {
                "items": [
                    {
                        "size": "1/4",
                        "inches": 60,
                        "joint_notes": "both sides",
                        "confidence": "high",
                    }
                ]
            },
            "times": {
                "by_size": [
                    {"size": "1/4", "inches": 60, "ipm": 3.5, "weld_minutes": 17.14}
                ],
                "total_inches": 60,
                "weld_minutes": 17.14,
                "quoted_no_fixture_hours": 0.5,
                "quoted_with_fixture_hours": 0.4,
                "quoted_no_fixture_labor": 47.5,
                "quoted_with_fixture_labor": 38.0,
                "fitup_no_fixture_minutes": 6,
                "fitup_with_fixture_minutes": 4,
                "labor_rate_per_hour": 95.0,
                "labor_placeholder": True,
            },
            "flags": ["Review cover plate"],
        }
    )
    assert "28106-1 Lower Boom" in html
    assert "$47.50" in html
    assert "$38.00" in html
    assert "Kannon Manufacturing" in html
    assert "placeholder" in html.lower()
    assert "Laser cutting" in html
    assert "<pre" not in html
    assert "takeoff_json" not in html


def test_secturafab_public_status_hides_secrets():
    empty = SecturaFabConfig(client_id="", client_secret="", username="", password="")
    status = empty.public_status()
    assert status["configured"] is False
    assert "SECTURAFAB_CLIENT_ID" in status["message"]
    assert "secret" not in status["message"].lower() or "CLIENT_SECRET" in status["message"]

    ready = SecturaFabConfig(client_id="id", client_secret="super-secret")
    ready_status = ready.public_status()
    assert ready_status["configured"] is True
    assert "super-secret" not in str(ready_status)


def test_export_html_after_recalculate(quote_client: TestClient, quote_token: str | None):
    headers = _headers(quote_token)
    files = {"pdf": ("boom.pdf", io.BytesIO(b"%PDF-quote"), "application/pdf")}
    with patch("app.main.process_job"):
        created = quote_client.post("/api/jobs", files=files, headers=headers)
    assert created.status_code == 200, created.text
    job_id = created.json()["id"]

    from app.db import Job, SessionLocal

    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        assert job
        job.status = "review"
        db.commit()
    finally:
        db.close()

    patched = quote_client.patch(
        f"/api/jobs/{job_id}",
        headers=headers,
        json={
            "items": [
                {
                    "size": "1/4",
                    "inches": 210,
                    "joint_notes": "manual",
                    "confidence": "high",
                    "source": "manual",
                }
            ],
            "efficiency_pct": 100,
            "fitup_drivers": {
                "part_count": 1,
                "joint_count": 1,
                "assembly_weight_lb": 25,
            },
            "status": "accepted",
        },
    )
    assert patched.status_code == 200, patched.text
    body = patched.json()
    assert body["status"] == "accepted"
    times = body["times"]
    assert times["quoted_with_fixture_labor"] > 0
    assert times["labor_rate_per_hour"] == 95.0

    html = quote_client.get(
        f"/api/jobs/{job_id}/export.html",
        headers=headers,
    )
    assert html.status_code == 200, html.text
    assert "Kannon Manufacturing" in html.text
    assert "$" in html.text
    assert "<pre" not in html.text
    assert body["title"] in html.text


def test_push_without_credentials_is_rejected(
    quote_client: TestClient, quote_token: str | None
):
    headers = _headers(quote_token)
    files = {"pdf": ("need-keys.pdf", io.BytesIO(b"%PDF-k"), "application/pdf")}
    with patch("app.main.process_job"):
        created = quote_client.post("/api/jobs", files=files, headers=headers)
    job_id = created.json()["id"]

    from app.db import Job, SessionLocal

    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        assert job
        job.status = "review"
        db.commit()
    finally:
        db.close()

    empty = SecturaFabConfig(client_id="", client_secret="", username="", password="")
    with patch("secturafab.config.SecturaFabConfig.from_env", return_value=empty):
        res = quote_client.post(
            f"/api/jobs/{job_id}/push-secturafab",
            headers=headers,
        )
        assert res.status_code == 400, res.text
        assert "SECTURAFAB_CLIENT_ID" in res.text

        batch = quote_client.post(
            "/api/jobs/batch-push",
            headers=headers,
            json={"job_ids": [job_id]},
        )
    assert batch.status_code == 200, batch.text
    body = batch.json()
    assert body["queued_count"] == 0
    assert body["rejected"]
    assert "SECTURAFAB_CLIENT_ID" in body["rejected"][0]["reason"]
