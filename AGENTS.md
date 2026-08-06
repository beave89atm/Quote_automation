# AGENTS.md

## Purpose

Kannon Quote Automation is a FastAPI + React app for weld-first quoting: PDF (and optional STEP) → weld/BOM takeoff → shop-rate times → human review → optional SecturaFAB push. Core domain logic lives in `quote_core/`; the web API in `app/`; SecturaFAB integration in `secturafab/`; UI in `frontend/`.

## Run locally

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 (password from `config/shop_rates.yaml`).

Dev UI (optional): API on `:8000` with `--reload`, then `cd frontend && npm install && npm run dev` → http://localhost:5173.

SecturaFAB: copy `.env.example` → `.env`, then `.\.venv\Scripts\python.exe -m secturafab auth-check`.

## Verify (only commands that exist)

```powershell
# Full suite
.\.venv\Scripts\python.exe -m pytest -q

# Smoke (fast local regression net)
.\.venv\Scripts\python.exe -m pytest -q tests/test_smoke_api.py tests/test_time_engine.py tests/test_bom_config.py tests/test_secturafab_push.py tests/test_imperial_ops.py

# Frontend when UI changed
cd frontend; npm run build
```

No lint or typecheck scripts are configured (no ruff/mypy/eslint/tsc).

## Architecture boundaries — ask before rewriting

- `secturafab/push.py` push order (CAD import → assembly link → ops → **BOM qty last**). Skipping settles or calling `UpdateItem_Part` on STEP assemblies can wipe `ItemList`.
- `quote_core/weld/takeoff.py`, `quote_core/bom.py`, `bom_config` multi-dash BOM logic.
- `app/db.py` SQLite schema / additive migrations; do not drop or rename columns casually.
- `app/auth.py` in-memory shared-password sessions.
- SPA catch-all at the bottom of `app/main.py` — keep all `/api` routes registered above it.
- Do not delete or overwrite live SecturaFAB customer quotes unless Kyle explicitly asks.

## Conventions

- Backend: FastAPI routes in `app/main.py`; job work in `app/services.py`; domain in `quote_core/`.
- Frontend: React Router under `frontend/src/pages/`; API via `frontend/src/api.js` with `X-App-Token`.
- Auth: `POST /api/login` → `kannon_quote_token`; protect with `Depends(require_auth)`.
- Shop rates: `config/shop_rates.yaml`. SecturaFAB: `.env` / `secturafab/config.py`.
- Quoting behavior: prefer `docs/quoting/*.md` before inventing shortcuts.
- Prefer imperial labels on SecturaFAB line items; do not casually rewrite STEP geometry for units.
- Imperial cleanup must run **last** in finalize (after settle). Delayed CAD can rewrite Descriptions back to `mm X` if skipped on the success path.

## Definition of done

- Smallest diff that solves the request; no drive-by refactors.
- Do not edit files the task does not require.
- Run the smoke verify command above before claiming done; full `pytest -q` when touching core paths; `npm run build` if frontend changed.
- For SecturaFAB push changes: live-verify qty, assembly links, and units when the task touches push.
- After a live push settles, ItemList Descriptions must not contain ` mm X ` / ` mm x ` (shop-visible imperial labels).

## Feature change plan template

Use in Plan mode before building:

```
Change: [describe the one thing]

Constraints:
- Touch only files required for this change
- Preserve all existing behavior not named above
- Match patterns already in the repo
- Include a verify checklist using AGENTS.md commands
- List risks / possible regressions before implementing

Wait for approval before building. After building, run verify and summarize
what changed + what you checked.
```
