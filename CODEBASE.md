# BinderPro — Project Context

## What This Is
A personalized home operating manual generator. Users complete a profile about their home, pay for a tier (standard/premium), and receive a custom PDF binder with emergency procedures, maintenance schedules, contacts, and region-specific content. Premium tier includes AI-personalized module content.

## Stack
- **Backend**: FastAPI (Python 3.12) + Motor (async MongoDB) + Uvicorn
- **Frontend**: React 18 + Vite + Tailwind CSS + React Router 6 + Axios
- **Database**: MongoDB (local or Atlas)
- **Auth**: Email OTP -> JWT access tokens (15 min) + httpOnly refresh token cookies (7 day)
- **Payments**: Stripe Checkout (webhook-driven)
- **Email**: Resend (falls back to console in dev)
- **PDF**: ReportLab
- **AI**: Anthropic Claude (primary) + Ollama (dev/fallback) — 3-stage pipeline
- **Encryption**: Fernet (field-level encryption for sensitive profile data)
- **Process Mgmt**: PM2 (ecosystem.config.cjs)

## Project Structure
```
home_binder/
  backend/
    app/
      main.py              # FastAPI app, lifespan, CORS, 5 middleware, error handlers, index creation
      config.py             # pydantic-settings (reads .env, production validation)
      errors.py             # ErrorCode enum + raise_error helper
      routes/
        auth.py             # OTP, verify, refresh, logout, dev-login
        profile.py          # CRUD + completeness + export + delete (GDPR) — encrypts/decrypts fields
        binders.py          # generate, list, sections, section content, download, sitter-packet, checklist
        payments.py         # Stripe checkout, webhook, verify-session
        admin.py            # orders, users, pricing, feedback, refunds, AI usage stats
        feedback.py         # user bug/feature reports
      models/
        profile.py          # Pydantic models for all profile sections
        user.py             # User + token models
        binder.py           # Binder model (includes missing_items, ai_tokens_used)
      middleware/
        rate_limit.py       # Token bucket rate limiting
        logging.py          # Request logging with request IDs
        security.py         # Security headers (X-Content-Type-Options, X-Frame-Options, HSTS, etc.)
        audit.py            # Audit logging — sensitive data access to audit_log collection
      services/
        email.py            # Resend email templates
        crypto.py           # Fernet encrypt/decrypt/mask for sensitive profile fields
      ai/
        generator.py        # AIContentGenerator — Stage 1 (drafts), Stage 2 (enhance), Stage 3 (modules)
        module_enhancer.py  # BlockSerializer + ModuleEnhancer — serialize blocks for AI enhancement
        ollama_client.py    # Ollama local model client
        enhancer.py         # Claude enhancement client
      templates/
        narrative.py        # TemplateWriter — renders YAML modules to Block objects + render_all_sections()
      pdf/
        generator.py        # ReportLab PDF generation — render_blocks with KeepTogether, callout accents
      outputs/
        fill_in_checklist.py # Fill-in checklist PDF (template unknowns + AI-identified gaps)
        sitter_packet.py    # Sitter/guest packet PDF
      library/
        loader.py           # YAML module loader
        home_type.py        # Home-type module definitions
        region.py           # Region module definitions
        systems.py          # System-specific module definitions
        universal.py        # Universal (all-home) modules
        validation.py       # Template + placeholder validation
        data/               # YAML content data files (9 files: home_type, household, etc.)
        placeholder_registry.yaml  # Known placeholder tokens
      rules/
        engine.py           # Rules engine — selects modules based on profile
      validation/
        completeness.py     # Profile completeness scoring
        validators.py       # Field-level validators (phone, ZIP, etc.)
        goal_mapping.py     # Binder goal to module mapping
      utils/
        secure_delete.py    # Overwrite-then-delete for sensitive files
    venv/                   # Python virtualenv (not committed)
  frontend/
    src/
      api.ts                # Axios instance, token management, error types
      AuthContext.tsx        # React context: isAuthenticated, login/logout, silent refresh
      App.tsx               # Routes + ProtectedRoute
      types.ts              # All TypeScript interfaces (mirrors backend models)
      schemas.ts            # Zod schemas for client-side validation
      pages/
        Landing.tsx
        Login.tsx            # OTP flow + dev account buttons
        Onboarding.tsx       # 12-step wizard with validation + save
        Dashboard.tsx        # Binder viewer, electronic content reader, secure downloads
        BinderReview.tsx     # Pre-purchase binder readiness review
        SelectPlan.tsx
        Checkout.tsx         # Stripe checkout
        PaymentSuccess.tsx   # Post-payment verification + binder generation trigger
        Admin.tsx
        Privacy.tsx
        Terms.tsx
        Support.tsx
        steps/               # Individual onboarding step components (12 active)
      components/
        Header.tsx           # Sticky header with auth-aware nav
        Footer.tsx           # Site footer (links to Support, Privacy, Terms)
        BlockRenderer.tsx    # Renders Block JSON to styled React elements (electronic viewer)
        ErrorBoundary.tsx    # React error boundary with retry/go-home
        Stepper.tsx          # Step indicator for onboarding
        ProgressBar.tsx
        StepCard.tsx
        Toast.tsx
        Skeleton.tsx
        HelpBubble.tsx
        EmptyState.tsx       # No-data placeholder component
        Icons.tsx            # SVG icon components
        ScrollManager.tsx    # Scroll-to-top on route change
      styles/
        form.ts              # Shared input/label/select class strings
        shared.ts            # Shared page layout class strings
```

