"""Outbound box worker. It polls the jobs API. Nothing dials in.

Active hours poll quickly after a job is found. An empty queue backs off so
Neon can suspend. Outside the window the default is to leave the API alone.
The default runner uses the existing push path. Tests inject a fake runner.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from typing import Any, Callable

from .hosted_platform import decide_poll, worker_zone
from .hosted_queue import (
    claim_next,
    complete_job,
    mark_loading,
    sectura_quote_exists,
)

Runner = Callable[[dict[str, Any]], dict[str, Any]]
Lookup = Callable[[dict[str, Any]], bool]


def default_runner(job: dict[str, Any]) -> dict[str, Any]:
    """Existing push path for the files on the job. Tests pass their own runner."""
    from .hosted_runner import execute_hosted_job

    return execute_hosted_job(job)


def default_lookup(job: dict[str, Any]) -> bool:
    """Stored quote ids are handled before this. The runner searches Sectura."""
    del job
    return False


def run_once(
    *,
    worker_id: str = "box-worker",
    runner: Runner | None = None,
    lookup: Lookup | None = None,
) -> dict[str, Any] | None:
    """Claim one job, skip a second push when a quote already exists, write the result."""
    job = claim_next(worker_id)
    if job is None:
        return None
    loading = mark_loading(str(job["id"]), worker_id)
    if loading is None:
        return None
    if sectura_quote_exists(loading, lookup or default_lookup):
        return complete_job(
            str(loading["id"]),
            worker_id,
            status="failed",
            error="existing_sectura_quote",
            sectura_quote_number=str(loading.get("sectura_quote_number") or ""),
            sectura_quote_id=str(loading.get("sectura_quote_id") or ""),
            qc_report=loading.get("qc_report") or {},
        )
    run = runner or default_runner
    try:
        result = run(loading)
    except Exception:
        return complete_job(
            str(loading["id"]),
            worker_id,
            status="failed",
            error="push_failed",
        )
    if not isinstance(result, dict):
        result = {}
    return complete_job(
        str(loading["id"]),
        worker_id,
        status=str(result.get("status") or "done"),
        sectura_quote_number=str(result.get("sectura_quote_number") or ""),
        sectura_quote_id=str(result.get("sectura_quote_id") or ""),
        qc_report=result.get("qc_report") if isinstance(result.get("qc_report"), dict) else {},
        error=str(result.get("error") or ""),
    )


def _request(base: str, path: str, token: str, payload: dict[str, Any] | None, method: str) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        base.rstrip("/") + path,
        data=data,
        method=method,
        headers={
            "X-Worker-Token": token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read()
    if not body:
        return {}
    parsed = json.loads(body.decode("utf-8"))
    return parsed if isinstance(parsed, dict) else {}


def poll_once(base_url: str, token: str, runner: Runner | None = None) -> dict[str, Any] | None:
    """One outbound claim. Raises if the token is rejected. Does not open a port."""
    try:
        claimed = _request(base_url, "/api/hosted/worker/claim", token, {}, "POST")
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise PermissionError("worker_unauthorized") from None
        raise
    job = claimed.get("job")
    if not isinstance(job, dict):
        return None
    job_id = str(job["id"])
    _request(base_url, "/api/hosted/worker/loading", token, {"job_id": job_id}, "POST")
    if sectura_quote_exists(job, default_lookup):
        return _request(
            base_url,
            f"/api/hosted/worker/complete?job_id={job_id}",
            token,
            {"status": "failed", "error": "existing_sectura_quote"},
            "POST",
        )
    run = runner or default_runner
    try:
        result = run(job)
    except Exception:
        result = {"status": "failed", "error": "push_failed"}
    if not isinstance(result, dict):
        result = {"status": "failed", "error": "push_failed"}
    return _request(
        base_url,
        f"/api/hosted/worker/complete?job_id={job_id}",
        token,
        {
            "status": result.get("status") or "done",
            "sectura_quote_number": result.get("sectura_quote_number") or "",
            "sectura_quote_id": result.get("sectura_quote_id") or "",
            "qc_report": result.get("qc_report") or {},
            "error": result.get("error") or "",
        },
        "POST",
    )


def poll_tick(
    base_url: str,
    token: str,
    *,
    moment: datetime,
    streak: int,
    purged_day: date | None,
    sleeper: Callable[[float], None],
    runner: Runner | None = None,
) -> tuple[int, date | None]:
    """One schedule decision. An empty pending response does not claim."""
    decision = decide_poll(moment, empty_streak=streak, purged_day=purged_day)
    sleep_before = float(decision["sleep_before"] or 0)
    if sleep_before > 0:
        sleeper(sleep_before)
    if not decision["contact"]:
        return 0, purged_day
    if decision["purge"]:
        _request(base_url, "/api/hosted/worker/purge", token, {}, "POST")
        purged_day = moment.astimezone(worker_zone()).date()
    pending = _request(base_url, "/api/hosted/worker/pending", token, None, "GET")
    if not pending.get("pending"):
        return streak + 1, purged_day
    result = poll_once(base_url, token, runner)
    if not result:
        return streak + 1, purged_day
    sleeper(float(decision["fast_s"] or 1))
    return 0, purged_day


def main() -> None:
    base = (os.getenv("HOSTED_API_BASE") or "").strip()
    token = (os.getenv("HOSTED_WORKER_TOKEN") or "").strip()
    if not base or not token:
        raise SystemExit("HOSTED_API_BASE and HOSTED_WORKER_TOKEN are required")
    streak = 0
    purged_day: date | None = None
    while True:
        streak, purged_day = poll_tick(
            base,
            token,
            moment=datetime.now(timezone.utc),
            streak=streak,
            purged_day=purged_day,
            sleeper=time.sleep,
        )


if __name__ == "__main__":
    main()
