# BinderPro - Development Guide (Current Branch)

This guide documents the current, unpublished branch state (changes on top of the published branch), including:

- Everything that changed recently
- How to use and extend those changes safely
- The complete environment variable inventory
- All external services and runtime processes that must be configured

If this conflicts with older v1.0 notes, this document is the source of truth.

---

## Table of Contents

1. [Current Branch Changes (Unpublished Delta)](#1-current-branch-changes-unpublished-delta)
2. [How to Build on Top of These Changes](#2-how-to-build-on-top-of-these-changes)
3. [Environment Variables Reference (Complete)](#3-environment-variables-reference-complete)
4. [External Services and Runtime Setup](#4-external-services-and-runtime-setup)

---

## 1. Current Branch Changes (Unpublished Delta)

### 1.1 Executive Summary

| Area | What Changed in This Branch | Why It Matters |
|------|-----------------------------|----------------|
| Binder generation | Moved from request-time generation to queued async generation via ARQ worker + Redis | Faster API response, better reliability under load |
| Runtime stack | Added Redis service and dedicated worker process in Docker Compose and PM2 | Required for queueing, background jobs, and distributed limits |
| Rate limiting | Replaced in-memory token bucket with Redis-backed sliding window limits | Cross-instance consistency and proper retry semantics |
| JWT security | Added `iss`, `aud`, `iat` claims and strict decode validation | Stronger token validation and future SSO compatibility |
| API hardening | Added body size limit middleware, tighter CORS methods/headers, production docs disabled | Reduced attack surface and better production hygiene |
| Observability | Added optional Sentry integration and production JSON logging | Better error visibility and operations debugging |
| Health checks | Added `/api/health/detailed` readiness endpoint | Better monitoring for dependency-level failures |
| Payments | Deterministic checkout idempotency, DB-level dedupe, webhook dedupe, more webhook events | Fewer duplicate charges/records and better auditability |
| Reconciliation | Added periodic Stripe reconciliation cron job in worker | Repairs missed webhooks and data drift automatically |
| CI/testing | Added GitHub Actions CI and comprehensive backend integration tests | Repeatable quality gates before merge/deploy |
| Frontend ops/SEO | Added Nginx SPA container setup, robots/sitemap/llms files, structured data, 404 page | Better production delivery and search/LLM discoverability |

---

### 1.2 Async Binder Generation Pipeline (Major Architecture Change)

Binder generation is now asynchronous.

```
User clicks generate
    |
    v
POST /api/binders/generate
    - validates profile
    - creates binder record with status="queued"
    - enqueues ARQ job (generate_binder_job)
    |
    v
ARQ worker (Redis queue)
    - status -> "generating"
    - runs AI stages + PDF outputs
    - status -> "ready" or "failed"
    - sends success/failure email
```

Current status lifecycle:

- `queued`
- `generating`
- `ready`
- `failed`

New status endpoint:

- `GET /api/binders/status/{binder_id}`

Additional protection added:

- Per-user generation cap: max 3 binders per hour

Impact for future frontend work:

- Do not assume binder is ready immediately after `POST /api/binders/generate`
- Poll status and only load sections/download links after `ready`

---

### 1.3 Worker and Queue Additions

New worker entrypoint:

- `backend/app/worker.py`

New async tasks:

- `backend/app/tasks/generate_binder.py`
- `backend/app/tasks/reconcile_payments.py`

Worker behavior:

- Uses MongoDB + Redis at startup
- Processes binder generation jobs
- Runs Stripe reconciliation cron at 00:15, 06:15, 12:15, 18:15 UTC
- `max_jobs=4`, `job_timeout=600` seconds

---

### 1.4 Security and Middleware Hardening

#### JWT hardening

Access and refresh tokens now include:

- `iss`
- `aud`
- `iat`

Protected routes now decode with issuer/audience validation (not just signature/exp), including profile routes, binder downloads, feedback token parsing, and refresh/logout flows.

Defaults:

- `JWT_ISSUER=binderpro`
- `JWT_AUDIENCE=binderpro`

#### Body size limiting

New middleware:

- `BodySizeLimitMiddleware` rejects requests over 512 KB by `Content-Length` with HTTP 413.

#### Rate limiting

Rate limiting moved to Redis sliding-window implementation:

- Auth endpoints: 5 requests / 60s
- Generation endpoint: 2 requests / 60s
- General API: 60 requests / 60s

429 responses now include:

- `Retry-After` header
- JSON `retry_after` field

Redis outage behavior:

- Fail-open (requests continue, error is logged)

#### CORS tightening

CORS now allows only:

- Methods: `GET, POST, PUT, DELETE, OPTIONS`
- Headers: `Authorization, Content-Type, X-Requested-With`

#### API docs in production

Interactive docs are disabled when `ENVIRONMENT=production`:

- `/docs`
- `/redoc`
- `/openapi.json`

---

### 1.5 Observability and Health

#### Logging

- Development: standard text logs
- Production: JSON-structured logs

#### Sentry

Optional Sentry initialization was added.

- Enabled only when `SENTRY_DSN` is set
- FastAPI + Starlette integrations
- `traces_sample_rate=0.1`
- `send_default_pii=False`

#### Health endpoints

- `GET /api/health`: liveness (Mongo ping)
- `GET /api/health/detailed`: readiness checks for:
  - MongoDB
  - Redis
  - ARQ pool presence
  - Stripe key configured
  - Resend key configured
  - Disk free space in `DATA_DIR`

---

### 1.6 Payments Reliability and Reconciliation

#### Checkout idempotency changed

Checkout idempotency keys are now deterministic by:

- user_id + tier + calendar day

Effect:

- Same-day retries deduplicate correctly
- New session can still be created next day

#### DB-level dedupe

`payments.stripe_session_id` now has a unique sparse index.

#### Webhook dedupe

Webhook handler checks existing `stripe_session_id` before insert.

#### Additional webhook events handled

- `checkout.session.completed`
- `checkout.session.expired`
- `payment_intent.payment_failed`

#### Reconciliation job

Periodic job scans recent Stripe completed sessions and repairs missing local records.

---

### 1.7 Runtime and Deployment Changes

#### Docker Compose

Added services:

- `redis`
- `worker`

Backend now depends on Redis and initializes ARQ pool.

Frontend container now:

- builds static assets
- serves via Nginx
- proxies `/api` to backend

Added healthchecks (March 2026):

- `mongo` healthcheck: `mongosh --eval "db.runCommand({ ping: 1 })"` — 10s interval, 5 retries, 20s start period
- `redis` healthcheck: `redis-cli ping` — 10s interval, 5 retries, 5s start period
- `backend` and `worker` `depends_on` now use `condition: service_healthy` for both `mongo` and `redis`, so neither process starts until the database and queue are confirmed ready

`VITE_SITE_URL` build arg default changed from the hardcoded `https://mybinderpro.com` to `http://localhost:${FRONTEND_PORT:-7680}` so local development builds do not embed a production URL.

#### PM2

Process list now includes:

- `backend` (uvicorn)
- `worker` (arq)
- `frontend` (serve dist)

#### Frontend Dockerfile

- Multi-stage build (`node` build stage + `nginx` runtime stage)
- Adds custom Nginx config with SPA fallback and `/api` proxy

---

### 1.8 Frontend SEO and Routing Updates

Added/updated:

- stronger homepage metadata and canonical URL
- JSON-LD structured data (Organization, SoftwareApplication/Offer, FAQ, WebSite)
- `frontend/public/robots.txt`
- `frontend/public/sitemap.xml`
- `frontend/public/llms.txt`
- catch-all route and dedicated `NotFound` page

---

### 1.9 Testing and CI Additions

New backend test suite coverage includes:

- Auth flow
- JWT hardening
- Health endpoints (including detailed readiness)
- Payment checkout/webhook idempotency
- Redis rate limiting behavior
- Payment reconciliation jobs
- Validation/completeness logic

New CI workflow (`.github/workflows/ci.yml`):

- Backend tests
- Python dependency audit (`pip-audit`)
- Frontend typecheck + build
- Frontend npm audit (non-blocking)

---

### 1.10 v1.0 Foundation Still Present

All core v1.0 capabilities remain in place (OTP auth, profile encryption, YAML module rules engine, AI enhancement pipeline, PDF outputs, admin APIs), but several runtime/security/ops behaviors now differ as described above.

---

### 1.11 Test Suite Hardening and Audit (March 2026)

A full audit of the backend test suite was conducted against all test files. The following issues were found and resolved.

#### New test files added

| File | Tests | Coverage area |
|------|-------|---------------|
| `app/tests/test_binders.py` | 28 | Binder generate, status, list, preview, sections, section content, all three download paths |
| `app/tests/test_profile.py` | 30 | Get/save profile, completeness, readiness, export (GDPR), delete account (PDF cleanup), messages (list, reply, mark-read) |
| `app/tests/test_feedback.py` | 8 | Anonymous submission, authenticated submission, field storage, validation, invalid-token fallback |
| `app/tests/test_generate_binder.py` | 11 | Not found, happy path, bad snapshot, AI failure fallback, PDF failure, premium vs standard, sitter packet non-fatal failure |

Total test count after hardening: **269 passing**.

#### Bugs fixed in existing test infrastructure

**`app/tests/conftest.py`**

- `FakeCursor` was missing `.skip()`, `.limit()`, `.to_list()`, and `.allow_disk_use()` methods — added all four so cursors can be chained without raising `AttributeError` in route tests.
- `_make_collection()` was missing `delete_many` — added so delete-account and similar routes can be asserted correctly.
- `replace_one` default mock returned `modified_count=0, upserted_id=<ObjectId>` which misrepresented a successful replace as an insert — corrected to `modified_count=1, upserted_id=None`.
- `audit_logs` and `feedback` collections were absent from `make_mock_db()` — added so routes that write to those collections do not raise `AttributeError`.
- Added clarifying comment on the `send_otp_email` patch explaining it is a safety net only, because the `resend_api_key=""` guard in `auth.py` prevents the real function from being called in tests.

**`app/tests/test_auth.py`**

- Added off-by-one boundary test: `test_verify_otp_exactly_four_attempts_still_allowed` proves that `attempts=4` (one below the lockout threshold) still succeeds with the correct code.
- Logout test now asserts `refresh_tokens.delete_one` is called — previously the test only confirmed the cookie was cleared, not that the token was invalidated in the database.
- `test_protected_endpoint_with_valid_token` was accepting `in (200, 404)` — narrowed to `200` (the mock returns `None` for `profiles.find_one`, which produces a default empty profile, not a 404).
- `test_request_otp_valid_email` now asserts `pending_otps.replace_one` is called — previously it only checked the HTTP status code.

**`app/tests/test_payments.py`**

- Added `test_create_checkout_unauthenticated` — the auth dependency was previously not tested for the checkout endpoint.
- Added `test_create_checkout_stripe_error` — the `StripeError` exception path in the checkout route was untested.
- `test_webhook_duplicate_delivery_is_idempotent` was sending no `stripe-signature` header — added the correct HMAC-signed header to match real request structure.
- `test_create_checkout_idempotency_key_is_deterministic` pinned `date.today()` to a fixed value so the test cannot fail when run across a midnight boundary.
- Removed dead `_signed_webhook` helper function that was never called.

**`app/tests/test_rate_limit.py`**

- `test_rate_limit_allows_when_under_limit` previously relied on Redis being unreachable to pass (fail-open behavior). Replaced with an explicit `_check_rate` mock returning `(True, 0)` so the test is deterministic in any environment.

**`app/tests/test_binders.py`**

- Magic number `9` for section count replaced with `len(SECTION_META)` imported from the route module.
- `test_generate_missing_required_fields` was accepting `in (400, 422)` — narrowed to `422` which is the correct status for `ErrorCode.VALIDATION`.
- Inline `import tempfile, os` in a test function moved to top-level imports.

**`app/tests/test_profile.py`**

- Export test (`test_export_includes_binders_and_payments`) previously only asserted `pdf_path` was stripped. Now also asserts `sitter_packet_path` and `fill_in_checklist_path` are absent from the export payload.
- `test_delete_account_with_binder_pdfs` previously only verified `secure_delete` was called for the main PDF. Expanded to cover all three PDF types (main, sitter packet, fill-in checklist) using `assert_has_calls` with `any_order=True`.
- Inline `import tempfile, os` moved to top-level imports.

**`app/tests/test_generate_binder.py`**

- `test_job_success_updates_status_to_ready` now verifies that `generating` is set before `ready` using `.index()` ordering check — previously both statuses were checked for presence but not sequence.
- `test_job_pdf_failure_marks_failed_and_reraises` left `generate_sitter_packet`, `generate_fill_in_checklist`, and `collect_unknowns_from_render` unpatched — added missing patches for consistent isolation.
- Added `test_job_premium_enhance_modules_failure_is_nonfatal` — the case where `enhance_modules` raises an exception for a premium-tier binder was untested.

**`app/tests/test_validation.py`**

- Removed dead helper functions `_minimal_profile()` and `_complete_profile()` that were defined at the bottom of the file but never called.

---

## 2. How to Build on Top of These Changes

### 2.1 Working with Async Binder Generation

Use this flow in new frontend or API consumers:

1. Call `POST /api/binders/generate`
2. Store returned binder ID and initial status
3. Poll `GET /api/binders/status/{binder_id}` every 2-5 seconds
4. When status is `ready`, fetch sections/download links
5. If status is `failed`, surface retry UX

Do not block a request waiting for PDF creation.

---

### 2.2 Adding New Background Jobs

To add another async capability:

1. Create task function under `backend/app/tasks/`
2. Register it in `backend/app/worker.py` under `WorkerSettings.functions` or `cron_jobs`
3. Enqueue from API route using `request.app.state.arq_pool.enqueue_job(...)`
4. Keep job arguments minimal (IDs, not large payloads)
5. Persist status transitions in MongoDB for UI visibility

---

### 2.3 Extending Payment Reliability

When adding payment features:

1. Preserve idempotency behavior in checkout creation
2. Keep webhook handlers idempotent (check existing records first)
3. Add reconciliation logic for any new critical payment states
4. Ensure Stripe metadata always includes user context needed for repair

---

### 2.4 Extending JWT / Auth

If introducing SSO or external identity:

1. Keep issuer/audience strategy explicit per environment
2. Update all decode call sites together
3. Add tests for wrong/missing claims
4. Avoid loosening validation except for explicit best-effort middleware use cases

---

### 2.5 Extending Middleware Safely

Current middleware order in `backend/app/main.py`:

1. CORS
2. Body size limit
3. Rate limit
4. Request logging
5. Security headers
6. Audit logging

When adding middleware, place it intentionally based on failure mode and cost.

---

### 2.6 Adding New API Endpoints

1. Add/modify route file under `backend/app/routes/`
2. Register router in `backend/app/main.py`
3. Add/update frontend types in `frontend/src/types.ts`
4. Use shared axios instance in `frontend/src/api.ts`
5. Use standardized error raising:

```python
from app.errors import raise_error, ErrorCode

raise_error(ErrorCode.NOT_FOUND, "Binder not found")
```

---

### 2.7 Adding New Onboarding/Profile Fields

1. Add frontend step/component in `frontend/src/pages/steps/`
2. Add field(s) to backend profile model in `backend/app/models/profile.py`
3. Update completeness logic in `backend/app/validation/completeness.py`
4. Update frontend schemas and types
5. If sensitive, add to encryption list and export masking

---

### 2.8 Adding New Binder Content Modules

For content-only changes:

1. Add/update YAML in `backend/app/library/data/`
2. Register in loader (`home_type.py`, `region.py`, `systems.py`, `universal.py`)
3. Add selection rule in `backend/app/rules/engine.py`
4. Run library validation before release

---

### 2.9 Adding Sensitive Profile Fields

For any secret/PII-like field:

1. Add to profile model
2. Add field to `ENCRYPTED_FIELDS` in `backend/app/services/crypto.py`
3. Mask in profile export endpoint
4. Avoid logging raw values
5. Consider audit logging on read/export

---

### 2.10 Frontend Conventions (Still Applicable)

- Use `useAuth()` from `AuthContext.tsx`
- Use shared axios instance (`frontend/src/api.ts`)
- Guard auth-required pages with `ProtectedRoute`
- Gate console logging behind `import.meta.env.DEV`
- Reuse shared style primitives from `frontend/src/styles/`

---

### 2.11 Backend Conventions (Still Applicable)

- Type hints on all function signatures
- Async DB access with Motor (`await` all calls)
- Import configuration from `app.config.settings` only
- Reuse shared validators from `backend/app/validation/validators.py`
- Never log decrypted secret values

---

## 3. Environment Variables Reference (Complete)

This section includes all variables currently used by backend, frontend, PM2, Docker Compose, or CI.

---

### 3.1 Backend Runtime Variables

These are consumed by `backend/app/config.py` and backend runtime code.

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `MONGO_URI` | Yes | `mongodb://localhost:27017/home_binder` | Primary Mongo connection string |
| `MONGODB_URI` | No | - | Alias accepted for `MONGO_URI` |
| `REDIS_URL` | Yes (current architecture) | `redis://localhost:6379` | Required for ARQ + rate limiting |
| `JWT_SECRET` | PROD: Yes | `change-me-in-production` | JWT signing key |
| `JWT_ALGORITHM` | No | `HS256` | JWT algorithm |
| `JWT_ISSUER` | No | `binderpro` | JWT `iss` claim |
| `JWT_AUDIENCE` | No | `binderpro` | JWT `aud` claim |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `15` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `7` | Refresh token lifetime |
| `ENCRYPTION_KEY` | PROD: Yes | *(empty)* | Fernet key for encrypted fields |
| `PORT` | No | `7691` | Backend listen port |
| `DATA_DIR` | No | `./data/binders` | PDF output directory |
| `FRONTEND_URL` | No | `http://localhost:7680` | Used for CORS and Stripe redirects |
| `CORS_ORIGINS` | No | *(empty)* | Comma-separated explicit origins |
| `STRIPE_SECRET_KEY` | PROD: Yes | *(empty)* | Stripe secret key |
| `STRIPE_PUBLISHABLE_KEY` | Frontend/payment UX | *(empty)* | Stripe publishable key |
| `STRIPE_WEBHOOK_SECRET` | PROD: Yes | *(empty)* | Stripe webhook signature secret |
| `RESEND_API_KEY` | PROD: Yes | *(empty)* | Email delivery API key |
| `FROM_EMAIL` | No | `noreply@mybinderpro.com` | Sender address |
| `ANTHROPIC_API_KEY` | Needed for Claude stages | *(empty)* | Claude API key |
| `AI_ENHANCEMENT_ENABLED` | No | `true` | Master AI switch |
| `AI_ENHANCEMENT_PROVIDER` | No | `auto` | `auto`, `claude`, `ollama`, `none` |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | Ollama endpoint |
| `OLLAMA_MODEL` | No | `homebinder:8b` | Ollama model name |
| `SENTRY_DSN` | Optional | *(empty)* | Enables Sentry when set |
| `ENVIRONMENT` | No | `development` | `development`, `staging`, `production` |

---

### 3.2 Root/Process Manager Variables (PM2 + Compose)

| Variable | Required | Default | Used By |
|----------|----------|---------|---------|
| `BACKEND_PORT` | No | `7691` | PM2 and compose port mapping |
| `FRONTEND_PORT` | No | `7680` | PM2 and compose port mapping |
| `WEB_CONCURRENCY` | No | `2` | Uvicorn worker count in PM2 backend command |
| `MONGO_URI` | Yes | `mongodb://localhost:27017/home_binder` | Passed to backend/worker |
| `REDIS_URL` | Yes | `redis://localhost:6379` | Passed to backend/worker |
| `JWT_SECRET` | PROD: Yes | `change-me-in-production` | Passed to backend/worker |
| `DATA_DIR` | No | `./data/binders` | Passed to backend/worker |
| `RESEND_API_KEY` | PROD: Yes | *(empty)* | Passed to backend/worker |
| `FROM_EMAIL` | No | `noreply@mybinderpro.com` | Passed to backend/worker |
| `SITE_URL` | No | `http://localhost:7680` | Compose build arg source for `VITE_SITE_URL`. Set to production URL at deploy time. |

---

### 3.3 Frontend Variables

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `VITE_API_URL` | No | `/api` | Axios base URL at build/runtime |
| `VITE_API_PORT` | No | `7691` | Used by Vite dev proxy |
| `VITE_SITE_URL` | No | `http://localhost:7680` | Site URL for meta/OG context. Set to production URL at deploy time. |
| `PORT` | No | `7680` | Vite dev server port |

---

### 3.4 CI/Test Variables (GitHub Actions)

Configured in `.github/workflows/ci.yml` for backend tests:

- `ENVIRONMENT=test`
- `JWT_SECRET=ci-test-secret-not-for-production`
- `MONGO_URI=mongodb://localhost:27017/binderpro_test`
- `ENCRYPTION_KEY=`
- `STRIPE_SECRET_KEY=`
- `STRIPE_WEBHOOK_SECRET=`
- `RESEND_API_KEY=`
- `ANTHROPIC_API_KEY=`
- `SENTRY_DSN=`

---

### 3.5 Production Readiness Checklist

The application should not be considered production-ready until all are true:

- [ ] `ENVIRONMENT=production`
- [ ] `JWT_SECRET` is changed from default
- [ ] `ENCRYPTION_KEY` is configured
- [ ] `MONGO_URI` uses TLS (`mongodb+srv` or `tls=true`)
- [ ] `REDIS_URL` points to production Redis
- [ ] `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` are configured
- [ ] `RESEND_API_KEY` is configured
- [ ] `FRONTEND_URL` is non-localhost
- [ ] ARQ worker process is running
- [ ] Optional but recommended: `SENTRY_DSN` configured

---

## 4. External Services and Runtime Setup

### 4.1 MongoDB

Purpose:

- Primary system of record (users, profiles, binders, payments, tokens, feedback, audit data)

Local dev quick start:

```bash
docker run -d -p 27017:27017 --name mongodb mongo:7
```

Set:

- `MONGO_URI=mongodb://localhost:27017/home_binder`

Production recommendation:

- MongoDB Atlas with TLS-enabled URI

---

### 4.2 Redis (New Required Service)

Purpose:

- ARQ job queue backend
- Shared rate limiting store

Local dev quick start:

```bash
docker run -d -p 6379:6379 --name redis redis:7-alpine
```

Set:

- `REDIS_URL=redis://localhost:6379`

Important:

- Backend startup expects Redis to be reachable for ARQ pool creation.

---

### 4.3 ARQ Worker Process (New Required Runtime Process)

Purpose:

- Executes queued binder generation jobs
- Runs scheduled payment reconciliation

Run manually:

```bash
cd backend
arq app.worker.WorkerSettings
```

If worker is down:

- Binder requests remain `queued`
- PDFs will not be generated

---

### 4.4 Stripe

Purpose:

- Checkout sessions, payment completion events, payment metadata

Webhook events to configure:

- `checkout.session.completed`
- `checkout.session.expired`
- `payment_intent.payment_failed`

Local webhook forwarding:

```bash
stripe listen --forward-to localhost:7691/api/payments/webhook
```

Set:

- `STRIPE_SECRET_KEY`
- `STRIPE_PUBLISHABLE_KEY`
- `STRIPE_WEBHOOK_SECRET`

---

### 4.5 Resend

Purpose:

- OTP emails
- welcome email
- payment confirmation
- binder ready/failure notifications

Set:

- `RESEND_API_KEY`
- `FROM_EMAIL`

Development behavior:

- With no key in development, OTP/email content is printed to console.

---

### 4.6 Anthropic (Claude)

Purpose:

- AI enhancement stages (when enabled)

Set:

- `ANTHROPIC_API_KEY`
- `AI_ENHANCEMENT_ENABLED=true`
- `AI_ENHANCEMENT_PROVIDER=auto` or `claude`

---

### 4.7 Ollama (Optional)

Purpose:

- Local AI stage support and fallback behavior

Set:

- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`

If not using Ollama in production:

- set `AI_ENHANCEMENT_PROVIDER=claude`

---

### 4.8 Sentry (Optional but Recommended)

Purpose:

- Exception tracking and performance traces

Set:

- `SENTRY_DSN`

Notes:

- Disabled when DSN is empty
- Production logging still works without Sentry

---

### 4.9 Reverse Proxy / TLS

Production should run behind a reverse proxy (Nginx, Caddy, or Cloudflare) for:

- HTTPS termination
- HTTP-to-HTTPS redirect
- optional static/API routing control

---

### 4.10 PM2 Runtime

Start all processes:

```bash
pm2 start ecosystem.config.cjs
```

Production mode:

```bash
pm2 start ecosystem.config.cjs --env production
```

Expected process set:

- backend
- worker
- frontend

---

### 4.11 Docker Compose Runtime

The compose stack now includes:

- mongo
- redis
- backend
- worker
- frontend

Run:

```bash
docker compose up --build
```

---

### 4.12 CI Service (GitHub Actions)

Workflow:

- `.github/workflows/ci.yml`

Purpose:

- Run backend tests
- Audit Python dependencies
- Typecheck + build frontend

This should be kept green before release.

---

Last updated: March 2026 (current branch, unpublished delta included — test suite hardening and Docker health check additions applied)
