# Subscriptions and entitlements

Phase 18. Six subscription plans (free/premium-monthly/premium-yearly for
customers, free/professional-monthly/professional-yearly for artists),
backend-enforced feature entitlements and usage quotas, subscription
checkout/renewal/cancellation/expiration/grace-period lifecycle, billing
history, and coupon validation/redemption. Builds on the Phase 2 schema
scaffolding (`SubscriptionPlan`, `Subscription`, `Coupon`,
`CouponRedemption`) and Phase 15's payment infrastructure.

## 1. Plan definitions

`app/db/models/subscription.py::SubscriptionPlan` — `target_role`
(`customer`/`artist`), `price_amount` (decimal major units — see §17),
`billing_interval` (`monthly`/`yearly`), and a `features` JSONB bag read by
every entitlement check in this phase. The six required plans are seeded by
a data migration (`migrations/versions/f1c8a37e5b04_seed_subscription_
plans.py`, mirroring `a4708e2fb0ee_seed_basic_categories.py`'s precedent):

| Plan | `target_role` | `billing_interval` | `features` |
| --- | --- | --- | --- |
| Free | customer | monthly | `premium_design_access: false, download_limit_per_month: 5, ai_credits_per_month: 3` |
| Premium Monthly | customer | monthly | `premium_design_access: true, download_limit_per_month: 100, ai_credits_per_month: 50` |
| Premium Yearly | customer | yearly | same features as Premium Monthly |
| Free Artist | artist | monthly | `portfolio_limit: 10, download_limit_per_month: 5, ai_credits_per_month: 3` |
| Professional Monthly | artist | monthly | `portfolio_limit: null (unlimited), download_limit_per_month: 200, ai_credits_per_month: 100` |
| Professional Yearly | artist | yearly | same features as Professional Monthly |

A user with no `Subscription` row at all (never subscribed) is treated
identically to being on their role's free plan —
`app/services/entitlements.py::_DEFAULT_CUSTOMER_FEATURES`/
`_DEFAULT_ARTIST_FEATURES` mirror the seeded free plans exactly, so no call
site needs to special-case "no row yet" versus "on the free plan."

## 2. Feature entitlements and usage quotas

`app/services/entitlements.py` is the single place every entitlement check
goes through — routes never trust a client-sent "am I premium?" flag; they
call this module, which re-derives the caller's plan from the database
every time.

- `get_active_subscription()` — the user's `active` or `past_due` (grace
  period, still entitled — see §9) subscription, if any.
- `get_effective_features()` — that subscription's plan `features`, or the
  role's free-tier default.
- `check_and_increment_usage()` — atomically checks a numeric feature
  (e.g. `download_limit_per_month`) against a `UsageRecord` counter for the
  current calendar month and increments it, raising if the caller is
  already at their limit. A `None` limit (e.g. a professional artist's
  `portfolio_limit`) means unlimited — no counter is ever created for it.
- `require_premium_design_access()` / `require_portfolio_capacity()` —
  boolean/count-threshold checks with no counter of their own.

`UsageRecord` (`app/db/models/usage.py`) is one row per
`(user_id, usage_type, period_start)`, uniquely constrained so a race
between two concurrent requests can't double-count. The usage period is a
plain **calendar month**, independent of any subscription's own billing
anchor date — a free-tier user with no subscription at all still gets a
well-defined monthly download/AI-credit quota.

## 3. Subscription checkout reuses payments

There is no separate recurring-billing integration. `POST /subscriptions/
checkout` creates a `Payment` row exactly like a booking payment does
(`app/services/subscriptions.py::create_subscription_checkout`), except
`payments.subscription_id` is set instead of `payments.booking_id` — a new
`exactly_one_parent` check constraint (migration
`d4a29f8b6c31_subscriptions_and_entitlements.py`) guarantees a payment is
attributed to exactly one of the two, never both, never neither.

This means subscription checkout gets every guarantee booking payments
already have for free: server-side amount determination, idempotency
keys, signed-webhook settlement, and reconciliation — see
docs/payments.md. `app/services/payments/service.py::_settle_payment()`
branches on `payment.subscription_id` and calls
`activate_or_renew_subscription()`/`handle_failed_subscription_payment()`
(§4/§5) instead of the booking-earning/commission path — subscription
revenue isn't attributed to any one artist, so no `ArtistEarning` is
created for it.

