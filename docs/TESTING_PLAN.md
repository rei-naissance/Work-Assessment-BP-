# MyBinderPro.com — Common-Sense UX Test (Production Readiness)

**Goal:** A human runs through the product once and answers: *Would a real user get from “interested” to “I have my binder” without getting stuck or confused?*

One run, ~30–45 minutes. Use a fresh email (or new test account) so you see the full flow.

---

## The One Journey

**Land → Log in → Set up home (onboarding) → Pick plan → Pay → Get binder → Use dashboard.**

For each step below, do the journey and answer the questions. If anything is confusing, slow, or feels broken, note it — that’s the UX you’re testing.

---

### 1. Landing (/)

- [ ] **First impression:** Within a few seconds, do you understand what BinderPro is and what you get (a personalized home binder)?
- [ ] **Next step obvious?** Is it clear you should click “Build Your Binder” or “Get Started” to begin? Do those go to login?
- [ ] **Scrolling:** Quick scroll through How it works, What’s included, Pricing, FAQ. Does it feel coherent, or does anything feel like filler or broken (e.g. region carousel, expandable cards)?

**Note anything confusing or missing:**

---

### 2. Log in (/login)

- [ ] **Flow makes sense?** Enter email → get code → enter code → in. No password is intentional; does the copy make that clear?
- [ ] **Errors:** Wrong or expired code — do you see a clear message and know you can try again or use a different email?
- [ ] **After login:** New user lands on onboarding; returning user with a binder lands on dashboard. Does that match what you expect?

**Note:**

---

### 3. Onboarding (12 steps)

- [ ] **Progress:** Do you always know which step you’re on (e.g. “Step 3 of 12”) and that you can go Back?
- [ ] **Required vs optional:** On step 1, is it clear that ZIP and home type are required? If you leave them blank and hit Continue, do you get a helpful message (not a generic error)?
- [ ] **Skip / “Don’t have”:** On steps with lots of fields (e.g. service providers, guest/sitter), can you skip or mark “Don’t have” without feeling forced to make things up?
- [ ] **Review (step 12):** Does the summary look like what you entered? Is it obvious that the next action is “Finish & Choose Your Plan” (or “Save & Return to Dashboard” if you already have a binder)?

**Note any step that felt tedious, unclear, or punishing:**

---

### 4. Select plan (/select-plan)

- [ ] **Choice clear?** Can you tell the difference between Standard and In-Depth and why you’d pick one over the other?
- [ ] **Your data reflected?** Do the module counts or “gaps” (e.g. unknown locations, missing providers) feel like they match what you entered?
- [ ] **Next step:** Is “Continue to Payment” (and the price) obvious? If you want to change answers, is “Edit Responses” easy to find?

**Note:**

---

### 5. Checkout (/checkout) → Payment success

- [ ] **Trust:** Does the order summary and “Pay $X” feel clear and secure (e.g. Stripe mention)?
- [ ] **After paying:** Do you see a clear “Verifying…” → “Generating…” → “Your Binder is Ready!” (or similar) and then land on the dashboard without wondering if it worked?
- [ ] **If something fails:** On payment-success, if there’s an error, do you get a message and a way to “Try Again” or “Go to Dashboard” instead of being stuck?

**Note:**

---

### 6. Dashboard (first time with a new binder)

- [ ] **Orientation:** Within a few seconds, do you understand: “Here’s my binder; I can read it here, download it, or edit my home info and regenerate”?
- [ ] **Finding content:** Can you open a chapter and see content (or a clear “available in PDF”)? Does expanding a sub-chapter load something sensible?
- [ ] **Downloads:** Do “Full Binder,” “Sitter Packet,” and “Fill-In Checklist” (if shown) download and open as PDFs without errors?
- [ ] **Editing and regenerating:** If you change something in Home Information and click Save, do you get clear feedback? If you click Regenerate, is it clear something is happening and then that it’s done (or why it’s disabled)?

**Note anything that felt hidden or confusing:**

---

### 7. Quick sanity checks

- [ ] **Header:** From dashboard, can you get to “Edit Profile” (onboarding) and Logout without hunting? After logout, are you clearly logged out and back on the landing page?
- [ ] **Help:** If you open the help bubble, can you report an issue or get to support/FAQ without dead ends?
- [ ] **Mobile (if you care):** Same journey on a phone — can you complete signup → onboarding → pay → dashboard without layout or tap targets getting in the way?

**Note:**

---

## Sign-off

| Check | Done? | Notes |
|-------|--------|-------|
| 1. Landing | | |
| 2. Login | | |
| 3. Onboarding | | |
| 4. Select plan | | |
| 5. Checkout → success | | |
| 6. Dashboard | | |
| 7. Sanity (header, help, optional mobile) | | |

**Common-sense verdict:** Could a first-time user go from landing to “I have my binder” without getting stuck or seriously confused?  
**Yes / No.** If No, what’s the main blocker?

---

## Reference: What’s in the product

- **Routes:** `/` (landing), `/login`, `/onboarding` (12 steps), `/select-plan`, `/checkout`, `/payment-success`, `/dashboard`, `/admin` (admin only), `/privacy`, `/terms`, `/support`.
- **Onboarding steps:** Home identity (ZIP, type required) → Binder goals → Features → Household → Critical locations → Emergency contacts → Service providers & utilities → Guest/sitter mode → Preferences → Output tone → Free notes → Review.
- **Global:** Header (logo, nav, Download PDF on dashboard, Account dropdown), footer (Support, Privacy, Terms), help bubble (report issue, email, FAQ).

Use this when you need to “find where in the app” something lives; the test above focuses on *experience*, not coverage of every screen.

---

*Last updated: March 2026*
