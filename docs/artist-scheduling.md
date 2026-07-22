# MehndiVerse — Artist Availability and Scheduling (Phase 12)

Status: Draft (Phase 12)
Last updated: 2026-07-19

This document covers weekly availability rules, blocked dates/holidays/leave, buffer/travel-buffer time, timezone-aware slot calculation, and the calendar view — introduced in Phase 12 on top of the `ArtistAvailability`/`ArtistBlockedDate` scaffolding created in Phase 2 and left unused until now (the same "table exists, nothing writes to it yet" pattern `Follow` and `AuditLog` followed in earlier phases). **Booking creation is explicitly out of scope for this phase** — the slot calculator is read-only; nothing here writes a `Booking` row.

## 1. Timezone strategy

Two different kinds of "time" appear in this schema, and they're stored differently on purpose:

- **Recurring wall-clock time** (`ArtistAvailability.start_time`/`end_time`, `ArtistBlockedDate.start_time`/`end_time`) — local time with no date attached, interpreted against `ArtistProfile.timezone` (an IANA zone name, e.g. `Asia/Kolkata`, never a fixed UTC offset). "9am every Monday" is stored as literally `09:00:00` + `timezone = "Asia/Kolkata"`, not as a precomputed UTC instant.
- **Concrete instants** (an actual computed slot, returned by `GET /artists/{id}/availability/slots`) — these ARE specific points in time, so they're resolved to UTC and returned as UTC-aware datetimes.

`compute_available_slots()` (`app/services/scheduling.py`) is what bridges the two: for each calendar date in the query range, it combines that date with a rule's local wall-clock time via Python's `zoneinfo` (`datetime.combine(day, rule.start_time, tzinfo=ZoneInfo(profile.timezone))`), then converts to UTC. Storing local time + zone name rather than a precomputed UTC offset is what makes daylight saving transitions transparent — see §2.

**Display**: the API only ever returns UTC. Both clients convert to the *viewer's* device/browser timezone for display (web: `Date.prototype.toLocaleString()`; Flutter: `DateTime.toLocal()`) — the artist's own timezone name is included in every slots response (`artist_timezone`) so a client could additionally label "artist's local time" if desired, but this phase's UI only shows the viewer's local time.

`tzdata` (the pure-Python IANA database) is now an explicit direct dependency (`pyproject.toml`), not left to be pulled in transitively — Windows and some minimal Linux containers don't ship an OS-level IANA database that `zoneinfo` can fall back to, so relying on a transitive install would be fragile.

## 2. Daylight saving handling

Because a rule's local time is combined with a *specific* calendar date and resolved via `zoneinfo` at compute time (not once, in advance), the UTC instant a recurring "9am" rule resolves to automatically shifts across a DST boundary — no special-casing needed in the algorithm itself. `tests/scheduling/test_slot_calculation.py::test_dst_spring_forward_shifts_the_utc_offset` verifies this directly: a single recurring Sunday-9am rule resolves to `14:00 UTC` on 2026-03-01 (EST, UTC-5) and `13:00 UTC` on 2026-03-08 (EDT, UTC-4, the day America/New_York springs forward) — same rule row, different UTC instant, because the *local* meaning of "9am" never changed. A fall-back test guards against the calculator crashing or double-counting near a fold date.

## 3. Weekly availability rules ("custom working hours")

`ArtistAvailability` (day_of_week 0=Sunday..6=Saturday, start_time, end_time, is_active) is the recurring shape. `POST/PATCH/DELETE /artist/availability/rules` — self-service, open to any `artist`/`verified_artist` (not gated on verification status, matching the `artist_services.py`/Phase 11 precedent).

## 4. Blocked dates, holidays, personal leave, and manual schedule blocks

All four share one table (`ArtistBlockedDate`), distinguished by `block_type` (`holiday`/`personal_leave`/`vacation`/`other`) and an optional `start_time`/`end_time` pair:

