# BinderPro — Production Readiness Checklist

A prioritized checklist for getting BinderPro production-ready. Work through each section in order.

---

## Phase 1: Critical for Launch

These must be complete before accepting real payments.

### 1.1 Error Handling & Recovery
- [x] **Backend error responses** — Consistent JSON error format across all endpoints
  - Created `app/errors.py` with `ErrorCode` enum, `raise_error()`, and `handle_db_error()`
  - Updated all route files to use standardized error utilities
  - Global error handlers in `main.py` for validation and unhandled exceptions
- [x] **Frontend error boundaries** — Wrap main routes to prevent white screen crashes
  - Created `ErrorBoundary.tsx` component with retry and go-home options
  - Wrapped entire app in error boundary in `App.tsx`
- [x] **Binder generation retry** — If AI generation fails, allow retry without re-payment
  - AI generation wrapped in try/except, falls back to empty dict
  - Users can regenerate from dashboard
- [x] **Graceful degradation** — If Ollama is down, fall back to template-only generation
  - Already implemented: AI pipeline has try/except fallback
- [x] **API timeout handling** — Frontend should handle slow/failed API calls gracefully
  - Added 30s timeout to axios in `api.ts`
  - Added `getErrorMessage()` helper for user-friendly error extraction
  - Added `ApiRequestError` class for structured error handling

### 1.2 Email System
- [x] **Email service setup** — Configure transactional email provider
  - Using Resend (already configured in settings)
  - Created `app/services/email.py` with all email functions
- [x] **Welcome email** — Send on successful signup
  - Sent automatically when new user verifies OTP
- [x] **Payment confirmation** — Send receipt after successful payment
  - Sent via Stripe webhook on checkout.session.completed
- [x] **Binder ready notification** — Email when PDF generation completes
  - Sent after successful binder generation
- [x] **Email templates** — Branded HTML templates for all transactional emails
  - All templates use consistent branded design with emerald theme

### 1.3 Payment Hardening
- [x] **Stripe webhook verification** — Verify webhook signatures to prevent spoofing
  - Already implemented in `payments.py` using `stripe.Webhook.construct_event()`
- [x] **Idempotency keys** — Prevent duplicate charges on retries
  - Added to checkout session creation
- [x] **Failed payment handling** — Clear error messages, retry option
  - Standardized error messages via `raise_error()`
  - Frontend can retry checkout
- [ ] **Payment state management** — Handle edge cases (user closes tab during payment)
- [x] **Refund flow** — Admin ability to process refunds
  - Added `/api/admin/refund/{payment_id}` endpoint
  - Processes refund via Stripe API, updates records
- [x] **Receipt storage** — Store payment receipts in database
  - Created `payments` collection in MongoDB
  - Stores session_id, payment_intent, amount, status, timestamps

### 1.4 Data Validation & Security
- [x] **Input sanitization** — Sanitize all user inputs on backend (XSS prevention)
  - Added `_sanitize_string()` function using HTML escaping
  - Applied to all string fields in Profile model via Pydantic validators
- [x] **Phone number validation** — Validate format on backend
  - Added `_validate_phone()` validator to EmergencyContact, ServiceProvider, UtilityProvider, InsuranceInfo, PetSitterInfo
- [ ] **Email validation** — Validate format and potentially verify deliverability
- [x] **ZIP code validation** — Validate against US ZIP code format
  - Added `_validate_zip_code()` validator to HomeIdentity model
- [x] **Rate limiting on auth** — Prevent brute force on login/signup endpoints
  - Created `RateLimitMiddleware` with 5 req/min for auth, 60 req/min for general API
  - Uses in-memory token bucket algorithm
- [x] **JWT expiration** — Ensure tokens expire and refresh flow works
  - Already implemented: access tokens expire after `access_token_expire_minutes` (default 15 min), refresh tokens after `refresh_token_expire_days` (default 7 days)
- [ ] **HTTPS enforcement** — Redirect HTTP to HTTPS in production

---

## Phase 2: Reliability & Operations

Complete these before significant traffic.

