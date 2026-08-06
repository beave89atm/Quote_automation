"""Tests for CreateFile transient retry behavior."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from secturafab.client import SecturaFabApiError
from secturafab.push import (
    SecturaFabPushService,
    is_transient_secturafab_error,
)


def test_is_transient_provider_failed():
    exc = SecturaFabApiError(
        "API request failed (500)",
        status_code=500,
        body={
            "ExceptionMessage": "The underlying provider failed on Open.",
            "ExceptionType": "System.Data.Entity.Core.EntityException",
        },
    )
    assert is_transient_secturafab_error(exc)


def test_is_transient_any_5xx():
    assert is_transient_secturafab_error(
        SecturaFabApiError("boom", status_code=503, body="Service Unavailable")
    )


def test_non_transient_auth_4xx():
    assert not is_transient_secturafab_error(
        SecturaFabApiError("unauthorized", status_code=401, body="Unauthorized")
    )
    assert not is_transient_secturafab_error(
        SecturaFabApiError("bad request", status_code=400, body="Invalid")
    )


def test_createfile_retries_then_succeeds(tmp_path: Path):
    pdf = tmp_path / "assy.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    client = MagicMock()
    fail = SecturaFabApiError(
        "API request failed (500)",
        status_code=500,
        body={"ExceptionMessage": "The underlying provider failed on Open."},
    )
    client.post_multipart.side_effect = [fail, fail, "qr-uuid-ok"]
    service = SecturaFabPushService(client=client)
    sleeps: list[float] = []
    progress: list[dict] = []

    qr = service.upload_drawings_quote_request(
        [pdf],
        on_progress=progress.append,
        sleep_fn=sleeps.append,
        retry_interval_s=1.0,
        retry_max_s=60.0,
    )
    assert qr == "qr-uuid-ok"
    assert client.post_multipart.call_count == 3
    assert sleeps == [1.0, 1.0]
    assert any(p.get("status") == "retrying_createfile" for p in progress)
    assert progress[-1].get("status") == "pushing"


def test_createfile_non_transient_fails_immediately(tmp_path: Path):
    pdf = tmp_path / "assy.pdf"
    pdf.write_bytes(b"%PDF")
    client = MagicMock()
    client.post_multipart.side_effect = SecturaFabApiError(
        "bad", status_code=400, body="Invalid org"
    )
    service = SecturaFabPushService(client=client)
    with pytest.raises(SecturaFabApiError):
        service.upload_drawings_quote_request(
            [pdf],
            sleep_fn=lambda _s: None,
            retry_interval_s=1.0,
            retry_max_s=60.0,
        )
    assert client.post_multipart.call_count == 1


def test_createfile_gives_up_after_max(tmp_path: Path):
    pdf = tmp_path / "assy.pdf"
    pdf.write_bytes(b"%PDF")
    client = MagicMock()
    fail = SecturaFabApiError(
        "API request failed (500)",
        status_code=500,
        body={"ExceptionMessage": "The underlying provider failed on Open."},
    )
    client.post_multipart.side_effect = fail
    service = SecturaFabPushService(client=client)
    # First attempt fails immediately; elapsed already >= max → no sleep retry.
    with pytest.raises(SecturaFabApiError, match="still failing"):
        service.upload_drawings_quote_request(
            [pdf],
            sleep_fn=lambda _s: None,
            retry_interval_s=1.0,
            retry_max_s=0.0,
        )
