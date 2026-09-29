"""Hosted quote queue: blob pointer, Postgres/SQLite jobs, single-flight claim.

SQLite ``BEGIN IMMEDIATE`` is the test stand-in for Postgres
``SELECT ... FOR UPDATE SKIP LOCKED`` plus the singleton flight lock.
Neither path claims two jobs, and only one job is loading at a time.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

from .paths import DATA_DIR, ensure_data_dirs

STATUSES = (
    "queued",
    "claimed",
    "loading",
    "qc_flagged",
    "done",
    "failed",
    "cancelled",
)
ACTIVE = ("claimed", "loading")
SCOPES = ("fab-only", "full-assembly")
ALLOWED_SUFFIXES = (".step", ".stp", ".pdf", ".dxf", ".zip")
MAX_UPLOAD_BYTES = 32 * 1024 * 1024

POSTGRES_CLAIM_JOB_SQL = """
SELECT id FROM hosted_jobs
WHERE status = 'queued'
ORDER BY submitted_at ASC, id ASC
FOR UPDATE SKIP LOCKED
LIMIT 1
"""

_engine: Engine | None = None

_SCHEMA = """
CREATE TABLE IF NOT EXISTS hosted_jobs (
    id TEXT PRIMARY KEY,
    submitted_by TEXT NOT NULL,
    submitted_at TEXT NOT NULL,
    customer TEXT NOT NULL,
    due_date TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    scope TEXT NOT NULL,
    files_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL,
    claimed_by_worker TEXT,
    heartbeat_at TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    requeues INTEGER NOT NULL DEFAULT 0,
    sectura_quote_number TEXT NOT NULL DEFAULT '',
    sectura_quote_id TEXT NOT NULL DEFAULT '',
    qc_report_json TEXT NOT NULL DEFAULT '{}',
    error TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS hosted_job_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    at TEXT NOT NULL,
    actor TEXT NOT NULL,
    from_status TEXT NOT NULL DEFAULT '',
    to_status TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS hosted_flight (
    id INTEGER PRIMARY KEY,
    holder TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS hosted_sessions (
    token_hash TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    role TEXT NOT NULL,
    tenant TEXT NOT NULL DEFAULT '',
    expires_at TEXT NOT NULL
);
"""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def database_url() -> str:
    raw = (os.getenv("HOSTED_DATABASE_URL") or "").strip()
    if raw:
        return raw
    ensure_data_dirs()
    return f"sqlite:///{DATA_DIR / 'hosted.sqlite'}"


def reset_for_tests(url: str | None = None) -> Engine:
    global _engine
    if _engine is not None:
        _engine.dispose()
    target = url or database_url()
    kwargs: dict[str, Any] = {}
    if target.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False, "timeout": 5}
    _engine = create_engine(target, **kwargs)
    init_hosted(_engine)
    return _engine


def hosted_engine() -> Engine:
    global _engine
    if _engine is None:
        reset_for_tests()
    assert _engine is not None
    return _engine


def init_hosted(engine: Engine) -> None:
    ddl = _SCHEMA
    if engine.dialect.name == "postgresql":
        ddl = ddl.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    with engine.begin() as conn:
        for statement in ddl.split(";"):
            sql = statement.strip()
            if sql:
                conn.exec_driver_sql(sql)
        conn.execute(
            text("INSERT INTO hosted_flight (id, holder) SELECT 1, '' WHERE NOT EXISTS (SELECT 1 FROM hosted_flight WHERE id = 1)")
        )


def _connect(engine: Engine) -> Connection:
    return engine.connect().execution_options(isolation_level="AUTOCOMMIT")


def _begin(conn: Connection, dialect: str) -> None:
    if dialect == "sqlite":
        conn.exec_driver_sql("BEGIN IMMEDIATE")
    else:
        conn.exec_driver_sql("BEGIN")


def _commit(conn: Connection) -> None:
    conn.exec_driver_sql("COMMIT")


def _rollback(conn: Connection) -> None:
    try:
        conn.exec_driver_sql("ROLLBACK")
    except Exception:
        return


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _parse_time(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _row_to_job(row: Any) -> dict[str, Any]:
    data = dict(row)
    data["files"] = json.loads(data.pop("files_json") or "[]")
    data["qc_report"] = json.loads(data.pop("qc_report_json") or "{}")
    return data


def _fetch(conn: Connection, job_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        text("SELECT * FROM hosted_jobs WHERE id = :id"),
        {"id": job_id},
    ).mappings().first()
    if row is None:
        return None
    return _row_to_job(row)


def _audit(
    conn: Connection,
    job_id: str,
    from_status: str,
    to_status: str,
    actor: str,
    note: str = "",
) -> None:
    conn.execute(
        text(
            """
            INSERT INTO hosted_job_events (job_id, at, actor, from_status, to_status, note)
            VALUES (:job_id, :at, :actor, :from_status, :to_status, :note)
            """
        ),
        {
            "job_id": job_id,
            "at": _iso(_utcnow()),
            "actor": actor,
            "from_status": from_status,
            "to_status": to_status,
            "note": note[:500],
        },
    )


def list_events(job_id: str) -> list[dict[str, Any]]:
    engine = hosted_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, job_id, at, actor, from_status, to_status, note
                FROM hosted_job_events WHERE job_id = :id ORDER BY id
                """
            ),
            {"id": job_id},
        ).mappings().all()
    return [dict(row) for row in rows]


