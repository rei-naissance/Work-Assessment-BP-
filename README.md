# BinderPro

Personalized home operating manual generator. Users complete a home profile, select a tier (Standard/In-Depth), pay via Stripe, and receive a custom PDF binder with emergency procedures, maintenance schedules, contacts, and region-specific content. In-Depth tier includes AI-personalized module content.

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Motor (async MongoDB) + Uvicorn |
| Frontend | React 18 + Vite + Tailwind CSS + React Router 6 |
| Database | MongoDB |
| Auth | Email OTP -> JWT (in-memory) + httpOnly refresh cookies |
| Payments | Stripe Checkout (webhook-driven) |
| Email | Resend (console fallback in dev) |
| PDF | ReportLab |
| AI | Anthropic Claude + Ollama (3-stage pipeline) |
| Encryption | Fernet (field-level for sensitive profile data) |
| Process Mgmt | PM2 |

## Quick Start

```bash
# Backend
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install

# Environment
cp .env.example .env          # root (for PM2)
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
# Edit all three with your values

# Run with PM2
pm2 start ecosystem.config.cjs

# Or run manually:
# Backend: cd backend && uvicorn app.main:app --reload --port 7691
# Frontend: cd frontend && npm run dev
```

**URLs** (default ports):
- Frontend: http://localhost:7680
- Backend API docs: http://localhost:7691/docs
- MongoDB: localhost:27017

### Dev Accounts

In development mode, two accounts are auto-seeded:

| Account | Email | Access |
|---------|-------|--------|
| Admin | admin@test.com | Admin dashboard |
| User | user@test.com | Standard user |

One-click login buttons appear on the login page in dev mode.

## Repo Structure

```
.
├── backend/          # FastAPI application
├── frontend/         # React + Vite application
├── docs/             # Project documentation
├── ecosystem.config.cjs  # PM2 process manager
├── docker-compose.yml    # Docker setup (alternative to PM2)
└── CODEBASE.md       # Project context and conventions
```

See [docs/REPOSITORY_STRUCTURE.md](docs/REPOSITORY_STRUCTURE.md) for detailed directory guide.

## Environment Variables

See `.env.example` (root), `backend/.env.example`, and `frontend/.env.example` for all required variables with descriptions.

Key production requirements:
- `JWT_SECRET` — must be changed from default
- `ENCRYPTION_KEY` — required (Fernet key for field-level encryption)
- `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` — required
- `RESEND_API_KEY` — required for email delivery
- `MONGO_URI` — should use TLS or Atlas `+srv`

## Documentation

- [Development Guide](docs/DEVELOPMENT_GUIDE.md) — what was built, how to extend it, all env vars, and service setup
- [Architecture](docs/ARCHITECTURE.md) — system design and key flows
- [Repository Structure](docs/REPOSITORY_STRUCTURE.md) — directory guide and conventions
- [Developer Handoff](docs/DEVELOPER_HANDOFF.md) — orientation for new developers
- [Release Readiness](docs/RELEASE_READINESS.md) — production signoff checklist
- [Testing Plan](docs/TESTING_PLAN.md) — manual UX test script
- [Production Checklist](docs/PRODUCTION_CHECKLIST.md) — infrastructure deployment checklist

Business docs (business plan, pitch deck, branding, print guide) are in the separate `business_plans/8_MyBinderPro/` directory.

## API

Interactive docs at `http://localhost:7691/docs` when running.

| Group | Prefix | Description |
|-------|--------|-------------|
| Auth | `/api/auth` | OTP login, token refresh, logout |
| Profile | `/api/profile` | CRUD, completeness, export, delete |
| Binders | `/api/binders` | Generate, list, sections, download |
| Payments | `/api` | Pricing, checkout, webhooks |
| Admin | `/api/admin` | Orders, users, pricing, feedback, AI usage |
| Feedback | `/api/feedback` | Bug reports |
| Health | `/api/health` | MongoDB connectivity check |

## Process Management

```bash
pm2 start ecosystem.config.cjs              # development
pm2 start ecosystem.config.cjs --env production  # production
pm2 logs                                     # view logs
pm2 restart all                              # restart
```
