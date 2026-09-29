# Hosted front door

The team drops quotes on a hosted site. Nobody on the team signs in to SecturaFAB. The shop box worker is the only process that holds the AI.Agent Sectura session. It polls outbound. Nothing on the internet dials into the box.

This document is the provisioning checklist. Do not create the Vercel project, Neon database, or blob store until that checklist is approved. No secret values belong in git. Names only.

## What is real in this build

- Jobs table, audit rows, and single-flight claim. SQLite `BEGIN IMMEDIATE` is what tests run. Postgres uses `SELECT ... FOR UPDATE SKIP LOCKED` plus a lock on the `hosted_flight` row so only one job is loading.
- Allow-list, email domain, and tenant checks.
- Local blob storage for dev. Uploads are STEP, STP, PDF, DXF, and zip.
- Worker poll client (`python -m app.hosted_worker`) and stale-heartbeat rules: requeue once, then fail. A stored Sectura quote id or number fails the job instead of pushing again.
- Weld-labor text in `qc_report.flags` forces status `qc_flagged`. The app does not invent a weld rate or minutes.

## What is stubbed until provisioning

- Entra, Auth.js, and Clerk signature checks fail closed (`verifier_not_configured`). This build does not fetch JWKS and does not call those providers.
- `HOSTED_BLOB_PROVIDER=vercel` refuses the upload (`BLOB_READ_WRITE_TOKEN is not set`, or `vercel_blob_not_called` if the token name is present). It does not call Vercel Blob.
- `HOSTED_DATABASE_URL` empty uses SQLite under `data/hosted.sqlite`. Neon is not provisioned.
- The worker's default runner raises `hosted_runner_not_configured` and makes no Sectura call. The box process supplies the existing push path when it is started there.
- Local shop password login at `POST /api/login` is unchanged for the existing app.

## Architecture

1. Browser → Vercel (static UI + API). Sign-in is Entra ID for `kannonmfg.com`, plus an allow-list. `admin` sees every job. `user` sees own jobs and can open all jobs read-only.
2. Upload → blob. One row in Postgres: id, submitted_by, submitted_at, customer, due date, notes, scope (`fab-only` or `full-assembly`), files, status, claimed_by_worker, heartbeat_at, attempts, requeues, sectura quote number and id, qc_report, error.
3. Every status change writes `hosted_job_events` with the actor.
4. Box worker, outbound only, polls `POST /api/hosted/worker/claim` with `X-Worker-Token`, heartbeats, runs the existing push and QC, then `POST /api/hosted/worker/complete`.

Statuses: `queued`, `claimed`, `loading`, `qc_flagged`, `done`, `failed`, `cancelled`.

Switching the sign-in provider is `HOSTED_AUTH_PROVIDER` (`local`, `entra`, `authjs`, `clerk`). Non-local providers share the same allow-list and tenant gate.

## Provisioning checklist (needs approval)

Do these in order. Stop if a step is not approved.

1. Vercel project for this repo. Production branch is the hosted-queue branch after review, not an automatic deploy from this draft. Framework: the existing Vite frontend. API: the FastAPI app needs a Python host (Vercel Python or a separate API service). Set `VITE_API_BASE` to that API origin at build time if the UI and API are different hosts. Leave it empty when they share a host.
2. Environment variables on that project (values entered in the host, never in git). See the name list below.
3. Neon Postgres via the Vercel Marketplace. Put the connection string in `HOSTED_DATABASE_URL`. The app creates `hosted_jobs`, `hosted_job_events`, `hosted_flight`, and `hosted_sessions` on first use.
4. Vercel Blob store. Set `HOSTED_BLOB_PROVIDER=vercel` and `BLOB_READ_WRITE_TOKEN`. Until the blob client is wired, uploads stay on local disk and the vercel provider fails closed.
5. Entra app registration in the Kannon tenant (domain `kannonmfg.com`):
   - Redirect URI: the value of `HOSTED_ENTRA_REDIRECT_URI` (the hosted `/queue` callback URL you choose at registration time).
   - Platform: web. ID tokens. Scopes `openid`, `profile`, `email`.
   - Copy the tenant id into `HOSTED_AUTH_TENANT_ID` and `HOSTED_ENTRA_TENANT_ID`.
   - Copy the application id into `HOSTED_ENTRA_CLIENT_ID`.
   - Optional JWKS URL name: `HOSTED_ENTRA_JWKS_URL`. This build does not fetch it.
6. Allow-list: `HOSTED_AUTH_ADMINS` (Kyle) and `HOSTED_AUTH_USERS` (the rest of the team). Comma-separated emails. Anyone else, a wrong domain, or a wrong tenant id is rejected.
7. Worker token: generate a long random value, store it as `HOSTED_WORKER_TOKEN` on the API and on the box. Same value both places. Do not send it to the browser.
8. Box: set `HOSTED_API_BASE` to the hosted API origin. Keep the existing Sectura names the box already uses. Do not open an inbound port or tunnel.

## Secret names

Values stay in the host and on the box.

Hosted front door:

- `HOSTED_DATABASE_URL`
- `BLOB_READ_WRITE_TOKEN`
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

Non-secret config (still do not invent values in git): `HOSTED_AUTH_PROVIDER`, `HOSTED_AUTH_DOMAIN`, `HOSTED_BLOB_PROVIDER`, `HOSTED_BLOB_DIR`, `HOSTED_WORKER_POLL_S`, `VITE_API_BASE`.

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

## Cost tier (estimate, not a quote)

Low volume, a handful of people:

- Vercel Pro, about $20 per user per month.
- Neon Launch, about $0–19 per month.
- Blob storage, usage priced, small at this volume.
- Entra ID for the Kannon Microsoft 365 tenant, no extra app fee for this registration.
- Box worker, no new host.

Rough band: about $20–50 per month until volume grows. Confirm current prices before purchasing.

## Local dev

`HOSTED_AUTH_PROVIDER=local` (the default) keeps a password form on `/queue`. The password is the existing shop shared password. The email must still be on the allow-list. An empty shared password does not sign anyone in.

```powershell
$env:HOSTED_AUTH_ADMINS = "kyle@kannonmfg.com"
$env:HOSTED_AUTH_USERS = "pat@kannonmfg.com"
$env:HOSTED_WORKER_TOKEN = "<local-only token>"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/queue`. Jobs land in `data/hosted.sqlite`. Files land in `data/hosted-blobs`. Both sit under `data/`, which is gitignored.

The existing Upload / Jobs screens still use `POST /api/login` and `X-App-Token`.

## Box worker runbook

On the shop box, after the API is up and the token is set:

```powershell
$env:HOSTED_API_BASE = "https://<approved-api-host>"
$env:HOSTED_WORKER_TOKEN = "<same value as the API>"
$env:HOSTED_WORKER_POLL_S = "5"
.\.venv\Scripts\python.exe -m app.hosted_worker
```

The process sleeps at least one second between polls. It claims one job, marks it loading, refuses a second push when a quote id is already stored, runs QC, and writes the quote number and flags. A dead heartbeat returns the job to `queued` once. The next stale heartbeat marks it `failed`. It does not claim a second job while one is `claimed` or `loading`.

Wire the existing `secturafab` push into the worker on the box before relying on it for live quotes. The copy in this repo will not push until that runner is passed. Do not start a second worker against the same token if both can sign in as AI.Agent; the queue lock allows only one loading job, and Sectura still has a single agent session.
