# Repository Structure

## Top Level

```
.
├── backend/               # FastAPI application (Python)
├── frontend/              # React SPA (TypeScript)
├── docs/                  # Project documentation
├── README.md              # Project overview and quick start
├── CODEBASE.md            # Project context and conventions
├── ecosystem.config.cjs   # PM2 process manager config
├── docker-compose.yml     # Docker setup (alternative to PM2)
├── package.json           # Root package (dotenv for PM2 ecosystem)
├── .env.example           # Root environment variable template
└── .gitignore
```

## Backend (`backend/`)

```
backend/
├── app/
│   ├── main.py            # FastAPI app, lifespan, CORS, middleware, error handlers
│   ├── config.py          # pydantic-settings config with production validation
│   ├── errors.py          # ErrorCode enum + raise_error helper
│   ├── ai/
│   │   ├── generator.py       # AIContentGenerator — 3-stage pipeline orchestration
│   │   ├── enhancer.py        # Claude enhancement client
│   │   ├── module_enhancer.py # BlockSerializer + ModuleEnhancer (Stage 3)
│   │   └── ollama_client.py   # Ollama local model client
│   ├── library/           # Content modules (YAML) for binder generation
│   ├── middleware/
│   │   ├── rate_limit.py  # Token bucket rate limiting
│   │   ├── logging.py     # Request logging with request IDs
│   │   ├── security.py    # Security headers (CSP, HSTS, etc.)
│   │   └── audit.py       # Sensitive data access audit logging
│   ├── models/
│   │   ├── user.py        # User + token Pydantic models
│   │   ├── profile.py     # Profile section models
│   │   └── binder.py      # Binder model (includes AI token usage)
│   ├── outputs/
│   │   ├── fill_in_checklist.py  # Fill-in checklist PDF
│   │   └── sitter_packet.py     # Sitter/guest packet PDF
│   ├── pdf/
│   │   └── generator.py   # ReportLab PDF renderer
│   ├── routes/
│   │   ├── auth.py        # OTP, verify, refresh, logout, dev-login
│   │   ├── profile.py     # CRUD + completeness + export + delete
│   │   ├── binders.py     # Generate, list, sections, download
│   │   ├── payments.py    # Stripe checkout + webhooks
│   │   ├── admin.py       # Admin dashboard endpoints
│   │   └── feedback.py    # User bug/feature reports
│   ├── rules/             # Rules engine — module selection based on profile
│   ├── services/
│   │   ├── crypto.py      # Fernet encrypt/decrypt/mask
│   │   └── email.py       # Resend email templates
│   ├── templates/
│   │   └── narrative.py   # TemplateWriter — YAML modules to Block objects
│   ├── tests/
│   │   ├── test_smoke.py  # Integration tests
│   │   ├── test_pdf.py    # PDF generation tests
│   │   └── test_rules.py  # Rules engine tests
│   ├── utils/
│   │   └── secure_delete.py  # Overwrite-then-delete for sensitive files
│   └── validation/
│       └── completeness.py   # Profile completeness scoring
├── data/                  # Generated PDFs (gitignored)
├── requirements.txt
├── Dockerfile
├── Modelfile.homebinder   # Ollama model definition
├── .env.example
└── .env                   # Local config (gitignored)
```

## Frontend (`frontend/`)

```
frontend/
├── src/
│   ├── main.tsx           # React entry point
│   ├── App.tsx            # Routes + ProtectedRoute
│   ├── AuthContext.tsx     # Auth state (isAuthenticated, login, logout, refresh)
│   ├── api.ts             # Axios instance, token management, error types
│   ├── types.ts           # TypeScript interfaces (mirrors backend models)
│   ├── schemas.ts         # Zod validation schemas
│   ├── components/
│   │   ├── Header.tsx         # Sticky header with auth-aware nav
│   │   ├── Footer.tsx
│   │   ├── BlockRenderer.tsx  # Renders Block JSON to styled React elements
│   │   ├── Stepper.tsx        # Step indicator for onboarding
│   │   ├── StepCard.tsx
│   │   ├── ProgressBar.tsx
│   │   ├── Toast.tsx
│   │   ├── Skeleton.tsx
│   │   ├── HelpBubble.tsx
│   │   ├── ErrorBoundary.tsx
│   │   ├── Icons.tsx
│   │   ├── EmptyState.tsx
│   │   └── ScrollManager.tsx
│   ├── pages/
│   │   ├── Landing.tsx
│   │   ├── Login.tsx          # OTP flow + dev account buttons
│   │   ├── Onboarding.tsx     # 12-step wizard
│   │   ├── Dashboard.tsx      # Binder viewer + downloads
│   │   ├── SelectPlan.tsx
│   │   ├── Checkout.tsx
│   │   ├── PaymentSuccess.tsx
│   │   ├── BinderReview.tsx
│   │   ├── Admin.tsx
│   │   ├── Privacy.tsx
│   │   ├── Terms.tsx
│   │   ├── Support.tsx
│   │   └── steps/             # Onboarding step components (12 active)
│   └── styles/
│       ├── form.ts            # Shared input/label/select class strings
│       └── shared.ts
├── public/                # Static assets (logos, favicons, OG image)
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.js
├── postcss.config.js
├── Dockerfile
├── .env.example
└── .env                   # Local config (gitignored)
```

## Conventions

- **Backend naming**: snake_case for files, functions, variables. PascalCase for classes.
- **Frontend naming**: PascalCase for components (`.tsx`). camelCase for utilities (`.ts`).
- **New routes**: Add to `backend/app/routes/`, register in `main.py`.
- **New components**: Add to `frontend/src/components/`.
- **New pages**: Add to `frontend/src/pages/`, add route in `App.tsx`.
- **New content modules**: Add YAML to `backend/app/library/`, update rules in `backend/app/rules/`.
- **Documentation**: Technical docs in `docs/`. Business docs (business plan, pitch deck, branding, print guide) in `business_plans/8_MyBinderPro/`.