def _reap_stale(conn: Connection, now: datetime, stale_after_s: float) -> None:
    rows = conn.execute(
        text(
            """
            SELECT id, status, heartbeat_at, requeues, sectura_quote_id, sectura_quote_number
            FROM hosted_jobs WHERE status IN ('claimed', 'loading')
            """
        )
    ).mappings().all()
    cutoff = now - timedelta(seconds=stale_after_s)
    for row in rows:
        heartbeat = _parse_time(row["heartbeat_at"])
        if heartbeat is not None and heartbeat >= cutoff:
            continue
        quote = str(row["sectura_quote_id"] or row["sectura_quote_number"] or "").strip()
        requeues = int(row["requeues"] or 0)
        if quote or requeues >= 1:
            reason = "existing_sectura_quote" if quote else "stale_heartbeat"
            conn.execute(
                text(
                    """
                    UPDATE hosted_jobs
                    SET status = 'failed', error = :error,
                        claimed_by_worker = NULL, heartbeat_at = NULL
                    WHERE id = :id AND status IN ('claimed', 'loading')
                    """
                ),
                {"id": row["id"], "error": reason},
            )
            _audit(conn, str(row["id"]), str(row["status"]), "failed", "system", reason)
            continue
        conn.execute(
            text(
                """
                UPDATE hosted_jobs
                SET status = 'queued', requeues = requeues + 1,
                    claimed_by_worker = NULL, heartbeat_at = NULL
                WHERE id = :id AND status IN ('claimed', 'loading')
                """
            ),
            {"id": row["id"]},
        )
        _audit(conn, str(row["id"]), str(row["status"]), "queued", "system", "requeue_once")


def claim_next(
    worker_id: str,
    *,
    now: datetime | None = None,
    stale_after_s: float = 90,
) -> dict[str, Any] | None:
    """Claim exactly one queued job. A live claimed/loading job blocks the rest."""
    engine = hosted_engine()
    moment = now or _utcnow()
    dialect = engine.dialect.name
    conn = _connect(engine)
    try:
        _begin(conn, dialect)
        _reap_stale(conn, moment, stale_after_s)
        if dialect == "postgresql":
            conn.execute(text("SELECT id FROM hosted_flight WHERE id = 1 FOR UPDATE"))
            row = conn.execute(text(POSTGRES_CLAIM_JOB_SQL)).first()
        else:
            conn.execute(
                text("UPDATE hosted_flight SET holder = :worker WHERE id = 1"),
                {"worker": worker_id},
            )
            busy = conn.execute(
                text("SELECT id FROM hosted_jobs WHERE status IN ('claimed', 'loading')")
            ).first()
            if busy:
                _commit(conn)
                return None
            row = conn.execute(
                text(
                    """
                    SELECT id FROM hosted_jobs
                    WHERE status = 'queued'
                    ORDER BY submitted_at ASC, id ASC
                    LIMIT 1
                    """
                )
            ).first()
        if row is None:
            _commit(conn)
            return None
        job_id = str(row[0])
        if dialect == "postgresql":
            busy = conn.execute(
                text("SELECT id FROM hosted_jobs WHERE status IN ('claimed', 'loading')")
            ).first()
            if busy:
                _commit(conn)
                return None
        updated = conn.execute(
            text(
                """
                UPDATE hosted_jobs
                SET status = 'claimed', claimed_by_worker = :worker,
                    heartbeat_at = :heartbeat, attempts = attempts + 1
                WHERE id = :id AND status = 'queued'
                """
            ),
            {"id": job_id, "worker": worker_id, "heartbeat": _iso(moment)},
        )
        job = _fetch(conn, job_id)
        claimed = (
            job is not None
            and job["status"] == "claimed"
            and job["claimed_by_worker"] == worker_id
        )
        if updated.rowcount not in (1, -1) or not claimed:
            _commit(conn)
            return None
        _audit(conn, job_id, "queued", "claimed", worker_id, "claim")
        _commit(conn)
        return job
    except Exception:
        _rollback(conn)
        raise
    finally:
        conn.close()


