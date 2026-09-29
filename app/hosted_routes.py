"""Hosted front-door routes. Local /api/login is unchanged."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from .hosted_auth import (
    HOSTED_TOKEN_HEADER,
    AuthRejected,
    Identity,
    auth_config,
    authorize_claims,
    check_local_password,
    dev_bypass_allowed,
    hash_token,
    new_session_token,
    provider_name,
    require_worker,
    verify_bearer_claims,
)
from .hosted_platform import platform_name, suggested_storage
from .hosted_queue import (
    BlobNotProvisioned,
    blob_store,
    get_job as read_job,
    cancel_job,
    claim_next,
    complete_job,
    create_job,
    get_job,
    heartbeat,
    list_jobs,
    mark_loading,
    purge_expired_files,
    queue_pending,
    read_session,
    save_session,
)

router = APIRouter(prefix="/api/hosted")


class LoginBody(BaseModel):
    email: str = ""
    password: str = ""


class CallbackBody(BaseModel):
    id_token: str = ""


class CompleteBody(BaseModel):
    status: str = "done"
    sectura_quote_number: str = ""
    sectura_quote_id: str = ""
    qc_report: dict[str, Any] = Field(default_factory=dict)
    error: str = ""


class HeartbeatBody(BaseModel):
    job_id: str


def require_identity(
    x_hosted_token: str | None = Header(default=None, alias=HOSTED_TOKEN_HEADER),
) -> Identity:
    token = (x_hosted_token or "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="unauthorized")
    row = read_session(hash_token(token))
    if row is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    return Identity(email=row["email"], role=row["role"], tenant=row["tenant"])


def _issue(identity: Identity) -> dict[str, Any]:
    token, digest, expires = new_session_token()
    save_session(digest, identity, expires)
    return {
        "token": token,
        "email": identity.email,
        "role": identity.role,
        "expires_at": expires.isoformat(),
    }


@router.get("/auth/config")
def get_auth_config() -> dict[str, Any]:
    return auth_config()


@router.get("/platform")
def platform_info() -> dict[str, str]:
    return {"platform": platform_name(), "suggested_storage": suggested_storage()}


@router.post("/login")
def hosted_login(body: LoginBody) -> dict[str, Any]:
    if provider_name() != "local":
        raise HTTPException(status_code=400, detail="password_login_disabled")
    if not check_local_password(body.password):
        raise HTTPException(status_code=401, detail="unauthorized")
    try:
        identity = authorize_claims({"email": body.email}, provider="local")
    except AuthRejected as exc:
        raise HTTPException(status_code=403, detail=exc.code) from None
    return _issue(identity)


@router.post("/auth/callback")
def hosted_callback(body: CallbackBody) -> dict[str, Any]:
    if provider_name() == "local":
        raise HTTPException(status_code=400, detail="callback_disabled")
    try:
        claims = verify_bearer_claims(body.id_token)
        identity = authorize_claims(claims)
    except AuthRejected as exc:
        raise HTTPException(status_code=403, detail=exc.code) from None
    return _issue(identity)


@router.post("/auth/dev")
def hosted_dev(body: LoginBody, request: Request) -> dict[str, Any]:
    if not dev_bypass_allowed(request.url.hostname or ""):
        raise HTTPException(status_code=403, detail="dev_bypass_disabled")
    try:
        identity = authorize_claims({"email": body.email}, provider="local")
    except AuthRejected as exc:
        raise HTTPException(status_code=403, detail=exc.code) from None
    return _issue(identity)


@router.get("/me")
def me(identity: Identity = Depends(require_identity)) -> dict[str, str]:
    return {"email": identity.email, "role": identity.role}


@router.post("/jobs")
async def submit_job(
    customer: str = Form(""),
    scope: str = Form(""),
    notes: str = Form(""),
    due_date: str = Form(""),
    files: list[UploadFile] = File(default=[]),
    identity: Identity = Depends(require_identity),
) -> dict[str, Any]:
    store = blob_store()
    stored: list[dict[str, Any]] = []
    try:
        for upload in files:
            data = await upload.read()
            stored.append(store.put(upload.filename or "file", data))
        job = create_job(
            submitted_by=identity.email,
            customer=customer,
            scope=scope,
            files=stored,
            notes=notes,
            due_date=due_date,
        )
    except BlobNotProvisioned as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return job


@router.get("/jobs")
def jobs(
    scope: str = "",
    identity: Identity = Depends(require_identity),
) -> list[dict[str, Any]]:
    if scope == "all":
        return list_jobs()
    return list_jobs(email=identity.email)


@router.get("/jobs/{job_id}")
def job_detail(job_id: str, identity: Identity = Depends(require_identity)) -> dict[str, Any]:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="not_found")
    if identity.role != "admin" and job["submitted_by"] != identity.email:
        raise HTTPException(status_code=404, detail="not_found")
    return job


@router.post("/jobs/{job_id}/cancel")
def cancel(job_id: str, identity: Identity = Depends(require_identity)) -> dict[str, Any]:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="not_found")
    if identity.role != "admin" and job["submitted_by"] != identity.email:
        raise HTTPException(status_code=403, detail="forbidden")
    updated = cancel_job(job_id, identity.email)
    if updated is None:
        raise HTTPException(status_code=409, detail="not_cancellable")
    return updated


@router.get("/worker/file")
def worker_file(
    job_id: str,
    key: str,
    _: str = Depends(require_worker),
) -> Response:
    job = read_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="not_found")
    match = next((item for item in job.get("files") or [] if item.get("blob_key") == key), None)
    if match is None:
        raise HTTPException(status_code=404, detail="not_found")
    try:
        data = blob_store().get(key, url=str(match.get("url") or ""))
    except BlobNotProvisioned as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    name = Path(str(match.get("name") or "file")).name
    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.get("/worker/pending")
def worker_pending(_: str = Depends(require_worker)) -> dict[str, Any]:
    pending, cached = queue_pending()
    return {"pending": pending, "cached": cached}


@router.post("/worker/purge")
def worker_purge(_: str = Depends(require_worker)) -> dict[str, int]:
    return purge_expired_files()


@router.post("/worker/claim")
def worker_claim(_: str = Depends(require_worker)) -> dict[str, Any]:
    job = claim_next("box-worker")
    return {"job": job}


@router.post("/worker/loading")
def worker_loading(body: HeartbeatBody, _: str = Depends(require_worker)) -> dict[str, Any]:
    job = mark_loading(body.job_id, "box-worker")
    if job is None:
        raise HTTPException(status_code=409, detail="not_claimed")
    return job


@router.post("/worker/heartbeat")
def worker_heartbeat(body: HeartbeatBody, _: str = Depends(require_worker)) -> dict[str, Any]:
    job = heartbeat(body.job_id, "box-worker")
    if job is None:
        raise HTTPException(status_code=409, detail="not_claimed")
    return job


@router.post("/worker/complete")
def worker_complete(
    body: CompleteBody,
    job_id: str,
    _: str = Depends(require_worker),
) -> dict[str, Any]:
    try:
        job = complete_job(
            job_id,
            "box-worker",
            status=body.status,
            sectura_quote_number=body.sectura_quote_number,
            sectura_quote_id=body.sectura_quote_id,
            qc_report=body.qc_report,
            error=body.error,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    if job is None:
        raise HTTPException(status_code=409, detail="not_claimed")
    return job
