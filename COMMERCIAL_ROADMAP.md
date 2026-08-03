# DJ AI OS Commercial Roadmap

## Product Revenue Model

DJ AI OS should become a licensed desktop client connected to a cloud control
plane. The desktop app handles local audio analysis and DJ workflow. The server
handles accounts, license activation, subscription billing, cloud archive
permissions, trend data, and optional heavy AI jobs.

## Plans

### Demo
- Limited local analysis.
- AI Ear preview.
- No Rekordbox export.
- No DJ archive downloads.

### Pro
- Larger library limits.
- AI Ear and Set Builder.
- Rekordbox/USB preparation.
- Cloud trend radar.

### DJ Archive
- Everything in Pro.
- Monthly DJ archive packs.
- Cloud catalog updates.
- Archive download entitlement.

### Studio
- Multi-DJ/team account.
- Admin permissions.
- Shared cloud library rules.
- Venue/event workflows.

### Enterprise
- Custom licensing.
- Venue chains, agencies, DJ schools.
- Private cloud archive and custom AI model policy.

## Server Modules

1. Account service: users, devices, machine activations.
2. Billing service: Stripe/Paddle/iyzico/PayTR checkout and webhooks.
3. License service: signed license tokens, expiry, plan, entitlements.
4. Cloud archive service: monthly packs, manifests, signed URLs, checksums.
5. Trend service: partner/official data connectors and curated DJ charts.
6. AI service: optional server-side analysis and recommendation jobs.
7. Admin portal: users, subscriptions, packs, licenses, audit log.

## Security Rules

- Never trust client-only plan checks for paid downloads.
- Every paid cloud download must be checked server-side.
- Signed download URLs should expire quickly.
- License tokens should include machine id, plan, expiry, and entitlements.
- Payment webhooks should be the source of truth for subscription state.

## Next Engineering Step

Build a small FastAPI backend prototype with:
- `/activate`
- `/entitlements`
- `/checkout`
- `/cloud/packs`
- `/cloud/packs/{id}/download`

The desktop app already has local stubs that can be replaced by these endpoints.

## Backend Prototype

The first local backend prototype lives in `app/server`.

Run target after installing requirements:

```powershell
uvicorn app.server.api:app --reload --port 8080
```

Initial endpoints:

- `GET /health`
- `POST /activate`
- `POST /entitlements`
- `POST /checkout`
- `POST /cloud/packs`
- `POST /cloud/packs/{pack_id}/download`

Production hardening still needed:

- Replace dev license secret with server-only secret storage.
- Store users, devices, subscriptions, and issued licenses in Postgres.
- Validate payment provider webhooks with provider signatures.
- Generate real signed CDN URLs for cloud archive downloads.
- Add admin dashboard and audit log.
