# Release Readiness

Last updated: 2026-03-10

## Validated

- [x] Backend starts and serves `/api/health` successfully
- [x] Frontend builds (`tsc && vite build`) without errors
- [x] Auth flow works (OTP login, token refresh, logout)
- [x] Profile CRUD with field-level encryption
- [x] Stripe checkout integration (test mode)
- [x] PDF binder generation (template-based)
- [x] AI content pipeline (3-stage, Claude + Ollama)
- [x] Electronic binder viewer with BlockRenderer
- [x] Admin dashboard (orders, users, payments, feedback, AI usage)
- [x] Rate limiting, security headers, audit logging
- [x] DOMPurify sanitization on rendered content
- [x] Secure PDF downloads (auth header, no URL tokens)
- [x] Account deletion with secure file overwrite
- [x] Port defaults consistent across all config files (7680/7691)
- [x] Environment variable templates complete (root, backend, frontend)
- [x] Documentation consolidated and reconciled

## Unresolved — Must Fix Before Production

### CRITICAL

1. **HTTPS enforcement** — no TLS termination configured. Need nginx reverse proxy or Cloudflare in front.
2. **Production domain + SSL certificate** — currently running on localhost URLs.
3. **Stripe live mode keys** — currently using `sk_test_` keys. Switch to live keys before accepting real payments.
4. **Strong JWT_SECRET** — production `.env` must use a cryptographically random secret, not the default.
5. **ENCRYPTION_KEY** — must be set in production (backend validates this on startup).
6. **Email domain authentication** — SPF, DKIM, DMARC records needed for Resend deliverability.

### IMPORTANT

7. **STRIPE_WEBHOOK_SECRET** — currently empty in staging `.env`. Webhooks will fail without it. Run `stripe listen` to get a local signing secret, or configure in Stripe dashboard for production.
8. **ANTHROPIC_API_KEY** — currently empty in staging. AI enhancement falls back to Ollama (or template-only if Ollama isn't running). Set this for Claude-powered personalization.
9. **MongoDB backups** — no automated backup strategy configured. Use Atlas automated backups or set up `mongodump` cron.
10. **Error tracking** — no Sentry or equivalent. Unhandled errors return generic 500s but aren't reported anywhere.

## Known Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| AI enhancement is best-effort | Low | Falls back to template content. Users still get a complete binder. |
| Ollama requires local GPU/CPU resources | Low | Production should rely on Claude. Ollama is dev/fallback only. |
| No automated tests in CI | Medium | 3 test files exist but no CI pipeline runs them. Set up GitHub Actions. |
| No database migration strategy | Medium | Schema changes require manual MongoDB updates. No migration framework. |
| Single-server deployment | Medium | PM2 handles process restarts but no multi-server redundancy. |
| PDF generation is synchronous | Low | Generation takes a few seconds. Acceptable for current scale. Consider background jobs if volume grows. |
| Refresh token TTL mismatch | Low | Config default is 7 days, staging `.env` overrides to 14. Decide on one value. |

## Recommended Next Steps

1. Set up nginx with Let's Encrypt for HTTPS termination
2. Configure Stripe live keys and verify webhook endpoint
3. Set up Resend production domain with SPF/DKIM/DMARC
4. Generate and set production `JWT_SECRET` and `ENCRYPTION_KEY`
5. Configure MongoDB Atlas (or set up backup cron for self-hosted)
6. Add GitHub Actions CI (run `pytest` and `tsc && vite build`)
7. Set up error tracking (Sentry recommended)
8. Run the manual testing plan (`docs/TESTING_PLAN.md`) end-to-end on staging
9. Load test binder generation to establish baseline performance
10. Set `ENVIRONMENT=production` and verify startup validation passes

## Detailed Checklist

See [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md) for the full phased implementation tracker (7 phases, per-item status).
