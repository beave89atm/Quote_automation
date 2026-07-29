# Quote automation — Kannon standalone app (weld-first)

Team web app for drawing drop → weld takeoff → weld/fit-up times → human review.

SecturaFAB client code remains in `secturafab/` for a later integration phase.

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

1. Drag/drop a **PDF** (required) and optional **STP/STEP**
2. App extracts weld sizes + estimates lengths (STP when present)
3. Review inches by size, efficiency %, flags
4. Recalculate → Accept or Needs info
5. Export printable HTML or JSON

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## SecturaFAB (paused)

```powershell
.\.venv\Scripts\python.exe -m secturafab auth-check
```

Credentials live in `.env` (see `.env.example`).
