# Hosted front door

The team drops quotes on a hosted site. Nobody on the team signs in to SecturaFAB. The shop box worker is the only process that holds the AI.Agent Sectura session. It polls outbound. Nothing on the internet dials into the box.

Testing stays on free tiers. Moving to a paid plan later is a settings change: the same code, the same env var names. This document is the provisioning checklist. Do not create the Vercel project, Cloudflare project, Neon database, R2 bucket, or blob store until that checklist is approved. No secret values belong in git. Names only.

## What is real in this build

- Jobs table, audit rows, and single-flight claim. SQLite `BEGIN IMMEDIATE` is what tests run. Postgres uses `SELECT ... FOR UPDATE SKIP LOCKED` plus a lock on the `hosted_flight` row so only one job is loading.
- Allow-list, email domain, and tenant checks. Entra ID tokens are checked against the tenant JWKS (signature, issuer, audience, expiry) when the client id and tenant are set.
- File storage selected by `HOSTED_BLOB_PROVIDER`: `local` (dev), `vercel` (private Blob), `r2` (Cloudflare R2 over the S3 API), `sharepoint` (Microsoft Graph into an existing SharePoint or OneDrive folder). Any other value fails closed. Leaving the variable unset stays on local files, including when `HOSTED_PLATFORM=cloudflare`.
- Retention deletes uploaded files N days after a job reaches `done`, `qc_flagged`, `failed`, or `cancelled`. `HOSTED_FILE_RETENTION_DAYS` defaults to 30. `0` turns retention off. A failed delete leaves that job's file list in place.
- Worker poll client (`python -m app.hosted_worker`) and stale-heartbeat rules: requeue once, then fail. Before a push, a stored quote id or a Sectura search by QuoteNumber or Description fails the job instead of pushing again. The runner then calls the existing STEP, Image Files, or Long path and runs QC.
- Weld-labor text in `qc_report.flags` forces status `qc_flagged`. The app does not invent a weld rate or minutes.

## What still needs a host, not new code

- `HOSTED_DATABASE_URL` empty uses SQLite under `data/hosted.sqlite`. On a host set it to Neon with the pure-Python driver: `postgresql+pg8000://...`. The app does not rewrite the URL. The serverless disk does not keep SQLite.
- Auth.js and Clerk still fail closed (`verifier_not_configured`). Entra is the provider that verifies tokens. Switching to Auth.js or Clerk is still a config name, not a second verifier.
- The box worker is a process on the shop PC. It is not a Vercel function or a Cloudflare worker. Chrome and the Sectura session cannot run inside the serverless function.
- Local shop password login at `POST /api/login` is unchanged for the existing app.

## One codebase, two hosts

`HOSTED_PLATFORM` is `vercel` or `cloudflare`. It tells the health and platform endpoints which host is in use. It does not fork the UI or the hosted routes.

The browser calls relative `/api` URLs. `VITE_API_BASE` stays empty when the UI and API share a host.

- Vercel Hobby: `vercel.json` sets `"framework": null`. Static UI is `frontend/dist`. `api/index.py` exports the full FastAPI app from `app.main` for `/api/*`. `maxDuration` is 10 so Hobby accepts the function. In the project settings, leave the framework as Other. Do not pick the FastAPI preset. That preset routes `/` through Python and drops the static UI. The function imports the full app, including PDF libraries. If the deploy rejects the bundle size, the fallback is a second project for the API only, with `VITE_API_BASE` pointed at it. Do not do that until the single project fails.
- Cloudflare Workers free: `wrangler.toml` serves `frontend/dist` as assets and runs `cloudflare/worker.py` first for `/api/*`. That entry builds the slim app in `app/hosted_asgi.py` (the hosted router plus `/api/health`). It does not import the full application module, because PyMuPDF does not load on Workers Python. The quoting engine stays on the shop box. `GET /api/hosted/platform` returns `platform` and `suggested_storage` and no secrets. Suggested storage is `vercel` Blob on Vercel and `r2` on Cloudflare unless `HOSTED_BLOB_PROVIDER` is set.

Worker file download is `GET /api/hosted/worker/file` with `X-Worker-Token`. The function reads the private blob with the server credentials and returns the bytes. The box does not hold `BLOB_READ_WRITE_TOKEN`, the R2 secret, or the Graph client secret.

## Architecture

1. Browser → Vercel Hobby or Cloudflare Workers (static UI + API). Sign-in is Entra ID for `kannonmfg.com`, plus an allow-list. `admin` sees every job. `user` sees own jobs and can open all jobs read-only.
2. Upload → the selected store. One row in Postgres: id, submitted_by, submitted_at, customer, due date, notes, scope (`fab-only` or `full-assembly`), files, status, claimed_by_worker, heartbeat_at, attempts, requeues, sectura quote number and id, qc_report, error, finished_at.
3. Every status change writes `hosted_job_events` with the actor. Purging files writes a `files_purged` note.
4. Box worker, outbound only, asks `GET /api/hosted/worker/pending` before it claims. An empty answer does not call `POST /api/hosted/worker/claim`.

