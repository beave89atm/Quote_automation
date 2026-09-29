# Hosted front door

The team drops quotes on a hosted site. Nobody on the team signs in to SecturaFAB. The shop box worker is the only process that holds the AI.Agent Sectura session. It polls outbound. Nothing on the internet dials into the box.

This document is the provisioning checklist. Do not create the Vercel project, Neon database, or blob store until that checklist is approved. No secret values belong in git. Names only.

## What is real in this build

- Jobs table, audit rows, and single-flight claim. SQLite `BEGIN IMMEDIATE` is what tests run. Postgres uses `SELECT ... FOR UPDATE SKIP LOCKED` plus a lock on the `hosted_flight` row so only one job is loading.
- Allow-list, email domain, and tenant checks. Entra ID tokens are checked against the tenant JWKS (signature, issuer, audience, expiry) when the client id and tenant are set.
- Local blob storage for dev. `HOSTED_BLOB_PROVIDER=vercel` uploads and downloads private blobs with the server token.
- Worker poll client (`python -m app.hosted_worker`) and stale-heartbeat rules: requeue once, then fail. Before a push, a stored quote id or a Sectura search by QuoteNumber or Description fails the job instead of pushing again. The runner then calls the existing STEP, Image Files, or Long path and runs QC.
- Weld-labor text in `qc_report.flags` forces status `qc_flagged`. The app does not invent a weld rate or minutes.

## What still needs a host, not new code

- `HOSTED_DATABASE_URL` empty uses SQLite under `data/hosted.sqlite`. On Vercel set it to Neon. The serverless disk does not keep SQLite.
- Auth.js and Clerk still fail closed (`verifier_not_configured`). Entra is the provider that verifies tokens. Switching to Auth.js or Clerk is still a config name, not a second verifier.
- The box worker is a process on the shop PC. It is not a Vercel function. Chrome and the Sectura session cannot run inside the serverless function.
- Local shop password login at `POST /api/login` is unchanged for the existing app.

## Deploy shape

One Vercel project, two runtimes. `vercel.json` sets `"framework": null` so the FastAPI preset does not take over the site.

- Static UI: `npm run build` in `frontend/`, output `frontend/dist`. `/queue` rewrites to `index.html` when no file matches.
- API: `api/index.py` exports the FastAPI `app` from `app/main.py`. Rewrites send `/api/*` to that function (`maxDuration` 60). The browser calls the same origin, so `VITE_API_BASE` stays empty.
- In the Vercel project settings, leave the framework as Other. Do not pick the FastAPI preset. That preset routes `/` through Python and drops the static UI.
- The function imports the full app, including PDF libraries. If the deploy rejects the bundle size, the fallback is a second project for the API only, with `VITE_API_BASE` pointed at it. Do not do that until the single project fails.
- Worker file download is `GET /api/hosted/worker/file` with `X-Worker-Token`. The function reads the private blob with the server token and returns the bytes. The box does not hold `BLOB_READ_WRITE_TOKEN`.

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
4. Vercel Blob store, private access. Set `HOSTED_BLOB_PROVIDER=vercel` and `BLOB_READ_WRITE_TOKEN`. Uploads use `PUT https://blob.vercel-storage.com` with `x-vercel-blob-access: private`. The token stays on the server. `HOSTED_BLOB_PROVIDER=local` remains the dev default.
5. Entra app registration in the Kannon tenant (domain `kannonmfg.com`):
   - Redirect URI: the value of `HOSTED_ENTRA_REDIRECT_URI` (the hosted `/queue` callback URL you choose at registration time).
   - Platform: web. ID tokens. Scopes `openid`, `profile`, `email`.
   - Copy the tenant id into `HOSTED_AUTH_TENANT_ID` and `HOSTED_ENTRA_TENANT_ID`.
   - Copy the application id into `HOSTED_ENTRA_CLIENT_ID`.
   - Optional JWKS URL name: `HOSTED_ENTRA_JWKS_URL`. When it is empty the app uses `https://login.microsoftonline.com/<tenant>/discovery/v2.0/keys`, caches the keys for one hour, and checks RS256, issuer, audience (`HOSTED_ENTRA_CLIENT_ID`), expiry, and tenant. `HOSTED_AUTH_TENANT_ID` and `HOSTED_ENTRA_TENANT_ID` must be the same directory when both are set. A missing client id or tenant fail-closes with `verifier_not_configured` and does not fetch JWKS.
   - Local bypass: `HOSTED_AUTH_DEV=1` enables `POST /api/hosted/auth/dev` only when the request host is `localhost`, `127.0.0.1`, or `::1`. The email still has to pass the domain and allow-list. Leave this unset on Vercel.
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

The default runner reads the files and picks one existing path. It does not guess.

- One STEP (optional single PDF) whose stock is plate, or whose name is a weldment/assembly/formed plate: page-native STEP (`push_job` with the STEP).
- One PDF and no STEP: Image Files + Long (`push_job` with the PDF only).
- One STEP whose stock is bar or tube and whose file name already classifies as Linear: Long (`push_job` with no STEP, so it is not sent down Cad contours). A bar file whose name does not say it is linear fails `linear_name_missing`.
- Two STEPs, two PDFs, a DXF, a STEP mixed with a DXF, or a plate name on bar stock: `unknown_file_mix` or `ambiguous_step_stock`. Nothing is pushed.

Before the push it refuses a job that already has a quote id or number. It then searches Sectura by QuoteNumber (`GET v1/quote/byName/{number}`) and, when a title block produced a description, by Description on `GET v1/quote`. A hit fails the job with `existing_sectura_quote` and stores the id. A search error fails `sectura_search_failed` and does not push. After a successful push it reads the quote tree and runs the existing QC checker. There is no invented LOM: without `expected_parts` on the job the report stays FLAG (`expected part list missing`) and still reports weld labor when the tree is missing it. No weld rate is invented.

Do not start a second worker against the same token if both can sign in as AI.Agent; the queue lock allows only one loading job, and Sectura still has a single agent session.
