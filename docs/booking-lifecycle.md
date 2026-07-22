# MehndiVerse — Booking System (Phase 13)

Status: Implemented (Phase 13)
Last updated: 2026-07-19

This is the source of truth for the booking request lifecycle — draft, submission, artist review, quoting, confirmation, cancellation, and reschedule. It supersedes the Phase 2 placeholder in [booking-status-rules.md](booking-status-rules.md). **Payments remain disabled this phase** — no HTTP endpoint moves money or triggers `deposit_paid`; those hooks exist in the state graph for a future payments phase to wire up.

## 1. States

| Status | Meaning | Terminal? |
|---|---|---|
| `draft` | Customer is filling in a request; not yet visible to the artist. | No |
| `requested` | Submitted; awaiting the artist's response. | No |
| `artist_reviewing` | Artist has opened the request (inbox triage signal). | No |
| `quotation_sent` | Artist sent a quote; awaiting the customer's decision. | No |
| `customer_reviewing` | Customer is actively reviewing a sent quote. | No |
| `confirmed` | Customer accepted a quote that needs no deposit. | No |
| `deposit_pending` | Customer accepted a quote whose service requires a deposit; awaiting payment (future phase). | No |
| `deposit_paid` | Deposit payment succeeded (future phase — unreachable via any endpoint this phase). | No |
| `in_progress` | The appointment is underway. | No |
| `completed` | Service delivered. | No — see §1a |
| `cancelled` | Cancelled by either party. | **Yes** |
| `rejected` | Artist declined the request, or customer declined a quote. | **Yes** |
| `refund_requested` | Customer requested a refund after completion (future phase). | No |
| `refunded` | Refund processed (future phase). | **Yes** |
| `disputed` | Either party raised a dispute. | No |

### 1a. Why `completed` isn't a dead end here

Unlike the Phase 2 draft model, `completed → refund_requested` is a valid edge — a customer can raise a post-completion refund request, and admin resolution (`refund_requested → refunded` or back to `completed` if denied) is a later phase's concern to build UI for. `TERMINAL_BOOKING_STATUSES` (app/db/enums.py) is derived automatically from "has no outgoing transitions," so this is self-consistent rather than hardcoded in two places.

## 2. Transition table

Full graph in `app/db/enums.py::BOOKING_STATUS_TRANSITIONS`. Summary:

```
None            -> draft
draft           -> requested, cancelled
requested       -> artist_reviewing, quotation_sent, rejected, cancelled
artist_reviewing-> quotation_sent, rejected, cancelled
quotation_sent  -> customer_reviewing, confirmed, deposit_pending, rejected, cancelled
customer_reviewing -> confirmed, deposit_pending, rejected, cancelled
confirmed       -> deposit_pending, in_progress, cancelled, disputed
deposit_pending -> deposit_paid, cancelled, disputed
deposit_paid    -> in_progress, cancelled, disputed
in_progress     -> completed, cancelled, disputed
completed       -> refund_requested
refund_requested-> refunded, completed
disputed        -> completed, cancelled, refunded
cancelled, rejected, refunded -> (terminal)
```

Every status is reachable from `None`; every terminal status genuinely has zero outgoing edges — both are asserted directly by `tests/db/test_booking_transitions.py`, walking the graph rather than hardcoding the reachable set.

## 3. Explicit state-transition service

`app/services/booking.py::transition_booking()` is the **only** place `bookings.status` is ever assigned. It validates the hop against `is_valid_booking_transition()` (422 if invalid) and writes a `booking_status_history` row in the same call — so the audit trail and the current status can never drift apart. Every higher-level action (`submit_booking`, `send_quote`, `accept_quote`, `reject_quote`, `cancel_booking`) calls it exactly once for its one real status change.

