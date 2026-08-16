# DJ AI OS — Stripe Webhook Operations Runbook

**Purpose:** Document the Stripe CLI E2E verification procedure and `STRIPE_WEBHOOK_SECRET` rotation runbook for production deployment. This closes the **P0-5 OPS** gate.

---

## 1. Stripe CLI E2E Verification (Pre-Release / Post-Deploy Smoke Test)

### Prerequisites
- Stripe CLI installed: `brew install stripe/stripe-cli/stripe` (macOS) or download from https://stripe.com/docs/stripe-cli
- Local server running: `uvicorn app.server.run:app --reload` (or `python -m app.server.run`)
- Test Stripe account with test keys (`sk_test_...`, `whsec_...`)

### Step 1: Start Local Server with Test Keys
```bash
# Terminal 1: Start API server
export DJ_AI_OS_DATABASE_URL="sqlite+aiosqlite:///./test.db"
export DJ_AI_OS_INIT_DB="true"
export STRIPE_SECRET_KEY="sk_test_YOUR_TEST_KEY"
export STRIPE_WEBHOOK_SECRET="whsec_YOUR_TEST_WEBHOOK_SECRET"
uvicorn app.server.run:app --reload --port 8000
```

### Step 2: Forward Webhooks via Stripe CLI
```bash
# Terminal 2: Forward Stripe events to local server
stripe listen --forward-to localhost:8000/api/webhooks/stripe
```
> **Output example:** `> Ready! Your webhook signing secret is whsec_abc123...`
> **Copy the `whsec_...` secret** — set it as `STRIPE_WEBHOOK_SECRET` in Terminal 1 and restart the server.

### Step 3: Trigger Test Events
```bash
# Terminal 3: Trigger test events (one per event type)

# 1. Checkout completed → license issued
stripe trigger checkout.session.completed

# 2. Subscription created
stripe trigger customer.subscription.created

# 3. Subscription updated (plan change)
stripe trigger customer.subscription.updated

# 4. Subscription deleted → downgrade to DEMO
stripe trigger customer.subscription.deleted

# 5. Invoice payment failed → license suspended
stripe trigger invoice.payment_failed

# 6. Invoice payment succeeded → license reactivated
stripe trigger invoice.payment_succeeded
```

### Step 4: Verify Responses
Check Terminal 1 (server logs) for each event:
```
webhook.received type=checkout.session.completed action=ISSUE_LICENSE ok=true
webhook.received type=invoice.payment_failed action=LICENSE_SUSPENDED_PAYMENT_FAILED ok=true
webhook.received type=invoice.payment_succeeded action=LICENSE_REACTIVATED_PAYMENT_SUCCEEDED ok=true
...
```

### Expected Behavior by Event Type

| Event | Handler | DB Mutation | Notes |
|-------|---------|-------------|-------|
| `checkout.session.completed` | `_handle_checkout_completed` | `User` (if new) + `Subscription` + `License` (active) | Issues 12-month license, logs audit |
| `customer.subscription.created` | `_handle_subscription_created` | None (noop) | Creates local `Subscription` record |
| `customer.subscription.updated` | `_handle_subscription_updated` | `Subscription` (status/period) + `License` (reissue if plan changed) | Maps `price_id` → plan via `STRIPE_PRICES` |
| `customer.subscription.deleted` | `_handle_subscription_deleted` | `Subscription` (cancelled) + `License` (deactivated) + `MachineActivation` (deactivated) | Downgrades to DEMO |
| `invoice.payment_failed` | `_handle_payment_failed` | `License` (deactivated) + `MachineActivation` (deactivated) | **Suspends entitlements** |
| `invoice.payment_succeeded` | `_handle_payment_succeeded` | `License` (reactivated if was suspended) + `MachineActivation` (reactivated) | **Recovers entitlements** |

### Pass Criteria
- All 6 event types return `{"ok": true, "action": "..."}` from `/api/webhooks/stripe`
- No `500` errors in server logs
- DB state matches expected mutations above (verify via `sqlite3 test.db` or admin panel)

---

## 2. STRIPE_WEBHOOK_SECRET Rotation Runbook

### When to Rotate
- Secret suspected compromised (leaked in logs, CI, etc.)
- Scheduled rotation (quarterly recommended)
- Stripe dashboard → Webhooks → "Rotate secret" used

### Rotation Procedure (Zero-Downtime)

#### Step 1: Generate New Secret in Stripe Dashboard
1. Go to **Developers → Webhooks** in Stripe Dashboard
2. Click the webhook endpoint (`https://api.dj-ai-os.example/api/webhooks/stripe`)
3. Click **"Rotate secret"** → **Rotate immediately** or **Rotate in 24 hours**
4. Copy the **new** `whsec_...` secret