Statuses: `queued`, `claimed`, `loading`, `qc_flagged`, `done`, `failed`, `cancelled`.

Switching the sign-in provider is `HOSTED_AUTH_PROVIDER` (`local`, `entra`, `authjs`, `clerk`). Non-local providers share the same allow-list and tenant gate.

## Neon compute

Neon free is 100 CU-hours per project per month. Compute is 0.25 CU and suspends after 5 minutes idle. The numbers below are computed by `always_on_cu_hours`, `busy_workweek_cu_hours`, and `empty_workweek_cu_hours` in `app/hosted_platform.py`.

| Pattern | CU-hours / month | Against the 100 cap |
| --- | --- | --- |
| Poll every few seconds, 24/7 | about 182 | over |
| Mon–Fri 06:00–18:00 America/Chicago, queue busy the whole window (compute stays awake) | about 65 | under, tight |
| Same window, empty queue, backoff capped at 15 minutes (each probe bills about 5 minutes until suspend) | about 22 | under |
| Nights and weekends with `HOSTED_WORKER_OFFHOURS_POLL_S=0` | about 0 | under |

A job left in `loading` with a heartbeat holds compute for the length of that push.

The empty-queue cache (`HOSTED_QUEUE_CACHE_S`, default 60 seconds) lets one API instance answer `pending: false` without a Postgres query. Only a fresh empty flag skips the database. Creating, cancelling, or claiming a job clears it. The cache is in memory, so another serverless isolate can still miss and query. The backoff is what lets Neon suspend. A new job during a quiet stretch waits for the next poll: seconds at the start of the backoff, at most 15 minutes once the cap is reached, and the next weekday morning if it was submitted overnight.

The backoff cap must stay above 5 minutes. A poll every 5 minutes would reset the idle timer and the compute would not suspend. The default cap is 900 seconds.

## $0 checklist A — Vercel Hobby + Neon Free + Blob or SharePoint

Stop if a step is not approved. Enter values in the host, never in git.

1. Vercel Hobby. The Hobby terms are non-commercial; use checklist B if this queue is commercial work. Import this repo. Framework: Other. Do not pick the FastAPI preset. Do not select a paid add-on.
2. Leave `maxDuration` at 10 in `vercel.json`. That is the Hobby limit. Production branch is the hosted-queue branch after review, not an automatic deploy from this draft.
3. Neon Free project. Connection string in `HOSTED_DATABASE_URL`, scheme `postgresql+pg8000://`. The app creates `hosted_jobs`, `hosted_job_events`, `hosted_flight`, and `hosted_sessions` on first use. Autoscaling at the free 0.25 CU is enough for this checklist.
4. Storage, one of:
   - Vercel Blob on the free 1 GB: `HOSTED_BLOB_PROVIDER=vercel` and `BLOB_READ_WRITE_TOKEN`. Uploads use `PUT https://blob.vercel-storage.com` with `x-vercel-blob-access: private`.
   - SharePoint on the existing Microsoft 365 tenant: `HOSTED_BLOB_PROVIDER=sharepoint`, `HOSTED_SHAREPOINT_DRIVE_ID`, `HOSTED_SHAREPOINT_FOLDER` (default `QuoteQueue`), and `HOSTED_ENTRA_CLIENT_SECRET` on the same Entra app. The app asks for an app-only Graph token (`https://graph.microsoft.com/.default`) and uploads with `PUT /drives/{id}/root:/{folder}/{key}:/content`. Grant that app Files access to the drive. The secret stays on the server.
5. `HOSTED_PLATFORM=vercel`. `VITE_API_BASE` empty.
6. Entra app registration in the Kannon tenant (domain `kannonmfg.com`):
   - Redirect URI: the value of `HOSTED_ENTRA_REDIRECT_URI` (the hosted `/queue` URL you choose at registration time).
   - Platform: web. ID tokens. Scopes `openid`, `profile`, `email`.
   - Copy the tenant id into `HOSTED_AUTH_TENANT_ID` and `HOSTED_ENTRA_TENANT_ID`.
   - Copy the application id into `HOSTED_ENTRA_CLIENT_ID`.
   - Optional JWKS URL name: `HOSTED_ENTRA_JWKS_URL`. When it is empty the app uses `https://login.microsoftonline.com/<tenant>/discovery/v2.0/keys`, caches the keys for one hour, and checks RS256, issuer, audience (`HOSTED_ENTRA_CLIENT_ID`), expiry, and tenant. `HOSTED_AUTH_TENANT_ID` and `HOSTED_ENTRA_TENANT_ID` must be the same directory when both are set. A missing client id or tenant fail-closes with `verifier_not_configured` and does not fetch JWKS.
   - Local bypass: `HOSTED_AUTH_DEV=1` enables `POST /api/hosted/auth/dev` only when the request host is `localhost`, `127.0.0.1`, or `::1`. The email still has to pass the domain and allow-list. Leave this unset on the host.