**First checkout** creates a new `Subscription` row in `trialing` (the
model's own pre-existing default status) with a placeholder period; it only
becomes `active` — and only then does
`app/core/authz.py::get_effective_role()` grant `premium_customer`/the
plan's entitlements — once a webhook confirms the payment succeeded.
**A later checkout while already trialing/active/past_due** reuses the same
`Subscription` row (a renewal or plan change), rather than creating a
second membership.

## 4. Renewal

There is no automatic recurring charge — the Razorpay integration here is
an Order-API integration (see docs/payments.md#1-2), not the separate
Subscriptions/e-mandate API a fully automatic recurring charge would
require. A renewal is a fresh `POST /subscriptions/checkout` call for the
same plan; the "renewal webhook" is the same
`POST /webhooks/payments/razorpay` endpoint every payment settles through.
On success, `activate_or_renew_subscription()` chains the new period from
wherever the *previous* period ended (not from "now"), so a renewal paid a
few days early or late never shifts the customer's billing anchor date.

`app/services/subscriptions.py::process_due_subscriptions()` is the
foundation function that notices a subscription's period has actually
elapsed with no renewal payment and moves it into grace period (§9) or
expires it (§8) — see §6 for why this, like payment reconciliation, is a
manually/externally-triggered command rather than a real scheduler.

## 5. Failed renewal

A `payment.failed` webhook for a subscription payment calls
`handle_failed_subscription_payment()`:

- If the subscription was still `trialing` (never activated), it goes
  straight to `expired` — there's no active membership to protect with a
  grace period.
- If it was `active`/`past_due` (a renewal charge failed), it moves to
  `past_due` and `grace_period_ends_at` is set to
  `now + subscription_grace_period_days` (default 3, `app/core/config.py`).

## 6. Cancellation

`POST /subscriptions/me/cancel` sets `cancel_at_period_end = true` — the
existing `Subscription.cancel_at_period_end` column (Phase 2 schema) was
already shaped for exactly this. `status` itself does not change at
cancellation time (access continues through the already-paid-for period),
so no `SubscriptionStatusHistory` row is written for the cancel action
itself — the audit log (`subscription.cancelled`) records *that* the user
asked to cancel; status history (§10) only records actual status
transitions, which happen later once the period actually ends (§8).

## 7. Expiration

Handled uniformly by `process_due_subscriptions()`, invoked via
`python -m app.cli.process_subscriptions [--dry-run]` — mirrors
`app/cli/reconcile_payments.py` exactly, including the "no scheduler exists
in this environment yet" caveat (docs/payments.md#10). Two transitions:

1. An `active` subscription whose `current_period_end` has passed:
   - `cancel_at_period_end = true` → `expired`.
   - Otherwise (no renewal payment arrived in time) → `past_due` + a fresh
     grace period (§9).
2. A `past_due` subscription whose `grace_period_ends_at` has passed with
   no successful renewal → `expired`.

## 8. Grace period

`SubscriptionStatus` has no dedicated "grace period" value — `past_due` *is*
the grace period, reusing Stripe's own naming convention for the same
concept. `Subscription.grace_period_ends_at` (new column, this phase's
migration) is the only new piece of state: entitlements stay active for a
`past_due` subscription (`app/services/entitlements.py::_ENTITLED_STATUSES`
includes it), and `process_due_subscriptions()` (§7) is what eventually
expires it once the window elapses.

## 9. Billing history and status history

Two distinct, deliberately separate records:

- **Billing history** (`GET /subscriptions/me/billing-history`) — the
  user's `payments` rows where `payment_type = 'subscription'`. This is
  "what did I pay, when, and did it succeed."
- **Status history** (`GET /subscriptions/{id}/status-history`) —
  `SubscriptionStatusHistory` (new table, mirrors `BookingStatusHistory`
  exactly: append-only, `from_status`/`to_status`/`reason`/`changed_by`).
  This is "how did this membership's status change over time" — every
  `active → past_due → expired` (or `→ active` on renewal) transition is
  recorded here, independent of which payment (if any) caused it.

## 10. Coupons

`Coupon`/`CouponRedemption` (Phase 2 schema) were booking-shaped
(`min_booking_amount`, `booking_id`). This phase adds a nullable
`CouponRedemption.subscription_id`, parallel to the existing nullable
`booking_id`, so a redemption can be attributed to either kind of checkout.

**Validation** (`POST /coupons/validate`,
`app/services/coupons.py::price_coupon`) only *previews* a discount against
a specific plan's price — it never redeems, so checking a mistyped code
doesn't burn the one-per-user redemption. It checks `is_active`,
`valid_from`/`valid_until`, and `max_redemptions` vs. `redemption_count`,
then computes the discount server-side (percentage or fixed amount) —
never trusting a client-computed number.

**Redemption abuse prevention** is enforced at two layers:

1. The pre-existing `uq_coupon_redemptions_coupon_user` unique constraint
   (Phase 2 schema) — the database itself is what stops the same user
   redeeming the same coupon twice, even across a race between two
   concurrent requests (`redeem_coupon()` inserts first and treats a
   unique-constraint conflict as "already redeemed," the same
   insert-first-then-treat-conflict-as-done pattern
   `app/services/payments/service.py::handle_webhook` uses for webhook
   dedup).
2. `redeem_coupon()` is called from `create_subscription_checkout()` at
   order-creation time (not payment-success time) — a deliberate
   simplification: if the checkout's payment later fails, the coupon has
   still been "used" without benefit. This is an accepted rough edge, not
   an abuse gap — the requirement is "prevent repeated abuse of the same
   coupon," which the unique constraint already guarantees unconditionally.

**Staff management**: `Coupon.created_by` (Phase 2 schema) implied
staff-authored coupons, but no CRUD surface existed anywhere until
`app/api/routes/admin_coupons.py` (admin/super_admin only, mirrors
`admin_tags.py`'s shape — the same "first place this table gets a route"
situation).

## 11. Premium-design access

`Design.is_premium` (existing column) gates full-resolution *viewing*, not
just downloading. `GET /designs/{id}` computes `premium_locked` (new
`DesignOut` field): `false` for the owner/staff or a non-premium design,
otherwise `true` unless the viewer's `get_effective_features()` has
`premium_design_access: true`. When locked, `image_url`/
`thumbnail_medium_url` are withheld from every `DesignImageOut` (only
`thumbnail_small_url` — the existing gallery-card thumbnail — is returned),
so browsing/discovery still works but the full image requires premium.

## 12. Download limits

A separate, distinct gate from §11: `POST /designs/{id}/download` requires
premium access *if* the design is premium, and — for every design,
premium or not — consumes one unit of the caller's `download_limit_per_month`
quota via `check_and_increment_usage()`. A free customer can still download
their `download_limit_per_month` allotment of non-premium designs; a
premium subscriber gets a higher limit *and* premium designs.

## 13. AI-credit foundation

`app/services/ai.py::create_ai_generation()` — quota-gated
(`ai_credits_per_month`) logging of an `AiGeneration` row (Phase 2 schema).
No real AI-provider call exists anywhere in this codebase yet; this mirrors
the project's established "foundation, not full automation" precedent
(`app/services/payments/service.py::create_payout_batch` is the same shape
— real record-keeping, no external integration). `POST /ai/generations`
is the first route this table has ever had.

## 14. Artist portfolio limits

Enforced at the one place a design's status actually becomes `published`:
`PATCH /designs/{id}` with `status: "published"`. Before applying the
transition, the route counts the artist's current published (non-deleted)
designs and calls `require_portfolio_capacity()` against the *design
owner's* plan (resolved via `_owning_user_id()`, not necessarily the
caller — staff can edit on an artist's behalf). Designs are always created
as `draft` (no `status` field on `DesignCreateRequest`), so this is the
only enforcement point needed; there's no separate "publish" endpoint to
duplicate the check in.

## 15. Why `price_amount` stays decimal

`SubscriptionPlan.price_amount` is `Numeric(10,2)` (decimal major units),
*not* converted to the integer-minor-unit ledger convention
`payments.amount` uses (docs/payments.md#7). This isn't an inconsistency —
it's the same distinction docs/payments.md#7 already draws for
`bookings.total_amount`/`artist_services.price_amount`: a **list price** a
human reads is a different domain from **money that actually moved through
a provider**. `price_amount` is converted to integer minor units (with the
coupon discount applied) only at the moment `create_subscription_checkout`
creates the `Payment` row — the same `to_minor_units()` conversion booking
checkout already does.

## 16. Client implementations

- **Web** (`apps/web`) — `/pricing` (plan browsing, checkout via the same
  Razorpay Checkout JS flow booking payments use — the loader/types are now
  shared in `src/lib/razorpay-checkout.ts` rather than duplicated),
  `/account/subscription` (status, cancel, billing/status history), a
  coupon-code field at checkout, and premium-lock/download UI on the design
  detail page.
- **Mobile** (`apps/mobile`, Flutter) — plan browsing and subscription
  status/cancel/billing-history screens (`lib/features/subscriptions/`),
  plus premium-lock messaging and a download action on the design detail
  screen. **No in-app checkout**: no payment SDK exists anywhere in this
  Flutter app yet (booking payments don't integrate Razorpay natively
  either — see docs/booking-lifecycle.md#7-client-implementations, which
  already pushes payment flows to the web app), so subscribing to a paid
  plan directs the user to the web checkout rather than adding native
  Razorpay integration as new native-platform surface just for this one
  flow.
- **Staff** (`apps/admin`) — out of scope for this phase; coupon management
  got a route (`admin_coupons.py`) but no dashboard module, consistent with
  Phase 18's request being scoped to subscriptions/entitlements rather than
  an admin-dashboard expansion (that was Phase 17's scope).

## 17. What Phase 18 deliberately does not do

- No real recurring-billing/e-mandate integration (§4) — renewal is a
  fresh checkout, not an automatic provider-initiated charge.
- No scheduler for expiration/grace-period processing (§7) — a standalone
  CLI command, same constraint payment reconciliation already has.
- No in-app mobile checkout (§16) — deferred to the web app.
- No admin dashboard module for coupons/plans — a route exists for staff
  coupon CRUD, but no `apps/admin` UI.

## 18. Related documents

- docs/payments.md — the payment-order/webhook/reconciliation machinery
  subscription checkout reuses.
- docs/database-schema.md — Phase 2's original `SubscriptionPlan`/
  `Subscription`/`Coupon`/`CouponRedemption` scaffolding.
- docs/design-catalog.md — `Design.is_premium` and the image pipeline §11
  gates.
- docs/migration-guidelines.md — the schema-vs-data-migration split this
  phase's two migrations (`d4a29f8b6c31_...`/`f1c8a37e5b04_...`) follow.