#### Step 2: Deploy New Secret to All Servers (Rolling)
```bash
# For each server / container / VM:
export STRIPE_WEBHOOK_SECRET="whsec_NEW_SECRET_FROM_DASHBOARD"
# Restart the API process (systemd, docker, etc.)
sudo systemctl restart dj-ai-os-api
# OR
docker compose restart api
```
> **Critical:** The code reads `STRIPE_WEBHOOK_SECRET` at call time (see `stripe_service.py:37`). **No code change, no redeploy required** — just env var + process restart.

#### Step 3: Verify Rotation
```bash
# Trigger a test event against production
stripe trigger checkout.session.completed --live
```
Check logs: `webhook.received type=checkout.session.completed action=ISSUE_LICENSE ok=true`

#### Step 4: Revoke Old Secret
- In Stripe Dashboard: wait for old secret to expire (or click "Revoke" if immediate rotation)
- Remove old secret from any secret manager (Vault, AWS Secrets Manager, etc.)

### Rollback Procedure
If new secret causes webhook failures:
```bash
export STRIPE_WEBHOOK_SECRET="whsec_OLD_SECRET"
# Restart API
sudo systemctl restart dj-ai-os-api
```
Then investigate (check logs for `INVALID_SIGNATURE` vs `WEBHOOK_SECRET_MISSING`).

---

## 3. Local Development Secrets Setup

### `.env.local` Template (never commit)
```bash
# Stripe test keys (from Stripe Dashboard → Developers → API Keys)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Database
DJ_AI_OS_DATABASE_URL=sqlite+aiosqlite:///./dj_ai_os_dev.db
DJ_AI_OS_INIT_DB=true
```

### GitIgnored Secret Files
```
vendor_private_key.pem        # Ed25519 private key for license/update signing (vendor machine ONLY)
dev.flag                      # Owner dev mode flag (local dev only)
.env                          # Production env (never commit)
.env.local                    # Local dev env (never commit)
```

---

## 4. Production Deployment Checklist

- [ ] `STRIPE_SECRET_KEY` (sk_live_...) set in production env / secret manager
- [ ] `STRIPE_WEBHOOK_SECRET` (whsec_...) set in production env / secret manager
- [ ] Stripe Dashboard webhook endpoint registered: `https://api.dj-ai-os.example/api/webhooks/stripe`
- [ ] Webhook events selected: `checkout.session.completed`, `customer.subscription.*`, `invoice.payment_failed`, `invoice.payment_succeeded`
- [ ] Stripe CLI E2E verification passed against staging
- [ ] Secret rotation documented in team runbook (this file)
- [ ] Monitoring alert on `webhook.received action=ERROR` or `INVALID_SIGNATURE` rate > 0

---

## 5. Code Reference (for auditors)

| File | Purpose |
|------|---------|
| `app/server/services/stripe_service.py` | Stripe API wrapper; reads `STRIPE_WEBHOOK_SECRET` from env at call time |
| `app/server/billing_service.py` | Webhook handler (`handle_webhook` + 6 `_handle_*` methods); idempotent via `WebhookEvent.id` PK |
| `app/server/db/models.py` | `WebhookEvent` (id, type, received_at, processed, payload_hash), `Subscription`, `License`, `MachineActivation`, `AuditLog` |
| `app/server/services/audit_service.py` | `log_audit()` — writes to `audit_log` table |

### Signature Verification Flow
```
POST /api/webhooks/stripe
  → BillingService.handle_webhook(raw_body, sig_header)
    → StripeService.construct_webhook_event()
      → stripe.Webhook.construct_event(raw_body, sig_header, self.webhook_secret)
        → raises SignatureVerificationError on bad sig
```

### Idempotency Flow
```
event.id = Stripe event ID (e.g., "evt_...")
WebhookEvent.id PK = event.id
SELECT WebhookEvent WHERE id = event.id → if exists: return DUPLICATE / EVENT_ALREADY_PROCESSED
```

### Replay Protection
- `payload_hash = sha256(raw_body)` stored in `WebhookEvent`
- Duplicate event with same ID but different payload → caught by PK constraint + hash mismatch (logged in audit)

---

## 6. Gap-1 Note (Deferred to V1.1+)

The code audit found `invoice.payment_failed` and `invoice.payment_succeeded` handlers **are implemented and functional** (they suspend/reactivate licenses + machine activations). No code change needed.

If billing GA at V1.0, the only remaining gate is **running the Stripe CLI E2E procedure above against a real Stripe test account** and confirming the 6 event types mutate DB state correctly.

---

*Generated: 2026-08-16 | Part of P0-5 OPS gate closure*