- **Both null** → the whole date range (`start_date`..`end_date`) is blocked — a holiday or multi-day vacation.
- **Both set** → only that time-of-day window on a single day (`start_date == end_date` is enforced by both a Pydantic validator and a DB check constraint) is blocked — a "manual schedule block" like a dentist appointment.

## 5. Preventing invalid ranges

Enforced at both the schema layer (Pydantic `model_validator`s, for immediate 422s on create) and the DB layer (CHECK constraints, as the final backstop against any code path that bypasses the schema):

- `end_time > start_time` for availability rules.
- `end_date >= start_date` for blocked dates.
- A time-scoped block requires both `start_time` and `end_time` together (never just one), `end_time > start_time`, and `start_date == end_date`.
- `default_buffer_minutes`/`default_travel_buffer_minutes`/`buffer_minutes`/`travel_buffer_minutes` are all non-negative.

## 6. Preventing overlapping manual blocks

Application-layer check-then-insert (`find_overlapping_rule`/`find_overlapping_block` in `app/services/scheduling.py`), not a DB exclusion constraint — this is a low-concurrency, single-artist-editing-their-own-calendar operation, so a query-then-insert race window is an acceptable tradeoff for avoiding a `btree_gist`-dependent exclusion constraint (mirrors this codebase's general preference for application-layer validation over exotic DB features, e.g. `uq_collections_one_default_per_user`'s partial-unique-index approach elsewhere).

- **Availability rules**: reject if an existing rule on the *same day of week* has an overlapping time range.
- **Blocked dates**: reject if an existing block's date range overlaps — with one nuance: two single-day, time-scoped blocks on the *exact same date* only conflict if their *time ranges* also overlap (a 9-10am dentist block and a 2-4pm haircut block on the same day are both fine); any block touching a whole-day/multi-day range is always a conflict with anything else on that date, since it has no "gap" a second block could fit into. See `_blocks_conflict()`.

Both return **409 Conflict**, not 422 — the request is well-formed, it just collides with existing state.

## 7. Buffer time and travel buffer

`ArtistProfile.default_buffer_minutes`/`default_travel_buffer_minutes` are artist-wide defaults; `ArtistService.buffer_minutes`/`travel_buffer_minutes` override them per service when set (`effective_buffer_minutes()`/`effective_travel_buffer_minutes()`). Foundation-level simplification: both are added together into one post-appointment gap (`step = duration + buffer + travel_buffer`) — splitting travel buffer by the booking's actual location type (in-studio vs. on-location) isn't possible yet since booking creation (and therefore a chosen location) doesn't exist; this is called out explicitly as a known simplification for a future phase to refine once bookings exist.

## 8. Available-slot calculation

`compute_available_slots()` — for each calendar date in `[start_date, end_date]` (capped at 60 days):

1. Resolve that date's weekday against the artist's active weekly rules → local-time windows.
2. Convert each window to an aware datetime via the artist's `zoneinfo` zone.
3. Subtract blocked-date windows touching that date (whole-day or time-scoped).
4. Subtract existing bookings' occupied ranges (any `Booking` row with a `requested_time` set, in a non-terminal status — `cancelled`/`declined`/`expired` don't occupy a slot) — this makes the calculator correct and forward-compatible for whenever a later phase adds booking creation, even though nothing in *this* phase ever inserts a `Booking`.
5. Slice the remaining free windows into `duration_minutes`-long slots spaced `duration + buffer + travel_buffer` apart.
6. Convert to UTC and drop anything at or before "now".

