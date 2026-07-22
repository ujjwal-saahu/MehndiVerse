# MehndiVerse — Payment Architecture and Booking Payments (Phase 15)

Status: Implemented (Phase 15)
Last updated: 2026-08-02

Booking deposits and payments, built on the `payments`/`refunds`/`payouts` schema that has existed since Phase 2 but had nothing writing to it until now. See [booking-lifecycle.md](booking-lifecycle.md) for the booking state machine this phase's deposit payment finally drives (`deposit_pending → deposit_paid`, previously only reachable by calling the service layer directly in tests).

## 1. Payment-provider abstraction

`app/services/payments/base.py` defines `PaymentProvider` (an `ABC`) plus normalized dataclasses (`ProviderOrder`, `ProviderWebhookEvent`, `ProviderPaymentStatus`, `ProviderRefund`) so every concrete provider speaks the same shape regardless of its own API's quirks. `app/services/payments/factory.py::get_payment_provider()` is the only place that picks a concrete implementation, keyed off `settings.payment_region` (default `"IN"`) with `settings.payment_provider` as an explicit override — mirrors `app/services/search/factory.py`'s exact shape (Phase 8), down to "adding a provider for another region never requires changing route or service code, only the factory's mapping and the new provider module."

## 2. Sandbox integration: Razorpay

MehndiVerse is India-first (INR throughout, Indian phone/address formats), so the "IN" region's provider is **Razorpay** — India's dominant gateway, with a well-documented test mode (`rzp_test_...` keys hit the exact same API as production, no separate sandbox host). `app/services/payments/razorpay_provider.py` is a thin `httpx` wrapper, not the Razorpay Python SDK, mirroring `app/integrations/supabase_storage.py`'s established pattern — this keeps the HTTP boundary trivial to test with `respx` (already a dev dependency) and keeps this module the *only* place `razorpay_key_secret` is ever read.

Credentials (`razorpay_key_id`, `razorpay_key_secret`, `razorpay_webhook_secret`) come from `Settings` (env vars via `apps/api/.env`, never committed) — see `app/core/config.py`. Non-functional placeholder defaults ship in source (`rzp_test_placeholder`, etc.), the same convention already used for the Supabase secrets. **`razorpay_key_id` is not a secret** — it's the publishable identifier Razorpay's client-side Checkout needs, deliberately returned to the browser/app in `ProviderOrder.provider_key_id`; `razorpay_key_secret` and `razorpay_webhook_secret` never leave the backend.

## 3. Payment order creation, deposits, and full payments

`app/services/payments/service.py::create_payment_order()` is the single entry point. For a given `payment_type` (`deposit`/`full`/`balance`):

1. **Idempotency** (§6) and **existing-order reuse** are checked first — a retried "pay" click or an already-PENDING order for the same purpose returns the existing `Payment` row rather than creating a second live order with the provider. An already-`succeeded` payment of that type is rejected (409).
2. **The amount is always derived from the booking's own stored state** (`determine_payment_amount_minor()`), never accepted from the client (§4): `deposit` requires `deposit_pending` + `booking.deposit_amount`; `full` requires `confirmed` + `booking.total_amount`; `balance` requires `deposit_paid` and computes `total − Σ(succeeded payments)`.
3. `provider.create_order()` is called, and a `Payment` row is inserted with `status=pending`, `provider_order_id` set (the only id known at this point — see §3a), `provider_payment_id` left `NULL`.

### 3a. `provider_order_id` vs. `provider_payment_id`

An order can accumulate multiple payment *attempts* (a declined card, then a successful retry) — the order id is known immediately, but which specific payment attempt actually succeeded is only known once a webhook or reconciliation poll reports it. `payments.provider_order_id` (unique, set at creation) and `payments.provider_payment_id` (unique, nullable, set once settled) are deliberately two separate columns, not one column re-purposed over time.

### 3b. Payment status

`GET /bookings/{id}/payments` / `GET /bookings/{id}/payments/{payment_id}` — read-only, party-authorized (§2 below is about webhooks; booking-party authorization is the same 403-for-third-parties check duplicated across `bookings.py`/`messaging.py`/`payments.py`).

### 3c. Payment receipts

`GET /bookings/{id}/payments/{payment_id}/receipt` — a structured JSON receipt (amount, currency, paid-at, provider reference, artist/service context), available only once a payment has actually `succeeded` (422 otherwise). Not a PDF/emailed document this phase — a foundation-level structured view a future phase can render into a downloadable document without changing what data is available.

## 4. Never trust client-reported success

The client is never the source of truth for "did this payment succeed." A `Payment` only ever transitions out of `pending` inside `_settle_payment()`, called from exactly two places:

- The **webhook** dispatcher (§5), after signature verification.
- **Reconciliation** (§10), which asks the provider's own API directly.

