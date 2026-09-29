"""Hosted runner, Entra tokens, and the Vercel entry. No live Sectura calls."""

from __future__ import annotations

import json
from pathlib import Path

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jwt.algorithms import RSAAlgorithm

from app.hosted_auth import reset_verifier_for_tests
from app.hosted_queue import reset_for_tests
from app.hosted_runner import (
    SecturaSearchError,
    classify_hosted_files,
    execute_hosted_job,
    expand_zip_files,
    push_selected,
)
from secturafab.push import PushResult
from secturafab.quote_qc import QcReport
from secturafab.step_classify import STOCK_ROUND_BAR, STOCK_STRONG_PLATE


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


def _step(path: Path, name: str) -> Path:
    target = path / name
    target.write_text("ISO-10303-21;", encoding="utf-8")
    return target


def _stock(monkeypatch, kind: str) -> None:
    monkeypatch.setattr(
        "app.hosted_runner.classify_step_file",
        lambda path: {"kind": kind},
    )


def test_classify_paths(tmp_path, monkeypatch) -> None:
    plate = _step(tmp_path, "A-11949-000.step")
    tube = _step(tmp_path, "TUBE-1.step")
    pdf = tmp_path / "drawing.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    dxf = tmp_path / "flat.dxf"
    dxf.write_bytes(b"0")
    _stock(monkeypatch, STOCK_STRONG_PLATE)
    assert classify_hosted_files([plate])[0] == "step_page_native"
    assert classify_hosted_files([plate, pdf])[0] == "step_page_native"
    assert classify_hosted_files([pdf]) == ("pdf_image_files", "")
    assert classify_hosted_files([plate, dxf])[1] == "unknown_file_mix"
    assert classify_hosted_files([dxf])[1] == "unknown_file_mix"
    assert classify_hosted_files([pdf, tmp_path / "b.pdf"])[1] == "unknown_file_mix"
    _stock(monkeypatch, STOCK_ROUND_BAR)
    assert classify_hosted_files([tube]) == ("linear", "")
    assert classify_hosted_files([plate])[1] == "linear_name_missing"
    named_plate = _step(tmp_path, "PLATE-1.step")
    assert classify_hosted_files([named_plate])[1] == "unknown_file_mix"
    _stock(monkeypatch, "other")
    assert classify_hosted_files([plate])[1] == "ambiguous_step_stock"


def test_zip_expands_one_pdf(tmp_path) -> None:
    import zipfile

    pdf = tmp_path / "drawing.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    archive = tmp_path / "pack.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.write(pdf, "drawing.pdf")
    paths, reason = expand_zip_files([archive], tmp_path / "out")
    assert reason == ""
    assert [p.name for p in paths] == ["drawing.pdf"]
    assert classify_hosted_files(paths) == ("pdf_image_files", "")


def test_unknown_mix_does_not_push_or_search(tmp_path) -> None:
    dxf = tmp_path / "flat.dxf"
    dxf.write_bytes(b"0")
    called: list[str] = []
    result = execute_hosted_job(
        {"files": [{"name": "flat.dxf", "local_path": str(dxf)}], "customer": "Acme"},
        search=lambda number, description: called.append("search") or None,
        push=lambda kind, paths, job: called.append("push") or PushResult(ok=True),
    )
    assert result["status"] == "failed"
    assert result["error"] == "unknown_file_mix"
    assert called == []


def test_existing_quote_blocks_push(tmp_path, monkeypatch) -> None:
    step = _step(tmp_path, "A-11949-000.step")
    _stock(monkeypatch, STOCK_STRONG_PLATE)
    pushed: list[str] = []
    result = execute_hosted_job(
        {"files": [{"name": step.name, "local_path": str(step)}], "customer": "Acme"},
        search=lambda number, description: {"id": "quote-9", "number": number or "11949-000"},
        push=lambda kind, paths, job: pushed.append(kind) or PushResult(ok=True),
    )
    assert pushed == []
    assert result["error"] == "existing_sectura_quote"
    assert result["sectura_quote_id"] == "quote-9"


def test_search_failure_does_not_push(tmp_path, monkeypatch) -> None:
    step = _step(tmp_path, "A-11949-000.step")
    _stock(monkeypatch, STOCK_STRONG_PLATE)

    def boom(number: str, description: str) -> None:
        del number, description
        raise SecturaSearchError("sectura_search_failed")

    result = execute_hosted_job(
        {"files": [{"name": step.name, "local_path": str(step)}], "customer": "Acme"},
        search=boom,
        push=lambda kind, paths, job: PushResult(ok=True, quote_id="new"),
    )
    assert result["error"] == "sectura_search_failed"
    assert result["sectura_quote_id"] == ""