Service must belong to the queried artist and have a `duration_minutes` set (a `custom_quote` service with no fixed duration can't have slots computed for it — 422).

## 9. Calendar view

`GET /artist/availability/calendar` (self-service) is a simpler, read-only companion to the slot calculator — for each day in range it just reports the raw weekly-rule windows and any touching blocks (`is_available: bool` = has at least one window and isn't whole-day-blocked), with no service/duration/buffer math. It's what the artist sees when reviewing their own setup; `compute_available_slots` is what a customer sees when checking bookability for a specific service.

## 10. Manual schedule block

The same `ArtistBlockedDate` create endpoint, with `start_time`/`end_time` set — see §4. No separate endpoint or table; the web UI exposes it as a checkbox ("Only block specific hours on this day") on the same block-creation form used for holidays/leave/vacation.

## 11. Client implementations

- **Web**: `/artist/availability` (self-service — tabbed: Weekly hours, Time off, Calendar, Settings) and a `CheckAvailabilityWidget` on the public artist profile page (`/artists/{id}`) — a read-only, service-scoped slot browser showing the *viewer's* local time, explicitly labeled "Booking isn't available yet." All backend calls go through `src/app/api/artist/availability/*` and `src/app/api/artists/[id]/availability/slots` proxy routes.
- **Flutter**: only the customer-facing "check availability" section on `ArtistPublicProfileScreen` (service picker + a week of slots, same read-only/no-booking framing as web). The artist-side self-service scheduling management screens (settings/rules/blocks/calendar) are **not** built on Flutter in this phase — same scope decision Phase 11 made for portfolio/services management: the web app already covers artist-side management end-to-end, and building a second, unverified (Flutter SDK is still unavailable in this environment) copy of a fairly complex tabbed CRUD UI was judged lower-value than keeping the customer-facing surface complete on both platforms.

## 12. Query, permission, boundary, and timezone tests

- `tests/scheduling/test_slot_calculation.py` — pure unit tests against `compute_available_slots()` directly (no HTTP layer): basic generation, buffer spacing, travel-buffer fallback/override, missing-duration/wrong-artist/invalid-range/over-max-range rejection, whole-day and time-scoped block exclusion, existing-booking exclusion (and that cancelled bookings don't exclude), inactive-rule and no-rule-that-day producing zero slots, exact-fit and one-minute-short boundary cases, the "now" cutoff boundary, non-UTC offset correctness (`Asia/Kolkata`, a half-hour offset), DST spring-forward and fall-back, a local-midnight-crossing case (UTC date rolls back a day), and invalid-timezone rejection.
- `tests/artist/test_scheduling_rules.py`/`test_scheduling_blocks.py` — CRUD, ownership, the full overlap-prevention matrix (including the same-day-non-overlapping-times-is-fine nuance from §6), invalid-range rejection.
- `tests/artist/test_scheduling_settings.py` — timezone/buffer settings get/update, invalid-timezone and negative-buffer rejection.
- `tests/artist/test_scheduling_calendar.py` — calendar view correctness, range-too-large rejection.
- `tests/artist/test_available_slots_api.py` — the public slots endpoint's visibility (404 for a hidden artist or a service belonging to someone else or an inactive service), and end-to-end computed-slot correctness through the HTTP layer.

## 13. What Phase 12 deliberately does not do

No booking creation (per the phase's explicit instruction) — the slot calculator is purely read-only. No splitting travel buffer by booking location type (§7). No recurring-exception UI beyond blocked dates (e.g., no "every other Tuesday" rule variants — a rule is a flat weekly recurrence). No Flutter self-service scheduling management (§11). No calendar sync (Google Calendar/iCal import-export) — out of scope for this phase.

## 14. Related documents

- [artist-directory.md](artist-directory.md) — the Phase 11 public profile/services this phase's scheduling attaches to (`ArtistService.duration_minutes` already existed; this phase adds the buffer/travel-buffer fields and the slot math around it)
- [booking-status-rules.md](booking-status-rules.md) — the `Booking`/`BookingStatus` model this phase's slot calculator reads from defensively, without ever writing to it
- [database-schema.md](database-schema.md) — general schema conventions (CHECK-constraint-as-enum, naming) this phase's migration follows