There is no endpoint anywhere that lets a client (or even an authenticated party) directly set a payment's status. The web client's Razorpay Checkout `handler` callback (fired client-side the instant Razorpay's widget reports success) is treated only as a cue to start polling `GET .../payments/{id}` — the UI shows "awaiting confirmation" until *our backend* reports a non-pending status, never before.

**Server-side amount validation** is the other half of this: `_settle_payment()` compares the webhook/reconciliation-reported amount against the `Payment.amount` recorded at order-creation time. A mismatch does not credit the payment — it's marked `failed` with a descriptive `failure_reason` and a `payment.amount_mismatch` audit event, and reconciliation/webhook processing moves on. Nothing about this phase makes the *creation-time* amount trustable from the client either (§3, point 2) — the two checks compose: the amount can never be client-influenced going in, and it's re-validated against the provider's own report coming out.

## 5. Signed webhook handling and duplicate protection

`POST /webhooks/payments/razorpay` is the only unauthenticated-by-session route in the app — authenticity comes entirely from `RazorpayProvider.verify_webhook_signature()`, an HMAC-SHA256 of the raw request body (read via `await request.body()` before any JSON parsing — signature verification must run against the exact bytes the provider signed) compared with `hmac.compare_digest` (constant-time; a naive `==` would leak timing information about how many leading bytes matched). A missing or invalid signature is rejected with 400 before the payload is even parsed.

**Duplicate webhook processing** is prevented by `payment_webhook_events`, a ledger with a `UNIQUE(provider, event_type, provider_reference)` constraint — the *database itself* is what makes a replayed delivery a no-op: the second insert attempt fails uniqueness, and `handle_webhook()` treats that as "already handled" and returns 200 without touching anything else. This insert is wrapped in `db.begin_nested()` (a `SAVEPOINT`) — the same "insert first, treat a unique-constraint conflict as already-done" pattern as `app/services/engagement.py::like_design()` (Phase 6) — so a duplicate delivery unwinds only that one insert, not the whole request's transaction. (An earlier version of this code called a bare `db.rollback()` on the conflict, which — caught by `test_duplicate_webhook_delivery_is_only_processed_once` — was rolling back the *entire* transaction rather than just the failed insert; switching to a SAVEPOINT fixed it.)

## 6. Idempotency keys

A client may pass `idempotency_key` when creating a payment order; `payments.idempotency_key` is unique, and a repeated request with the same key returns the original `Payment` row rather than creating a second order — standard practice for any endpoint that starts an external side effect (mirrors how a real payment provider's own API works, e.g. Stripe's `Idempotency-Key` header).

## 7. Integer minor currency units

Every money column touched by this phase — `payments.amount`, `refunds.amount`, `payouts.amount`, `artist_earnings.{gross,commission,net}_amount` — is `Integer`, storing minor units (paise, not rupees), not `Numeric`/float major units. This is what every payment provider's own API actually speaks (Razorpay's `amount` field is paise), and it sidesteps floating-point rounding entirely for money math. The Phase 2 schema originally stored these as `Numeric(12,2)` major-unit decimals; this phase's migration converts them (`amount * 100`, with the reverse `/100` in the downgrade). Booking-level "list price" fields (`bookings.total_amount`/`deposit_amount`, `artist_services.price_amount`) are unchanged, decimal major units — that's a human-facing quoting concern from Phases 11/13, a different domain from the integer-minor-unit ledger this phase introduces for money that actually moves through a provider.

## 8. Platform commission and artist earnings

`app/services/payments/commission.py::calculate_commission()` is a pure function — no I/O, trivially unit-testable — that splits a gross amount by `settings.platform_commission_percent` (default 15%), rounding the commission to the nearest minor unit and computing the net as the exact remainder (`commission + net == gross`, always, by construction — never two independently-rounded values that could drift by a paisa).

Every time `_settle_payment()` credits a payment, it computes this split and writes it onto the `Payment` row (`commission_amount`/`net_amount`) *and* inserts an `ArtistEarning` row (`gross_amount`/`commission_amount`/`net_amount`, one per payment — `payment_id` is unique). This is the artist's running ledger of what they're owed, independent of whether it's been paid out yet (§9).

## 9. Payout-record foundation

`create_payout_batch()` groups every `ArtistEarning` row for an artist that hasn't yet been assigned to a `Payout` (`payout_id IS NULL`) into a single new `Payout` (`status=pending`, `amount` = the sum of `net_amount`s), and stamps `payout_id` onto each included earning. **No actual bank transfer happens** — this is explicitly a foundation, the same "record-keeping now, execution later" scope already used for push/email notifications (Phase 14) and the reminder function (Phase 14). Staff-triggered via `POST /admin/payments/artists/{id}/payouts` (`admin`/`super_admin` only).