Actions that touch the audit trail *without* changing status — reschedule is the only one this phase — use the sibling `record_history_note()`, which writes a `from_status == to_status` row directly. This is deliberate: self-loops are excluded from the transition table (so `QUOTATION_SENT → QUOTATION_SENT` is correctly rejected by `transition_booking()` if ever attempted), and a reschedule genuinely isn't a status change.

## 4. Booking draft and submission

A booking starts as a `draft` (`POST /bookings`, needs only `artist_profile_id`) that the customer fills in incrementally (`PATCH /bookings/{id}`) — service, event type, date/time, location, number of customers, design preferences, notes, budget range, and contact details are all optional at this stage. `POST /bookings/{id}/submit` enforces `missing_submission_requirements()` (service, date, location type +address-if-needed, contact name/email/phone) before allowing `draft → requested`, mirroring `app/services/artist_verification.py`'s `missing_submission_requirements` precedent exactly.

Inspiration images attach via `POST /bookings/{id}/attachments` (multipart, reusing the same `process_image_upload`/public-`portfolio`-bucket pipeline as artist profile images — see `app/api/routes/artist_onboarding.py`), producing a `BookingAttachment` row.

## 5. Artist inbox, quotes, and confirmation

`GET /artist/bookings` lists all non-draft bookings for the artist's own profile (drafts are invisible to the artist — they're the customer's private scratch space until submitted). `POST /artist/bookings/{id}/review` is an optional triage signal (`requested → artist_reviewing`).

`POST /artist/bookings/{id}/quotes` serves both **quote creation** and **quote revision** from one endpoint: if the booking has no other pending quote yet, it's a creation (transitions `requested`/`artist_reviewing` → `quotation_sent`); if a quote is already pending (booking already `quotation_sent`/`customer_reviewing`), the old quote is marked `superseded` and the booking's status doesn't change again — this is what "revision" means. Only one quote is ever `pending` at a time per booking, enforced here at the service layer (not a DB constraint, per the Phase 2 docstring on `BookingQuote` this phase finally acts on).

**Quote acceptance** (`POST /bookings/{id}/quotes/{quote_id}/accept`) is where a request turns into a real calendar commitment:

1. Reject if the quote isn't `pending` or has expired (`valid_until`).
2. **Lock** the artist's `ArtistProfile` row (`SELECT ... FOR UPDATE`) for the rest of the transaction — see §6.
3. **Re-validate availability** (§5a) against the artist's *current* weekly rules and blocked dates — they may have changed since the quote was sent.
4. **Check for overlap** against other bookings that already occupy the calendar (§6).
5. Land on `confirmed` if the service doesn't require a deposit, or `deposit_pending` if it does (`ArtistService.deposit_required`) — one hop, chosen by the accept action itself, not a chained double-transition.

**Quote rejection** (`POST /bookings/{id}/quotes/{quote_id}/reject`) marks the quote `declined` and moves the booking to the terminal `rejected` status.

### 5a. Validating availability again at confirmation

`validate_availability_for_confirmation()` re-checks the booking's `requested_date`/`requested_time` against the artist's *current* `ArtistBlockedDate` rows (whole-day or time-scoped) and active `ArtistAvailability` weekly rules (`stored_weekday()`, reused from `app/services/scheduling.py`) — a time that was free when the customer first asked may no longer be, and this is caught here rather than trusted from request time. A booking with no `requested_time` (a whole-day event) skips the weekly-rule check and is only checked against blocked dates.

## 6. Preventing overlapping confirmed bookings

"Occupying" a calendar slot is a status property, not a blanket "any booking" rule — `BOOKING_OCCUPYING_STATUSES` (app/db/enums.py) is `{confirmed, deposit_pending, deposit_paid, in_progress, completed, disputed, refund_requested, refunded}`. A `draft`/`requested`/`*_reviewing`/`quotation_sent` booking is still just a request and must **not** block a different customer from requesting (or even being confirmed into) the same slot; only once a booking has actually been accepted does it reserve the artist's calendar. This is also what `app/services/scheduling.py`'s slot-preview calculator (Phase 12) now filters on, replacing that phase's cruder "not cancelled/declined/expired" placeholder.

