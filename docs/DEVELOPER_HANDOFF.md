# Developer Handoff

## Current Status

BinderPro is feature-complete for its initial release. All four development phases (security, AI pipeline, display formatting, production hardening) are done. The app is running in staging with real Stripe test keys and Resend email delivery.

## How to Orient Yourself

1. **Read the README.md** for quick start and stack overview.
2. **Read docs/ARCHITECTURE.md** for system design and key flows.
3. **Read CODEBASE.md** for detailed code-level context (file-by-file).
4. **Run the app locally** — `pm2 start ecosystem.config.cjs` after setting up `.env` files.
5. **Log in as admin@test.com** (dev mode) to explore the full admin flow.
6. **Log in as user@test.com** to walk the user flow: onboarding -> payment -> binder generation -> dashboard.

## Key Files to Read First

| File | What it tells you |
|------|------------------|
| `backend/app/main.py` | App initialization, middleware stack, route registration |
| `backend/app/config.py` | All environment variables and production validation |
| `backend/app/routes/binders.py` | Core business logic: binder generation flow |
| `backend/app/ai/generator.py` | AI content pipeline orchestration |
| `frontend/src/App.tsx` | All routes and auth protection |
| `frontend/src/api.ts` | API client, token management, error handling |
| `frontend/src/AuthContext.tsx` | Auth state management |
| `frontend/src/pages/Dashboard.tsx` | Main post-purchase experience |
| `frontend/src/pages/Onboarding.tsx` | 12-step profile wizard |

## Conventions

- **Backend**: Python with type hints. Pydantic for validation. Async MongoDB via Motor. Error handling through `ErrorCode` enum + `raise_error()`.
- **Frontend**: TypeScript strict mode. Tailwind for styling (shared class strings in `src/styles/`). Zod for client-side validation. No state management library — React context for auth, local state for everything else.
- **Auth**: Access tokens are in-memory only (module-level variable in `api.ts`). Never store in localStorage. Refresh via httpOnly cookie.
- **Sensitive data**: Encrypted at rest with Fernet. Always use `crypto.encrypt_field()` / `decrypt_field()`. Never log decrypted values.
- **PDF generation**: All PDF code uses ReportLab's `Block` abstraction. Blocks render to both PDF (via `pdf/generator.py`) and React (via `BlockRenderer.tsx`).
- **Console logging**: Frontend `console.log` must be gated behind `import.meta.env.DEV`.

## Notable Design Decisions

1. **No localStorage for tokens** — security choice. Access tokens live in a module-level variable. Page refresh requires a silent refresh via cookie.
2. **AI is best-effort** — if Claude/Ollama fail, binder generation falls back to template content. Premium users get AI enhancement; standard users get templates only.
3. **Field-level encryption, not full-database encryption** — only wifi passwords, garage codes, alarm codes, and insurance numbers are encrypted. This keeps queries fast while protecting the most sensitive fields.
4. **YAML content modules** — binder content lives in `backend/app/library/` as YAML files. The rules engine selects which modules apply based on home type, features, and region. This means content updates don't require code changes.
5. **No SPA framework for state** — the app is simple enough that React context + local state covers all needs. Adding Redux/Zustand would be over-engineering.

## What Was Cleaned Up (Repo Audit)

- 9 stale/duplicate markdown reports removed from root
- Documentation consolidated into `docs/` directory
- Port defaults standardized to 7680/7691 across all configs
- Root `.env.example` rewritten with all variables documented
- `backend/.env.example` created (was missing)
- Dockerfiles updated to production-ready defaults
- `.gitignore` updated to exclude `frontend/.env`

## Known Assumptions

- MongoDB is expected to be running locally on port 27017 (or configured via `MONGO_URI`)
- PM2 is installed globally (`npm install -g pm2`)
- Python 3.12+ is required
- Node 20+ is required
- Ollama is optional — only needed if `AI_ENHANCEMENT_PROVIDER` includes Ollama
- Stripe webhook requires a publicly accessible URL (use `stripe listen --forward-to` for local development)