def test_push_then_qc_writes_quote_and_weld_flag(tmp_path, monkeypatch) -> None:
    step = _step(tmp_path, "A-11949-000.step")
    _stock(monkeypatch, STOCK_STRONG_PLATE)
    monkeypatch.setattr(
        "secturafab.quote_qc.check_tree",
        lambda tree, parts, **kwargs: QcReport(
            label="Q",
            status="FLAG",
            flags=["ASSY: weld labor not on parent (waiting on Kyle; not guessed)"],
            summary="flagged",
        ),
    )
    seen: dict[str, str] = {}

    def push(kind, paths, job):
        del paths, job
        seen["kind"] = kind
        return PushResult(ok=True, quote_id="qid-1", quote_number="11949-000")

    result = execute_hosted_job(
        {
            "files": [{"name": step.name, "local_path": str(step)}],
            "customer": "Acme",
            "expected_parts": {"PLATE": 1},
        },
        search=lambda number, description: None,
        push=push,
        read_tree=lambda quote_id: {"quote_id": quote_id, "rows": []},
    )
    assert seen["kind"] == "step_page_native"
    assert result["status"] == "qc_flagged"
    assert result["sectura_quote_id"] == "qid-1"
    assert result["sectura_quote_number"] == "11949-000"
    assert result["qc_report"]["tree"]["quote_id"] == "qid-1"
    assert any("weld labor" in flag.lower() for flag in result["qc_report"]["flags"])


def test_selected_push_passes_step_only_for_page_native(tmp_path, monkeypatch) -> None:
    step = _step(tmp_path, "A-11949-000.step")
    captured: dict = {}

    class _Service:
        def push_job(self, **kwargs):
            captured.update(kwargs)
            return PushResult(ok=False, error="stopped")

    monkeypatch.setattr("secturafab.push.SecturaFabPushService", _Service)
    push_selected("step_page_native", [step], {"customer": "Acme"})
    assert captured["stp_path"] == step
    captured.clear()
    tube = _step(tmp_path, "TUBE-1.step")
    push_selected("linear", [tube], {"customer": "Acme"})
    assert captured["stp_path"] is None
    assert captured["title"] == "TUBE-1"
    captured.clear()
    pdf = tmp_path / "only.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    push_selected("pdf_image_files", [pdf], {"customer": "Acme"})
    assert captured["stp_path"] is None
    assert captured["pdf_path"] == pdf


def test_description_search_uses_list_when_number_misses(monkeypatch) -> None:
    from app.hosted_runner import live_search

    class _Response:
        status_code = 200

    class _Client:
        def request(self, method, path, params=None):
            assert method == "GET"
            assert path == "v1/quote"
            return _Response()

        def _parse_or_raise(self, response):
            del response
            return [{"ID": "desc-1", "QuoteNumber": "Q-9", "Description": "WINCH FRAME"}]

    class _Service:
        def __init__(self) -> None:
            self.client = _Client()

        def find_quote_by_number(self, number: str):
            assert number == "11949-000"
            return None

    monkeypatch.setattr("secturafab.push.SecturaFabPushService", _Service)
    hit = live_search("11949-000", "WINCH FRAME")
    assert hit is not None
    assert hit["id"] == "desc-1"
    assert hit["number"] == "Q-9"


def _rsa_token(private_key, claims: dict, *, kid: str = "k1") -> str:
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": kid})