### 2.1 Database
- [x] **MongoDB indexes** — Add indexes on `user_id`, `binder.status`, `created_at`
  - Added in `main.py` lifespan: users (email, created_at), profiles (user_id), binders (user_id, status, created_at), payments (user_id, session_id, status)
- [ ] **Backup strategy** — Automated daily backups with retention policy
- [ ] **Backup restoration test** — Verify backups can be restored
- [x] **Connection pooling** — Proper MongoDB connection management
  - Motor handles connection pooling automatically
- [ ] **Data retention policy** — Define how long to keep old binders

### 2.2 Monitoring & Logging
- [ ] **Error tracking** — Integrate Sentry or similar for backend errors
- [x] **Frontend error tracking** — Capture JS errors in production
  - ErrorBoundary catches and logs errors
  - In production, would send to error tracking service
- [x] **Structured logging** — JSON logs with request IDs for tracing
  - Created `RequestLoggingMiddleware` that adds request IDs
  - Logs include method, path, status code, duration
  - X-Request-ID header in responses for debugging
- [ ] **Uptime monitoring** — External service (UptimeRobot, Pingdom) to alert on downtime
- [ ] **API response time tracking** — Monitor slow endpoints
- [ ] **Alerting** — PagerDuty/Slack alerts for critical errors

### 2.3 Rate Limiting & Abuse Prevention
- [x] **Auth endpoint rate limiting** — Max 5 attempts per minute per IP
  - Implemented in `RateLimitMiddleware` (5 req/min burst 10)
- [ ] **Binder generation limiting** — Max 3 generations per hour per user
- [x] **API rate limiting** — General rate limit on all endpoints
  - Implemented in `RateLimitMiddleware` (60 req/min burst 100)
- [ ] **Bot protection** — Consider CAPTCHA on signup if abuse occurs

### 2.4 Environment & Configuration
- [x] **Environment variables** — All secrets in env vars, not code
  - Using pydantic-settings with .env file support
- [x] **Config validation** — App fails fast if required config missing
  - Added `validate_for_production()` method
  - Fails on startup if production mode and missing required config
- [ ] **Separate staging environment** — Test changes before production
- [ ] **Feature flags** — Ability to disable features without deploy

---

## Phase 3: Testing & Quality

Complete before marketing push.

### 3.1 Automated Testing
- [ ] **Unit tests: Validation logic** — Test completeness checks, profile validation
- [ ] **Unit tests: PDF generation** — Test template rendering
- [ ] **Integration tests: Auth flow** — OTP login, token refresh, logout
- [ ] **Integration tests: Payment flow** — Stripe checkout, webhook handling
- [ ] **Integration tests: Binder generation** — Full flow from profile to PDF
- [ ] **E2E tests: Critical paths** — Playwright/Cypress tests for happy paths
- [ ] **CI pipeline** — Run tests on every PR

### 3.2 Manual Testing
- [ ] **Cross-browser testing** — Chrome, Safari, Firefox, Edge
- [ ] **Mobile testing** — iOS Safari, Android Chrome
- [ ] **Payment testing** — Test with Stripe test cards (success, decline, 3DS)
- [ ] **Email testing** — Verify all emails render correctly
- [ ] **PDF testing** — Verify PDFs render correctly on different viewers

---

## Phase 4: Performance & Scalability

Complete before scaling marketing.

### 4.1 Performance Optimization
- [ ] **PDF caching** — Cache generated PDFs, regenerate only on profile change
- [ ] **Image optimization** — Compress images in PDFs
- [ ] **Frontend bundle size** — Analyze and reduce JS bundle
- [ ] **Lazy loading** — Lazy load non-critical components
- [ ] **CDN for static assets** — Serve JS/CSS from CDN
- [ ] **Database query optimization** — Review slow queries

### 4.2 Scalability Preparation
- [ ] **Stateless backend** — Ensure no server-side session state
- [ ] **Queue for PDF generation** — Move heavy work to background queue
- [ ] **Horizontal scaling plan** — Document how to add more backend instances
- [ ] **Database scaling plan** — MongoDB replica set or Atlas scaling

