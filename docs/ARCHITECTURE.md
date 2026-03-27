# Architecture

## System Overview

```
Browser (React SPA)
    │
    ▼
FastAPI Backend
    ├── MongoDB (profiles, users, binders, payments, refresh_tokens, audit_log)
    ├── ReportLab (PDF generation)
    ├── Anthropic Claude / Ollama (AI content pipeline)
    ├── Stripe (payment processing + webhooks)
    ├── Resend (transactional email)
    └── Fernet (field-level encryption)
```

The frontend is a React SPA. API calls use the relative path `/api`, proxied to the FastAPI backend. The proxy is handled by Vite (dev and local PM2) or nginx (production).

**Serving modes:**

| Mode | Command | Use case |
|------|---------|----------|
| Dev | `npm run dev` (Vite dev server) | Active development with HMR |
| Local PM2 | `vite preview` via `ecosystem.config.cjs` | Running locally without Docker |
| Production | nginx + Docker (`frontend/nginx.conf`) | Real deployments |

`vite preview` is intentionally used for local PM2 because it reuses Vite's proxy config to forward `/api` to the backend. It is **not suitable for production** — use nginx instead (see Production Deployment below).

## Auth Flow

1. User enters email -> backend generates OTP, stores hashed (SHA-256) in `pending_otps` with TTL
2. OTP sent via Resend (or printed to console in dev)
3. User submits OTP -> backend verifies, issues JWT access token + httpOnly refresh cookie
4. Access token stored in-memory (not localStorage) — sent as `Authorization: Bearer` header
5. Refresh token in httpOnly cookie, path `/api/auth` — 7-day expiry, DB-backed revocation
6. On 401, frontend dispatches `auth:unauthorized` event -> AuthContext clears state -> redirect to login
7. Silent refresh on page load via refresh cookie

## Binder Generation Flow

```
User Profile
    │
    ▼
Rules Engine ──── selects applicable YAML modules based on home type, features, region
    │
    ▼
TemplateWriter ── renders YAML modules into Block objects (paragraph, list, table, callout, etc.)
    │
    ▼
[Premium only] ModuleEnhancer ── AI personalizes blocks using profile context
    │                              Claude (primary) or Ollama (fallback)
    │                              Tracks missing_items for fill-in checklist
    │
    ▼
ReportLab PDF Generator ── renders Blocks into formatted PDF
    │
    ▼
MongoDB ── stores binder metadata, section data, AI token usage
```

### AI Content Pipeline (3 Stages)

| Stage | Purpose | Provider |
|-------|---------|----------|
| 1 | Draft intro paragraphs per section | Ollama (local) |
| 2 | Enhance low-confidence drafts | Claude |
| 3 | Personalize module content (premium only) | Claude primary, Ollama fallback |

Stage 3 serializes Block objects into a markup format, sends through AI for personalization (region-specific advice, household safety notes), then deserializes back. Missing items identified by AI are stored in the binder document and surfaced in the fill-in checklist PDF.

## Security Model

- **Token storage**: Access tokens in-memory only (XSS-immune). Refresh tokens in httpOnly cookies.
- **Field encryption**: Fernet AES-128-CBC + HMAC-SHA256 for wifi passwords, alarm codes, garage codes, insurance numbers. Prefixed `enc:1:` to prevent double-encryption.
- **PDF downloads**: Require `Authorization: Bearer` header — no tokens in URLs. Path traversal protection validates paths against `data_dir`.
- **Content sanitization**: DOMPurify in BlockRenderer allows only `<strong>`, `<em>`, `<br>`.
- **Rate limiting**: Token bucket per IP (auth: 5/min, generation: 2/min, general: 60/min).
- **Audit logging**: Sensitive data access (exports, downloads, deletions) logged to `audit_log` collection.
- **Security headers**: X-Content-Type-Options, X-Frame-Options, CSP, HSTS (production), Referrer-Policy.

## Middleware Stack

Applied in order in `main.py`:

1. CORS — locked to frontend origin in production
2. RateLimit — token bucket per IP
3. Logging — request IDs, timing
4. Security — security headers, CSP
5. Audit — logs sensitive data access

## Data Collections (MongoDB)

| Collection | Purpose |
|------------|---------|
| `users` | User accounts, admin flag |
| `profiles` | Home profile data (encrypted sensitive fields) |
| `binders` | Generated binder metadata, section data, AI token usage |
| `payments` | Stripe payment records |
| `pending_otps` | OTP codes (hashed, TTL auto-cleanup) |
| `refresh_tokens` | Session tokens (TTL auto-cleanup) |
| `audit_log` | Sensitive data access log |
| `feedback` | User bug reports and feature requests |

## Deployment

### Local Development (PM2)

`pm2 start ecosystem.config.cjs` runs three processes:
- **backend** — Uvicorn with configurable workers (`WEB_CONCURRENCY`)
- **frontend** — `vite preview` serving the built `dist/` with `/api` proxy to backend
- **worker** — ARQ background worker for PDF generation

After any frontend code change, rebuild before the changes take effect:
```bash
cd frontend && npm run build
pm2 restart frontend
```

### Production (nginx + Docker)

The intended production setup uses nginx as a reverse proxy in front of the static build. The config lives at `frontend/nginx.conf` and is used by `frontend/Dockerfile`.

**To migrate from `vite preview` to nginx:**

1. Install nginx: `sudo apt install nginx`
2. Copy and adapt `frontend/nginx.conf` to `/etc/nginx/sites-available/binderpro`:
   - Change `proxy_pass http://backend:7691` → `proxy_pass http://localhost:7691` (or your actual backend host)
   - Change `root /usr/share/nginx/html` → actual path to `frontend/dist`
3. Enable the site:
   ```bash
   sudo ln -s /etc/nginx/sites-available/binderpro /etc/nginx/sites-enabled/
   sudo rm /etc/nginx/sites-enabled/default   # remove nginx default
   sudo nginx -t                               # verify config
   sudo systemctl enable nginx
   sudo systemctl start nginx
   ```
4. Remove the `frontend` process from PM2 (`pm2 delete frontend`) — nginx replaces it.
5. Set `ENVIRONMENT=production` in backend env so HSTS and production guards activate.

nginx provides gzip compression, immutable asset caching, proper keepalives, and TLS termination — none of which `vite preview` handles.

Docker Compose is available as a containerized alternative (`docker-compose.yml`).

## Configuration

All config managed through environment variables. See `.env.example` files at root, `backend/`, and `frontend/`. Backend uses pydantic-settings (`backend/app/config.py`) with production validation that blocks startup if critical vars are missing.