def get_job(job_id: str) -> dict[str, Any] | None:
    engine = hosted_engine()
    with engine.connect() as conn:
        return _fetch(conn, job_id)


def list_jobs(*, email: str | None = None) -> list[dict[str, Any]]:
    engine = hosted_engine()
    sql = "SELECT * FROM hosted_jobs"
    params: dict[str, Any] = {}
    if email:
        sql += " WHERE submitted_by = :email"
        params["email"] = email
    sql += " ORDER BY submitted_at DESC, id DESC"
    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    return [_row_to_job(row) for row in rows]


def create_job(
    *,
    submitted_by: str,
    customer: str,
    scope: str,
    files: list[dict[str, Any]],
    notes: str = "",
    due_date: str = "",
    now: datetime | None = None,
) -> dict[str, Any]:
    if scope not in SCOPES:
        raise ValueError("bad_scope")
    if not customer.strip():
        raise ValueError("customer_missing")
    if not files:
        raise ValueError("files_missing")
    moment = now or _utcnow()
    job_id = str(uuid.uuid4())
    engine = hosted_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO hosted_jobs (
                    id, submitted_by, submitted_at, customer, due_date, notes, scope,
                    files_json, status, attempts, requeues, sectura_quote_number,
                    sectura_quote_id, qc_report_json, error
                ) VALUES (
                    :id, :submitted_by, :submitted_at, :customer, :due_date, :notes, :scope,
                    :files_json, 'queued', 0, 0, '', '', '{}', ''
                )
                """
            ),
            {
                "id": job_id,
                "submitted_by": submitted_by,
                "submitted_at": _iso(moment),
                "customer": customer.strip(),
                "due_date": due_date.strip(),
                "notes": notes.strip(),
                "scope": scope,
                "files_json": json.dumps(files),
            },
        )
        _audit(conn, job_id, "", "queued", submitted_by, "submit")
    job = get_job(job_id)
    assert job is not None
    return job


def _owned_update(
    job_id: str,
    worker_id: str,
    *,
    sql: str,
    params: dict[str, Any],
    from_status: tuple[str, ...],
    to_status: str,
    note: str,
) -> dict[str, Any] | None:
    engine = hosted_engine()
    conn = _connect(engine)
    try:
        _begin(conn, engine.dialect.name)
        current = _fetch(conn, job_id)
        if current is None:
            _commit(conn)
            return None
        if current["claimed_by_worker"] != worker_id or current["status"] not in from_status:
            _commit(conn)
            return None
        conn.execute(text(sql), params)
        _audit(conn, job_id, str(current["status"]), to_status, worker_id, note)
        job = _fetch(conn, job_id)
        _commit(conn)
        return job
    except Exception:
        _rollback(conn)
        raise
    finally:
        conn.close()


def mark_loading(job_id: str, worker_id: str, *, now: datetime | None = None) -> dict[str, Any] | None:
    moment = _iso(now or _utcnow())
    return _owned_update(
        job_id,
        worker_id,
        sql="""
            UPDATE hosted_jobs
            SET status = 'loading', heartbeat_at = :now
            WHERE id = :id AND claimed_by_worker = :worker AND status = 'claimed'
        """,
        params={"id": job_id, "worker": worker_id, "now": moment},
        from_status=("claimed",),
        to_status="loading",
        note="loading",
    )


def heartbeat(job_id: str, worker_id: str, *, now: datetime | None = None) -> dict[str, Any] | None:
    moment = _iso(now or _utcnow())
    engine = hosted_engine()
    conn = _connect(engine)
    try:
        _begin(conn, engine.dialect.name)
        current = _fetch(conn, job_id)
        if (
            current is None
            or current["claimed_by_worker"] != worker_id
            or current["status"] not in ACTIVE
        ):
            _commit(conn)
            return None
        conn.execute(
            text(
                """
                UPDATE hosted_jobs SET heartbeat_at = :now
                WHERE id = :id AND claimed_by_worker = :worker
                """
            ),
            {"id": job_id, "worker": worker_id, "now": moment},
        )
        job = _fetch(conn, job_id)
        _commit(conn)
        return job
    except Exception:
        _rollback(conn)
        raise
    finally:
        conn.close()


def weld_labor_flagged(qc_report: dict[str, Any] | None) -> bool:
    flags = (qc_report or {}).get("flags") or []
    return any("weld labor" in str(flag).lower() for flag in flags)


def complete_job(
    job_id: str,
    worker_id: str,
    *,
    status: str,
    sectura_quote_number: str = "",
    sectura_quote_id: str = "",
    qc_report: dict[str, Any] | None = None,
    error: str = "",
) -> dict[str, Any] | None:
    report = qc_report or {}
    final = status
    if weld_labor_flagged(report) and final == "done":
        final = "qc_flagged"
    if final not in {"done", "qc_flagged", "failed"}:
        raise ValueError("bad_status")
    engine = hosted_engine()
    conn = _connect(engine)
    try:
        _begin(conn, engine.dialect.name)
        current = _fetch(conn, job_id)
        if (
            current is None
            or current["claimed_by_worker"] != worker_id
            or current["status"] not in ACTIVE
        ):
            _commit(conn)
            return None
        conn.execute(
            text(
                """
                UPDATE hosted_jobs
                SET status = :status,
                    sectura_quote_number = :number,
                    sectura_quote_id = :quote_id,
                    qc_report_json = :report,
                    error = :error,
                    claimed_by_worker = NULL,
                    heartbeat_at = NULL
                WHERE id = :id
                """
            ),
            {
                "id": job_id,
                "status": final,
                "number": sectura_quote_number.strip(),
                "quote_id": sectura_quote_id.strip(),
                "report": json.dumps(report),
                "error": error.strip()[:500],
            },
        )
        _audit(conn, job_id, str(current["status"]), final, worker_id, "complete")
        job = _fetch(conn, job_id)
        _commit(conn)
        return job
    except Exception:
        _rollback(conn)
        raise
    finally:
        conn.close()


def cancel_job(job_id: str, actor: str) -> dict[str, Any] | None:
    engine = hosted_engine()
    conn = _connect(engine)
    try:
        _begin(conn, engine.dialect.name)
        current = _fetch(conn, job_id)
        if current is None or current["status"] not in {"queued", "claimed"}:
            _commit(conn)
            return None
        conn.execute(
            text(
                """
                UPDATE hosted_jobs
                SET status = 'cancelled', claimed_by_worker = NULL, heartbeat_at = NULL
                WHERE id = :id
                """
            ),
            {"id": job_id},
        )
        _audit(conn, job_id, str(current["status"]), "cancelled", actor, "cancel")
        job = _fetch(conn, job_id)
        _commit(conn)
        return job
    except Exception:
        _rollback(conn)
        raise
    finally:
        conn.close()


def save_session(token_hash: str, identity: Any, expires_at: datetime) -> None:
    engine = hosted_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO hosted_sessions (token_hash, email, role, tenant, expires_at)
                VALUES (:token_hash, :email, :role, :tenant, :expires_at)
                """
            ),
            {
                "token_hash": token_hash,
                "email": identity.email,
                "role": identity.role,
                "tenant": identity.tenant,
                "expires_at": _iso(expires_at),
            },
        )