7. Allow-list: `HOSTED_AUTH_ADMINS` (Kyle) and `HOSTED_AUTH_USERS` (the rest of the team). Comma-separated emails. Anyone else, a wrong domain, or a wrong tenant id is rejected.
8. Worker token: generate a long random value, store it as `HOSTED_WORKER_TOKEN` on the API and on the box. Same value both places. Do not send it to the browser.
9. Box: set `HOSTED_API_BASE` to the hosted origin. Keep the worker schedule defaults below. Keep the existing Sectura names the box already uses. Do not open an inbound port or tunnel.

## $0 checklist B — Cloudflare Workers + Neon Free + R2 or SharePoint

Same app. Use this when Hobby's non-commercial term rules Vercel out.

1. Cloudflare account on the free Workers plan. Do not attach a paid workers subscription. This repo already has `wrangler.toml`: assets from `frontend/dist`, worker first for `/api/*`, `python_workers`. Build the UI with `npm ci --prefix frontend && npm run build --prefix frontend` before deploy. Deploy command, when approved: `npx wrangler deploy`. Do not put secrets in `wrangler.toml`. Set them with `npx wrangler secret put NAME` or the dashboard.
2. `HOSTED_PLATFORM=cloudflare`. `VITE_API_BASE` empty so the UI and the worker share the host.
3. Neon Free, same as checklist A. `HOSTED_DATABASE_URL=postgresql+pg8000://...`.
4. Storage, one of:
   - R2 free 10 GB: `HOSTED_BLOB_PROVIDER=r2`, `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`. Optional `R2_ENDPOINT` when the S3 URL is not `https://<account>.r2.cloudflarestorage.com`. The app signs path-style requests (region `auto`, payload `UNSIGNED-PAYLOAD`). The secret is not placed in the URL.
   - SharePoint, same names as checklist A.
5. Entra, allow-list, and worker token: same steps as checklist A. The Graph client secret is required only for SharePoint.
6. Box: `HOSTED_API_BASE` is the workers.dev or custom host. Same schedule defaults.

Workers free has a small CPU budget per request. These routes are JSON, auth, and blob proxy. The quoting engine stays on the box. If a request exceeds the free CPU limit, the paid Workers plan is the switch below.

## Switch to paid (settings only)

No second codebase. Keep the env var names.

- Vercel: in the dashboard, change the project from Hobby to Pro. Optionally set `functions.api/index.py.maxDuration` from 10 to 60 in `vercel.json` if an API call needs longer than the Hobby limit. The push still runs on the box, so 10 seconds is enough for queue calls.
- Neon: in the Neon console, change the project from Free to Launch. Keep the same `HOSTED_DATABASE_URL`.
- Blob or R2: stay on the free store until the quota is gone. The same token or R2 keys work after a plan change.
- Cloudflare Workers: change the Workers plan in the dashboard. Keep `wrangler.toml`.
- SharePoint: stays on the existing Microsoft 365 tenant.

## Secret names

Values stay in the host and on the box.

Hosted front door:

