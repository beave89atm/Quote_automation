"""Top-level weldment drop must still resolve BOM children + STP from the library."""

from __future__ import annotations

import importlib
import io
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from quote_core.drawing_library import find_drawings

_RELOAD_MODULES = (
    "app.paths",
    "app.db",
    "app.auth",
    "app.library",
    "app.services",
    "app.main",
)


def _reload_app_modules() -> None:
    for mod_name in _RELOAD_MODULES:
        if mod_name in sys.modules:
            importlib.reload(sys.modules[mod_name])
        else:
            importlib.import_module(mod_name)


def _weldment_library(tmp_path: Path) -> Path:
    """Customer Drawings / Time / 21678-1 with assembly + children + STP."""
    folder = tmp_path / "Customer Drawings" / "Time" / "21678-1"
    folder.mkdir(parents=True)
    (folder / "21678-1.pdf").write_bytes(b"%PDF-assembly")
    (folder / "21679.pdf").write_bytes(b"%PDF-tube")
    (folder / "21680.pdf").write_bytes(b"%PDF-plate")
    (folder / "21681-1.pdf").write_bytes(b"%PDF-gusset")
    (folder / "21678-1.stp").write_bytes(b"ISO-10303-21")
    return folder


def test_find_drawings_lists_children_and_stp_from_top_level_key(tmp_path: Path):
    folder = _weldment_library(tmp_path)
    root = tmp_path / "Customer Drawings"
    match = find_drawings("21678-1", [root], primary_pdf_name="21678-1.pdf")
    assert match.folder == folder
    assert match.stp_path is not None
    assert match.stp_path.name == "21678-1.stp"
    child_names = {p.name for p in match.related_pdfs}
    assert child_names == {"21679.pdf", "21680.pdf", "21681-1.pdf"}
    assert "21678-1.pdf" not in child_names


@pytest.fixture()
def library_client(tmp_path: Path):
    data_dir = tmp_path / "data"
    lib_root = tmp_path / "Customer Drawings"
    _weldment_library(tmp_path)
    previous_data = os.environ.get("KANNON_DATA_DIR")
    previous_lib = os.environ.get("KANNON_DRAWING_LIBRARY")
    os.environ["KANNON_DATA_DIR"] = str(data_dir)
    os.environ["KANNON_DRAWING_LIBRARY"] = str(lib_root)
    _reload_app_modules()
    from app.main import app

    with TestClient(app) as c:
        yield c

    if previous_data is None:
        os.environ.pop("KANNON_DATA_DIR", None)
    else:
        os.environ["KANNON_DATA_DIR"] = previous_data
    if previous_lib is None:
        os.environ.pop("KANNON_DRAWING_LIBRARY", None)
    else:
        os.environ["KANNON_DRAWING_LIBRARY"] = previous_lib
    _reload_app_modules()


@pytest.fixture()
def library_token(library_client: TestClient) -> str | None:
    from app.paths import RATES_PATH
    from quote_core.config import load_shop_rates

    rates = load_shop_rates(RATES_PATH)
    password = rates.shared_password or ""
    if not password:
        return None
    res = library_client.post("/api/login", json={"password": password})
    assert res.status_code == 200
    return str(res.json()["token"])


def test_top_level_pdf_only_auto_attaches_library_stp_and_children(
    library_client: TestClient, library_token: str | None, tmp_path: Path
):
    from app.db import Job, SessionLocal
    from app.library import attach_library_stp

    headers = {"X-App-Token": library_token} if library_token else {}
    files = {"pdf": ("21678-1.pdf", io.BytesIO(b"%PDF-top"), "application/pdf")}
    with patch("app.main.process_job"):
        res = library_client.post("/api/jobs", files=files, headers=headers)
    assert res.status_code == 200, res.text
    job_id = res.json()["id"]
    assert not res.json().get("stp_filename")

    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        assert job
        assert job.pdf_filename == "21678-1.pdf"
        assert not job.stp_path
        summary = attach_library_stp(job)
        db.commit()
        db.refresh(job)
    finally:
        db.close()

    assert summary["attached"] is True
    assert summary["stp_filename"] == "21678-1.stp"
    assert summary["related_pdf_count"] == 3
    assert set(summary["related_pdfs"]) == {"21679.pdf", "21680.pdf", "21681-1.pdf"}
    assert job.stp_filename == "21678-1.stp"
    assert job.stp_path and Path(job.stp_path).is_file()
    assert Path(job.stp_path).read_bytes() == b"ISO-10303-21"


def test_process_job_still_runs_library_lookup_before_takeoff(
    library_client: TestClient, library_token: str | None
):
    """Happy path: top-level PDF only → library attach → takeoff sees children."""
    from app.db import Job, SessionLocal
    from app.services import process_job

    headers = {"X-App-Token": library_token} if library_token else {}
    import fitz

    buf = io.BytesIO()
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "21678-1 WELDMENT")
    doc.save(buf)
    doc.close()
    files = {"pdf": ("21678-1.pdf", io.BytesIO(buf.getvalue()), "application/pdf")}
    with patch("app.main.process_job"):
        res = library_client.post("/api/jobs", files=files, headers=headers)
    assert res.status_code == 200
    job_id = res.json()["id"]

    process_job(job_id)

    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        assert job
        takeoff = job.takeoff()
        library = takeoff.get("library") or {}
        assert library.get("attached") is True
        assert library.get("stp_filename") == "21678-1.stp"
        assert library.get("related_pdf_count") == 3
        assert job.stp_filename == "21678-1.stp"
        flags = job.flags()
        assert any("Related drawings in shared folder" in f for f in flags)
        assert any("21679.pdf" in f for f in flags)
    finally:
        db.close()