def read_session(token_hash: str, *, now: datetime | None = None) -> dict[str, Any] | None:
    moment = now or _utcnow()
    engine = hosted_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT email, role, tenant, expires_at FROM hosted_sessions WHERE token_hash = :h"),
            {"h": token_hash},
        ).mappings().first()
    if row is None:
        return None
    expires = _parse_time(row["expires_at"])
    if expires is None or expires <= moment:
        return None
    return {"email": row["email"], "role": row["role"], "tenant": row["tenant"]}


class BlobNotProvisioned(Exception):
    pass


class LocalBlobStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, filename: str, data: bytes) -> dict[str, Any]:
        name = Path(filename).name
        suffix = Path(name).suffix.lower()
        if suffix not in ALLOWED_SUFFIXES:
            raise ValueError("bad_file_type")
        if len(data) > MAX_UPLOAD_BYTES:
            raise ValueError("file_too_large")
        key = f"{uuid.uuid4().hex}/{name}"
        path = self.root / key
        if not path.resolve().is_relative_to(self.root.resolve()):
            raise ValueError("bad_file_type")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return {"name": name, "blob_key": key, "size": len(data)}


class VercelBlobStore:
    """Config switch only. This build does not call Vercel Blob."""

    def put(self, filename: str, data: bytes) -> dict[str, Any]:
        del filename, data
        if not (os.getenv("BLOB_READ_WRITE_TOKEN") or "").strip():
            raise BlobNotProvisioned("BLOB_READ_WRITE_TOKEN is not set")
        raise BlobNotProvisioned("vercel_blob_not_called")


def blob_store() -> LocalBlobStore | VercelBlobStore:
    provider = (os.getenv("HOSTED_BLOB_PROVIDER") or "local").strip().lower()
    if provider == "vercel":
        return VercelBlobStore()
    root = Path((os.getenv("HOSTED_BLOB_DIR") or "").strip() or (DATA_DIR / "hosted-blobs"))
    return LocalBlobStore(root)


def sectura_quote_exists(job: dict[str, Any], lookup: Any = None) -> bool:
    """True when a quote is already recorded. The default lookup makes no Sectura call."""
    if str(job.get("sectura_quote_id") or "").strip() or str(job.get("sectura_quote_number") or "").strip():
        return True
    if lookup is None:
        return False
    return bool(lookup(job))