## Key Patterns

### Auth Flow
- Access token stored **in-memory** (module-level variable, not localStorage), sent as `Authorization: Bearer` header
- Refresh token in httpOnly cookie, path `/api/auth` — handles session persistence across page loads
- On 401, API dispatches `auth:unauthorized` event → AuthContext clears state → ProtectedRoute redirects (no hard page reload)
- OTP codes generated with `secrets.randbelow()`, stored in MongoDB `pending_otps` collection (hashed with SHA-256, TTL index auto-cleanup, max 5 attempts per code)
- `AuthContext` provides `isAuthenticated`, `isAdmin`, `login()`, `logout()`
- Dev accounts auto-seeded in development mode (admin@test.com, user@test.com)

### Profile Save Flow
- Frontend: `api.put('/profile/', profileObject)` on each step advance
- Backend: Pydantic validates, encrypts sensitive fields, `model_dump()`, upsert to `db.profiles`
- `save()` returns boolean; `next()` blocks advancement on failure
- `get_profile` decrypts fields, validates through Pydantic (new fields get defaults)

### Sensitive Data Encryption
- Fernet AES-128-CBC + HMAC-SHA256 for field-level encryption
- Encrypted fields: `wifi_password`, `garage_code`, `alarm_instructions`, `insurance_policy_number`
- Encrypted values prefixed with `enc:1:` (version tag) to prevent double-encryption
- `ENCRYPTION_KEY` required in production, optional in dev (plaintext without it)
- **Production**: encryption failures raise errors (never falls back to plaintext)
- Profile export masks sensitive fields (last 4 chars or `[REDACTED]`)

### AI Content Pipeline
- **Stage 1**: Ollama drafts intro paragraphs per section
- **Stage 2**: Claude enhances low-confidence drafts
- **Stage 3**: ModuleEnhancer personalizes rendered template blocks (premium tier only)
  - BlockSerializer converts Block objects to/from AI-readable markup format
  - Claude processes full sections; Ollama chunks at subheading boundaries
  - Missing items (AI-identified gaps) stored in binder doc and shown in fill-in checklist
- Provider selection: `AI_ENHANCEMENT_PROVIDER` config — auto/claude/ollama/none
- Cost tracking: `ai_tokens_used` per binder, `GET /admin/ai-usage` summary