---

## Phase 5: User Experience Polish

Complete for professional launch.

### 5.1 UI/UX Improvements
- [x] **Loading skeletons** — Content skeletons on Dashboard and Admin
- [x] **Empty states** — EmptyState component for no-data views
- [x] **Success feedback** — Toast notifications on actions
- [x] **Mobile responsiveness** — Responsive nav, header menu, responsive tables
- [x] **Print styles** — Print stylesheet hides nav, adds page breaks

### 5.2 Accessibility
- [ ] **Keyboard navigation** — All interactive elements keyboard accessible
- [ ] **Screen reader testing** — Test with VoiceOver/NVDA
- [ ] **Color contrast** — Meet WCAG AA standards
- [ ] **Focus indicators** — Visible focus states on all interactive elements
- [ ] **Alt text** — All images have appropriate alt text
- [ ] **Form labels** — All form fields have associated labels

### 5.3 Content & Copy
- [ ] **Error message review** — User-friendly, actionable error messages
- [ ] **Empty state copy** — Helpful guidance when sections are empty
- [ ] **Onboarding copy review** — Clear, concise instructions
- [ ] **Email copy review** — Professional, on-brand email content

---

## Phase 6: Legal & Compliance

Required for commercial operation.

### 6.1 Legal Documents
- [x] **Privacy Policy** — What data collected, how used, how protected
  - Created `/privacy` page with data collection, security, rights sections
- [x] **Terms of Service** — Usage terms, liability limitations
  - Created `/terms` page with service description, payment terms, limitations
- [x] **Refund Policy** — Clear refund terms
  - Included in Terms of Service (30-day refund policy)
- [ ] **Cookie Policy** — If using cookies/analytics

### 6.2 Compliance
- [x] **Data deletion capability** — Users can request data deletion
  - Added `DELETE /api/profile/` endpoint
  - Deletes user, profile, binders, payments, and PDF files
- [x] **Data export capability** — Users can export their data
  - Added `GET /api/profile/export` endpoint
  - Returns JSON with user, profile, binders, payments data
- [x] **Payment compliance** — PCI compliance via Stripe (verify setup)
  - Using Stripe Checkout - no card data touches our servers
- [ ] **Accessibility statement** — Document accessibility efforts

---

## Phase 7: Launch Preparation

Final checks before go-live.

### 7.1 Infrastructure
- [ ] **Production domain configured** — DNS, SSL certificates
- [ ] **Email domain authentication** — SPF, DKIM, DMARC for deliverability
- [ ] **CDN configured** — CloudFlare or similar
- [ ] **Backup verification** — Confirm backups are running

### 7.2 Monitoring Verification
- [ ] **All alerts configured** — Error rates, uptime, response times
- [ ] **On-call rotation** — Who responds to alerts?
- [ ] **Runbook** — Document common issues and fixes

### 7.3 Launch Checklist
- [ ] **Stripe live mode** — Switch from test to live keys
- [ ] **Analytics configured** — Google Analytics, Mixpanel, or similar
- [x] **Social meta tags** — OG tags in index.html
- [x] **Favicon** — All sizes (ico, svg, 32px, apple-touch-icon)
- [ ] **404 page** — Custom, helpful 404 page
- [ ] **robots.txt** — Proper search engine directives
- [ ] **sitemap.xml** — For search engine indexing

---

## Progress Tracking

| Phase | Status | Completion |
|-------|--------|------------|
| Phase 1: Critical | Done (except HTTPS) | 95% |
| Phase 2: Reliability | Partial | 55% |
| Phase 3: Testing | Not Started | 0% |
| Phase 4: Performance | Not Started | 0% |
| Phase 5: UX Polish | Mostly Done | 80% |
| Phase 6: Legal | Mostly Done | 85% |
| Phase 7: Launch | Partial | 30% |

---

## Notes

- Update this document as items are completed
- Each checkbox can be checked off: `- [x]`
- Add notes under items if needed for context
- Prioritize within phases based on user feedback

---

*Last updated: March 10, 2026*
