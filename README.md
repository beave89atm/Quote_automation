# Quote automation — Kannon Manufacturing

Team web app: drop customer drawings (PDF / DXF / STP) → propose operations +
setup/run times from the shop capabilities list → push a quote into
**SecturaFAB** for Kyle to review. Local printable shop-labor HTML is a
fallback only — SecturaFAB is the v1 review surface.

The SecturaFAB client (`secturafab/`) stays in the repo even if the shop later
drops that ERP. No inbox / RFQ email intake.

## Quick start

### 1. Python deps

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
```

### 2. Shop rates

Edit [`config/shop_rates.yaml`](config/shop_rates.yaml) (see [`config/README.md`](config/README.md)):
- Shared app password (default `kannon`)
- Weld IPM by size
- Fit-up factors (with / without fixture)
- Default efficiency %

### 3. Frontend

A ready-to-serve UI lives in [`frontend/dist`](frontend/dist) (vanilla JS). The React/Vite source in [`frontend/src`](frontend/src) is available when Node/npm is installed:

```powershell
cd frontend
npm install
npm run build
```

### 4. Run API (serves UI from `frontend/dist`)

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 — password from `shop_rates.yaml`.

### Dev UI (hot reload)

```powershell
# terminal 1
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

# terminal 2
cd frontend
npm run dev
```

Open http://localhost:5173

## Workflow

1. **Happy path:** drop only the **top-level weldment**. The app searches
   `drawing_library.roots` (typically Fort Worth Engineering\\Customer Drawings)
   and auto-attaches the matching STP plus BOM child PDFs so you do not upload
   each child. Multi-file drop (PDF / DXF / STP, any subset) is for files that
   are **not** already in that library.
2. App proposes operations (laser, bend, weld/fit-up, saw, outsourced tube laser +
   powder coating, …) and setup/run times it can compute. Unknowns and mill/lathe
   are flagged — not invented.
3. Review flags + weld inches, then **Push to SecturaFAB**
4. Kyle reviews the live quote in SecturaFAB (Profile / Weld / memo / ItemList)
5. Printable HTML / JSON remain available as a local fallback

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## SecturaFAB (local keys only)

Push already exists. It needs Kyle’s laptop `.env` — **this cloud VM does not
have production credentials** and must not.

Auth uses **client credentials** per SecturaFAB support:

1. Create/get id + secret at https://secturafab.com/apikey
2. Put them in `.env` as `SECTURAFAB_CLIENT_ID` / `SECTURAFAB_CLIENT_SECRET`
3. Token URL: `https://www.secturafab.com/token` (form body) · API base: `https://api.secturafab.com`  
   Note: bare `https://secturafab.com/token` (no `www`) returns `unsupported_grant_type` in our tests.
4. `GET /api/secturafab/status` reports whether keys are present (never returns the secret)
5. Without keys, push returns **400** with a clear “set SECTURAFAB_CLIENT_ID…” message

```powershell
.\.venv\Scripts\python.exe -m secturafab auth-check
```

See `.env.example`. Capabilities live in [`config/shop_capabilities.yaml`](config/shop_capabilities.yaml)
(from Kyle’s July 2026 equipment list).