def test_entra_jwks_checks_and_fail_closed(monkeypatch) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
    jwk.update({"kid": "k1", "use": "sig", "alg": "RS256"})
    fetched: list[str] = []

    class _Resp:
        def read(self) -> bytes:
            return json.dumps({"keys": [jwk]}).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *args) -> bool:
            return False

    def urlopen(req, timeout=10):
        del timeout
        fetched.append(req.full_url)
        return _Resp()

    monkeypatch.setattr("app.hosted_auth.urllib.request.urlopen", urlopen)
    reset_verifier_for_tests()
    monkeypatch.setenv("HOSTED_AUTH_PROVIDER", "entra")
    monkeypatch.setenv("HOSTED_AUTH_TENANT_ID", "tenant-kannon")
    monkeypatch.setenv("HOSTED_ENTRA_TENANT_ID", "tenant-kannon")
    monkeypatch.setenv("HOSTED_ENTRA_CLIENT_ID", "client-1")
    monkeypatch.setenv("HOSTED_ENTRA_JWKS_URL", "https://jwks.example/keys")
    monkeypatch.setenv("HOSTED_AUTH_DOMAIN", "kannonmfg.com")
    monkeypatch.setenv("HOSTED_AUTH_USERS", "pat@kannonmfg.com")
    good = {
        "aud": "client-1",
        "iss": "https://login.microsoftonline.com/tenant-kannon/v2.0",
        "tid": "tenant-kannon",
        "exp": 9999999999,
        "preferred_username": "pat@kannonmfg.com",
    }
    from app.hosted_auth import authorize_claims, verify_bearer_claims

    claims = verify_bearer_claims(_rsa_token(private_key, good))
    identity = authorize_claims(claims)
    assert identity.email == "pat@kannonmfg.com"
    assert fetched == ["https://jwks.example/keys"]
    bad_aud = dict(good, aud="other-client")
    with pytest.raises(Exception) as aud:
        verify_bearer_claims(_rsa_token(private_key, bad_aud))
    assert aud.value.code == "wrong_audience"
    expired = dict(good, exp=1)
    with pytest.raises(Exception) as old:
        verify_bearer_claims(_rsa_token(private_key, expired))
    assert old.value.code == "token_expired"
    monkeypatch.setenv("HOSTED_ENTRA_CLIENT_ID", "")
    fetched.clear()
    with pytest.raises(Exception) as missing:
        verify_bearer_claims(_rsa_token(private_key, good))
    assert missing.value.code == "verifier_not_configured"
    assert fetched == []
    reset_verifier_for_tests()


def test_dev_bypass_is_localhost_only(hosted_db, monkeypatch) -> None:
    del hosted_db
    monkeypatch.setenv("HOSTED_AUTH_DEV", "1")
    from app.main import app

    with TestClient(app, base_url="http://testserver") as remote:
        denied = remote.post("/api/hosted/auth/dev", json={"email": "kyle@kannonmfg.com"})
    assert denied.status_code == 403
    assert denied.json()["detail"] == "dev_bypass_disabled"
    with TestClient(app, base_url="http://localhost") as local:
        allowed = local.post("/api/hosted/auth/dev", json={"email": "kyle@kannonmfg.com"})
        outsider = local.post("/api/hosted/auth/dev", json={"email": "sam@kannonmfg.com"})
    assert allowed.status_code == 200
    assert allowed.json()["email"] == "kyle@kannonmfg.com"
    assert outsider.status_code == 403
    assert outsider.json()["detail"] == "not_allow_listed"
    monkeypatch.setenv("HOSTED_AUTH_DEV", "0")
    with TestClient(app, base_url="http://localhost") as local:
        off = local.post("/api/hosted/auth/dev", json={"email": "kyle@kannonmfg.com"})
    assert off.status_code == 403


def test_worker_downloads_local_blob(client, monkeypatch) -> None:
    monkeypatch.setattr("app.hosted_routes.check_local_password", lambda password: password == "shop")
    login = client.post(
        "/api/hosted/login",
        json={"email": "pat@kannonmfg.com", "password": "shop"},
    )
    assert login.status_code == 200
    token = login.json()["token"]
    submitted = client.post(
        "/api/hosted/jobs",
        data={"customer": "Acme", "scope": "fab-only", "notes": "", "due_date": ""},
        files=[("files", ("bracket.step", b"ISO-10303-21;", "application/octet-stream"))],
        headers={"X-Hosted-Token": token},
    )
    assert submitted.status_code == 200, submitted.text
    job = submitted.json()
    key = job["files"][0]["blob_key"]
    downloaded = client.get(
        "/api/hosted/worker/file",
        params={"job_id": job["id"], "key": key},
        headers={"X-Worker-Token": "worker-test-token"},
    )
    assert downloaded.status_code == 200
    assert downloaded.content == b"ISO-10303-21;"
    hidden = client.get(
        "/api/hosted/worker/file",
        params={"job_id": job["id"], "key": "other"},
        headers={"X-Worker-Token": "worker-test-token"},
    )
    assert hidden.status_code == 404


def test_vercel_entrypoint_exports_the_api() -> None:
    import json
    from pathlib import Path

    from api.index import app

    config = json.loads(Path("vercel.json").read_text(encoding="utf-8"))
    assert config["framework"] is None
    assert config["outputDirectory"] == "frontend/dist"
    assert any(row["destination"] == "/api/index" for row in config["rewrites"])
    assert "/api/hosted/jobs" in app.openapi()["paths"]