- `HOSTED_DATABASE_URL`
- `BLOB_READ_WRITE_TOKEN`
- `R2_ACCOUNT_ID`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_BUCKET`
- `HOSTED_ENTRA_CLIENT_SECRET`
- `HOSTED_SHAREPOINT_DRIVE_ID`
- `HOSTED_AUTH_TENANT_ID`
- `HOSTED_ENTRA_TENANT_ID`
- `HOSTED_ENTRA_CLIENT_ID`
- `HOSTED_ENTRA_REDIRECT_URI`
- `HOSTED_ENTRA_JWKS_URL`
- `HOSTED_AUTHJS_SIGNIN_URL`
- `HOSTED_CLERK_SIGNIN_URL`
- `HOSTED_WORKER_TOKEN`
- `HOSTED_API_BASE`
- `HOSTED_AUTH_ADMINS`
- `HOSTED_AUTH_USERS`

Non-secret config (still do not invent values in git): `HOSTED_PLATFORM`, `HOSTED_AUTH_PROVIDER`, `HOSTED_AUTH_DOMAIN`, `HOSTED_BLOB_PROVIDER` (`local`, `vercel`, `r2`, `sharepoint`), `HOSTED_BLOB_DIR`, `HOSTED_SHAREPOINT_FOLDER`, `HOSTED_FILE_RETENTION_DAYS`, `R2_ENDPOINT`, `HOSTED_WORKER_POLL_S`, `HOSTED_WORKER_ACTIVE_HOURS`, `HOSTED_WORKER_TIMEZONE`, `HOSTED_WORKER_OFFHOURS_POLL_S`, `HOSTED_WORKER_EMPTY_BACKOFF_S`, `HOSTED_WORKER_EMPTY_BACKOFF_MAX_S`, `HOSTED_QUEUE_CACHE_S`, `VITE_API_BASE`.

Sectura names the box already uses (unchanged, still never committed):

- `SECTURA_WEB_EMAIL`
- `SECTURA_WEB_PASSWORD`
- `SECTURA_WEB_SECRETS_PATH`
- `SECTURA_WEB_CDP_PORT`
- `SECTURA_RELOGIN_COOLDOWN_S`
- `SECTURAFAB_CLIENT_ID`
- `SECTURAFAB_CLIENT_SECRET`
- `SECTURA_WEBSITE_COOKIE`
- `SECTURAFAB_WEBSITE_COOKIE`

## Local dev

`HOSTED_AUTH_PROVIDER=local` (the default) keeps a password form on `/queue`. The password is the existing shop shared password. The email must still be on the allow-list. An empty shared password does not sign anyone in.

```powershell
$env:HOSTED_AUTH_ADMINS = "kyle@kannonmfg.com"
$env:HOSTED_AUTH_USERS = "pat@kannonmfg.com"
$env:HOSTED_WORKER_TOKEN = "<local-only token>"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/queue`. Jobs land in `data/hosted.sqlite`. Files land in `data/hosted-blobs` (`HOSTED_BLOB_PROVIDER` unset or `local`). Both sit under `data/`, which is gitignored.

The existing Upload / Jobs screens still use `POST /api/login` and `X-App-Token`.

## Box worker runbook

On the shop box, after the API is up and the token is set:

```powershell
$env:HOSTED_API_BASE = "https://<approved-api-host>"
$env:HOSTED_WORKER_TOKEN = "<same value as the API>"
$env:HOSTED_WORKER_POLL_S = "5"
$env:HOSTED_WORKER_ACTIVE_HOURS = "Mon-Fri 06:00-18:00"
$env:HOSTED_WORKER_TIMEZONE = "America/Chicago"
$env:HOSTED_WORKER_OFFHOURS_POLL_S = "0"
$env:HOSTED_WORKER_EMPTY_BACKOFF_S = "15"
$env:HOSTED_WORKER_EMPTY_BACKOFF_MAX_S = "900"
.\.venv\Scripts\python.exe -m app.hosted_worker
```

Inside the window, the first check is immediate. After a job is found, the next check waits `HOSTED_WORKER_POLL_S` (default 5). An empty queue waits 15 seconds, then 30, then 60, up to 15 minutes, and does not call claim. Outside the window the default sleeps until the next opening and does not call the API. The first API call of a workday also runs file retention once.

The process claims one job, marks it loading, refuses a second push when a quote id is already stored, runs QC, and writes the quote number and flags. A dead heartbeat returns the job to `queued` once. The next stale heartbeat marks it `failed`. It does not claim a second job while one is `claimed` or `loading`.

The default runner reads the files and picks one existing path. It does not guess.

- One STEP (optional single PDF) whose stock is plate, or whose name is a weldment/assembly/formed plate: page-native STEP (`push_job` with the STEP).
- One PDF and no STEP: Image Files + Long (`push_job` with the PDF only).
- One STEP whose stock is bar or tube and whose file name already classifies as Linear: Long (`push_job` with no STEP, so it is not sent down Cad contours). A bar file whose name does not say it is linear fails `linear_name_missing`.
- Two STEPs, two PDFs, a DXF, a STEP mixed with a DXF, or a plate name on bar stock: `unknown_file_mix` or `ambiguous_step_stock`. Nothing is pushed.

Before the push it refuses a job that already has a quote id or number. It then searches Sectura by QuoteNumber (`GET v1/quote/byName/{number}`) and, when a title block produced a description, by Description on `GET v1/quote`. A hit fails the job with `existing_sectura_quote` and stores the id. A search error fails `sectura_search_failed` and does not push. After a successful push it reads the quote tree and runs the existing QC checker. There is no invented LOM: without `expected_parts` on the job the report stays FLAG (`expected part list missing`). A parent that received a Weld operation from the shop calculator is not flagged for weld labor. A parent with no Weld operation is flagged that the calculator ran and found no weld length. Weld minutes come from the existing takeoff and `shop_rates.yaml`. No weld length is invented.

Do not start a second worker against the same token if both can sign in as AI.Agent; the queue lock allows only one loading job, and Sectura still has a single agent session.