`check_no_overlapping_confirmed_booking()` compares the accepting booking's time range (service duration + effective buffer + effective travel buffer, reusing Phase 12's `effective_buffer_minutes`/`effective_travel_buffer_minutes`) against every other occupying booking on the same `artist_profile_id` + `requested_date`, in local wall-clock minutes-since-midnight (no timezone conversion needed since both sides are the same artist's own clock). A booking with no `requested_time` occupies the whole day.

**Locking**: there is no single row that naturally represents "this artist's calendar," so the confirm/reschedule path takes a `SELECT ... FOR UPDATE` lock on the artist's own `ArtistProfile` row for the duration of the transaction (`_lock_artist_calendar()`). This serializes any two concurrent confirmation attempts for the same artist: the first to acquire the lock does its overlap check against not-yet-committed state (sees nothing), completes, and commits (releasing the lock); the second, having been blocked until then, re-runs its own overlap check and now correctly sees the first's committed booking. Verified directly by `tests/booking/test_confirmation_concurrency.py`, which opens two genuinely separate connections/threads (mirroring `tests/engagement/test_concurrency.py`'s established pattern for this codebase) and asserts exactly one of two simultaneous accept attempts for the same artist/date/time succeeds.

Rescheduling (`POST /bookings/{id}/reschedule`) re-runs the same lock + availability + overlap checks whenever the booking being rescheduled is *already* occupying (confirmed or later) — a merely-`requested` booking can be freely rescheduled onto a slot that's already confirmed for someone else, since it isn't holding that slot to begin with.

## 7. Client implementations

- **Web**: full customer flow (`/bookings`, `/bookings/{id}` — draft edit form, submit, cancel, reschedule, quote accept/reject, inspiration-image upload) and the artist-side inbox/detail/quote-sending/calendar (`/artist/bookings`, `/artist/bookings/calendar`), reached from `/artists/{id}`'s "Request a booking" button (replacing the Phase 11 disabled placeholder) and the account page's new "My bookings"/"Booking inbox" links.
- **Flutter**: customer-facing only — "My Bookings" list (`/bookings`), a booking detail/edit screen (`/bookings/:id`, reachable from the list or from "Request a booking" on the artist public profile screen) covering submit/cancel/reschedule/quote-accept-reject/status history. The artist-side inbox stays the pre-existing placeholder screen at `/artist/bookings` — deferring artist self-service booking management to web-only, the same scope decision Phases 10-12 made for scheduling/portfolio/services management, given the Flutter SDK remains unavailable for automated verification in this environment.

## 8. What Phase 13 deliberately does not do

No payment processing anywhere — `deposit_pending`/`deposit_paid`/`refund_requested`/`refunded` exist as valid, tested state-machine nodes but nothing in this phase writes to `deposit_paid`/`refunded` through an HTTP endpoint; that's a future payments phase's webhook handler to call via `transition_booking()` directly. No admin dispute-resolution UI (the `disputed` state and its resolution edges exist in the graph but have no endpoint yet). No artist-side booking management on Flutter (§7). No message/chat thread tied to a booking (the `conversations` table's `BOOKING` type from an earlier phase is unused by this one). No calendar-sync/ICS export. No automatic quote expiry background job — `valid_until` is checked at accept-time only, not swept by a scheduler.

## 9. Related documents

- [booking-status-rules.md](booking-status-rules.md) — superseded Phase 2 placeholder this document replaces
- [artist-scheduling.md](artist-scheduling.md) — the weekly-availability/blocked-dates/buffer model this phase's availability re-validation and overlap prevention build directly on
- [artist-directory.md](artist-directory.md) — the "Request a booking" CTA foundation this phase finally wires up
- [database-relationships.md](database-relationships.md) — general bookings/quotes schema relationships