### Binder Generation Flow
```
Profile → Rules Engine → YAML Modules → TemplateWriter (render Blocks)
  → [Premium: ModuleEnhancer AI personalization]
  → generate_binder_pdf (ReportLab)
  → Store PDF path + metadata in MongoDB
```

### Electronic Viewer
- Dashboard lazy-loads section content via `GET /binders/{id}/sections/{key}/content`
- `BlockRenderer` component renders Block types: paragraph, numbered_list, callout_box, table, checklist, subheading
- All `dangerouslySetInnerHTML` content sanitized with **DOMPurify** (only `<strong>`, `<em>`, `<br>` allowed)
- AI-enhanced content shows "Personalized" badge
- Print stylesheet hides nav/sidebar, adds page breaks between sections

### Secure Downloads
- All PDF downloads require `Authorization: Bearer` header (no tokens in URLs)
- Frontend uses `fetch()` + `URL.createObjectURL()` instead of `window.open()`

### Onboarding Validation
- Step 0 (HomeIdentity): ZIP code required (regex `^\d{5}(-\d{4})?$`), home type required
- Step 6 (ServiceProviders): Service providers must be filled or marked "Don't have"
- Step 7 (GuestSitterMode): Guest/sitter fields must be filled or marked "Not needed"

### Admin Routing
- Admin users (`is_admin: true` in users collection) are redirected from `/dashboard` and `/onboarding` to `/admin`
- Header shows "Admin" link instead of "Edit Profile" for admin users

### Error Handling
- Backend: `ErrorCode` enum + `raise_error()` -> standardized JSON responses
- Frontend: `ApiRequestError` class, `getErrorMessage()` helper
- Global exception handler catches unhandled errors (500s don't leak internals)

### Middleware Stack (5 total)
1. **CORS** — locked to frontend origin
2. **RateLimit** — token bucket per IP (auth: 5/min, generation: 2/min, general: 60/min)
3. **Logging** — request IDs, timing
4. **Security** — security headers, CSP, HSTS in production
5. **Audit** — logs sensitive data access (exports, downloads, deletions) to `audit_log` collection

## Environment Variables
See `.env.example` for all required vars. Key ones:
- `MONGO_URI` — MongoDB connection string (use `+srv` or `tls=true` in production)
- `JWT_SECRET` — Must be strong in production
- `ENCRYPTION_KEY` — Fernet key for field encryption (required in production)
- `BACKEND_PORT` / `FRONTEND_PORT` — Server ports
- `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` — Stripe keys
- `RESEND_API_KEY` — Email (optional in dev, OTPs print to console)
- `ENVIRONMENT` — `development` or `production` (gates dev-login, OTP logging, security checks)
- `AI_ENHANCEMENT_ENABLED` / `AI_ENHANCEMENT_PROVIDER` — AI enhancement config

## Running Locally
```bash
# Backend
cd backend && python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port $BACKEND_PORT

# Frontend
cd frontend && npm install && npm run dev

# Or with PM2
pm2 start ecosystem.config.cjs
```

## Important Notes
- Never commit `.env` files (only `.env.example`)
- Dev accounts (admin@test.com, user@test.com) are only seeded when `ENVIRONMENT=development`
- The `/auth/dev-login` endpoint is blocked in production
- MongoDB indexes are created on startup (idempotent), including `pending_otps` TTL index
- Refresh tokens have TTL index for automatic cleanup
- OTPs stored in MongoDB with TTL auto-cleanup, SHA-256 hashed, max 5 attempts
- Sensitive profile fields encrypted at rest (Fernet) — key required in production, errors raised on failure
- AI module enhancement is premium-only and best-effort (falls back to template content on failure)
- Audit log tracks sensitive data access for compliance
- PDF download paths validated against `data_dir` to prevent path traversal
- Health endpoint (`/api/health`) pings MongoDB, returns 503 if unreachable
- No `console.log` in production frontend builds (all gated behind `import.meta.env.DEV`)