## 10. Reconciliation command

`python -m app.cli.reconcile_payments [--older-than-minutes N] [--dry-run]` — cross-checks every `payments` row still `pending` for at least `N` minutes (default 15) against `provider.get_order_status()` (a direct provider-API call, never the client) and settles it through the exact same `_settle_payment()` webhooks use. This is the fallback for a webhook delivery that was lost, delayed, or never sent — "confirm payment through a verified webhook **or provider API**" is satisfied by these two call sites sharing one settlement function, not by two different code paths that could disagree. No scheduler exists in this environment to run it periodically yet (no cron/task-queue infrastructure has been built in any earlier phase) — it's a standalone script for now, intended for periodic external invocation.

## 11. Refunds

A party (customer or the artist) may **request** a refund (`POST /bookings/{id}/payments/{payment_id}/refund`) on any `succeeded`/`partially_refunded` payment — this only creates a `Refund` row (`status=pending`); it does not move money. Only staff (`admin`/`super_admin`) can **approve** it (`POST /admin/payments/refunds/{id}/approve`) — approval is the point an actual provider API call happens (`provider.create_refund()`), so it's staff-gated rather than self-service, unlike the request step. Approval sets `status=approved` and records `provider_refund_id`; the refund only reaches its true terminal `processed` state once the `refund.processed` webhook confirms it (mirroring §4's "never trust anything but a verified webhook/provider-API report" for refunds too) — at which point the parent `Payment.status` becomes `refunded` or `partially_refunded` depending on how much of it has been refunded in total. Staff may also **reject** a pending refund request directly (no provider call needed).

## 12. Financial audit events

Every state-changing action in this phase (order created, payment succeeded/failed/amount-mismatched, refund requested/approved/rejected/processed, payout created) writes an `audit_logs` row (the generic table from Phase 10's artist-verification audit trail — not a payments-specific table) via a local `_record_audit()` helper. Unlike `app/services/audit.py::record_audit_log()` (which expects a live HTTP `Request` for `ip_address`/`user_agent`), most of this phase's events are webhook- or system-triggered, so this helper omits those fields rather than forcing a fake request context.

## 13. Never storing card details

No card field exists anywhere in this schema, and none ever will by construction: Razorpay's Checkout collects card/UPI/netbanking details entirely within their own hosted widget (loaded client-side via their `checkout.js`, initialized with only the publishable `provider_key_id` and `provider_order_id` — both non-secret), and reports back only a payment/order/signature triple our backend re-verifies. The backend never receives, transmits, or has any code path capable of accepting a raw card number, CVV, or expiry.

## 14. Client implementation

- **Web**: a `BookingPayments` component embedded in the booking detail page — triggers order creation for whichever `payment_type` the booking's current status allows, loads Razorpay's `checkout.js` and opens their hosted widget with the returned (non-secret) key id and order id, then polls our own backend (never Razorpay's client-side callback) until the payment is actually settled. Payment history, receipts, and refund requests are shown inline.
- **Admin web UI** (refund approval/rejection, payout-batch triggering) was **not** built this phase — the backend endpoints exist and are fully tested, but no dedicated staff-facing page consumes them yet, a deliberate scope cut given this phase's overwhelming emphasis on backend architecture/security correctness.
- **Flutter**: **deferred entirely this phase.** Completing an actual Razorpay payment on mobile requires either Razorpay's native Flutter SDK (not currently a pubspec dependency) or a WebView bridge to their hosted checkout — a meaningfully larger lift than the web integration (which only needed a `<script>` tag), and not justified on top of the backend work this phase already required. A future phase can add the mobile checkout integration without touching any backend code — the provider abstraction and every endpoint here are client-agnostic.

## 15. What Phase 15 deliberately does not do

No real payout execution (bank transfer) — §9 is a record only. No scheduler for reconciliation (§10) or reminders (Phase 14) — both are standalone functions awaiting a future task-queue phase. No partial/split refunds beyond "the remaining refundable amount" (a refund request always targets the full remaining balance, not an arbitrary sub-amount). No SMS/webhook-delivery-status dashboard. No support for a second payment provider (the abstraction is ready for one; only Razorpay is implemented). No admin payments web UI (§14). No mobile checkout (§14).

## 16. Related documents

- [booking-lifecycle.md](booking-lifecycle.md) — the booking state machine the deposit payment drives (`deposit_pending → deposit_paid`)
- [booking-messaging.md](booking-messaging.md) — the `notify_user()` fan-out this phase's payment/refund events also use, and the audit-log pattern reused for financial events
- [artist-directory.md](artist-directory.md) — `ArtistService.deposit_required`/`deposit_amount`, which determine whether a booking ever enters `deposit_pending` at all
