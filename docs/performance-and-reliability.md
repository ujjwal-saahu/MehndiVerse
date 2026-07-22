# MehndiVerse — Performance, Scalability, and Reliability (Phase 25)

Evidence-based changes only — see each section for what was measured/reasoned before changing anything. No Flutter/Dart toolchain was available in this environment (`flutter`/`dart` not installed), so `apps/mobile` findings are documented as specific, ready-to-apply recommendations rather than applied and unverifiable source edits.

## Slow queries / N+1 review

Reviewed `app/services/design_summaries.py`, `app/services/booking.py`, `app/services/scheduling*.py`, `app/services/analytics/*`, and admin listing routes for per-item queries inside loops. Finding: **already disciplined** — batch helpers (`batch_primary_images`, `batch_artist_summaries`, `summaries_for_designs`) fetch in bulk; loop bodies found (`booking.py`'s notify-both-parties loop, `account_deletion.py`'s device-cleanup loop) iterate either a single query's own results or a set bounded to ≤2 items. No N+1 found; no change made.

## Indexes

Three hot list endpoints filter on one column and sort by `created_at DESC` with a `LIMIT`, but only had a single-column index on the filter column:

| Endpoint | Query | Added index |
|---|---|---|
| `GET /bookings/mine` | `bookings.py:99-105` | `ix_bookings_customer_id_created_at` |
| Message list | `messaging.py:129-142` | `ix_messages_conversation_id_created_at` |
| `GET /notifications` | `notifications.py:62-77` | `ix_notifications_user_id_created_at` |

Migration `8f509ffde693`, upgrade/downgrade round-trip verified. Existing single-column indexes kept (other queries, e.g. unread-count, still use them). `EXPLAIN` on the local dev DB (near-empty) still shows `Seq Scan` for these tables — not meaningful evidence at that row count; the justification here is query-shape match (filter + sort + limit against a composite index), the same reasoning as every other index already in this schema (see `booking.py`'s pre-existing `ix_bookings_artist_profile_id_status_requested_date`).

## Pagination limits

Audited every `limit: int = N` query param across `app/api/routes/*.py`. Found one unclamped: `GET /analytics/recommended` passed `limit` straight to the query with no upper bound — fixed (`max(1, min(limit, 50))`, matching the sibling `/analytics/recently-viewed` endpoint's existing clamp). All other `limit`/admin `page_size` params were already clamped (`admin_listing.py::MAX_PAGE_SIZE = 100`, or an inline `max(1, min(limit, N))`).

## Image metadata responses

Reviewed `DesignImageOut`/`DesignSummaryOut` (`app/schemas/design.py`). Already lean: URLs + dimensions only, no EXIF/checksum/base64 data in any response (`ProcessedImage.checksum_sha256` is used internally, never serialized). List/search endpoints already return `DesignSummaryOut` (grid-card shape, single thumbnail), not the heavier `DesignOut`. No change made.

## Database connection pooling

`app/db/session.py::get_engine()` previously only set `pool_pre_ping=True` — pool size, overflow, timeout, and recycle were all unset SQLAlchemy defaults (`pool_size=5`, no overflow limit awareness, no recycle). Added explicit, configurable settings (`db_pool_size=10`, `db_max_overflow=20`, `db_pool_timeout_seconds=30`, `db_pool_recycle_seconds=1800`) — the recycle value keeps connections under most managed-Postgres providers' idle-connection cutoff.

## Timeouts

- Redis client (`app/core/redis_client.py`): had `socket_connect_timeout=2` but no `socket_timeout` — an unresponsive Redis could hang a request on a plain GET/INCR, not just on connect. Added `socket_timeout=2`.
- Supabase Auth/Storage/Razorpay httpx clients already had `timeout=` set (10-15s) — confirmed adequate, no change.

## Retry strategy

New `app/core/resilience.py` — no new dependency (hand-written, ~150 lines, justified over adding `tenacity` for three call sites per this project's "no dependency added for later" rule). Two policies:

- `retry_connect_only` — retries only `ConnectError`/`ConnectTimeout`/`PoolTimeout` (the request was never transmitted). Applied to every mutating call (Supabase Auth's five endpoints, Razorpay `create_order`/`create_refund`) — **never** retries a `ReadTimeout` or 5xx for these, since the provider may have already processed the request and retrying could duplicate it (e.g. a second Razorpay order).
- `retry_idempotent` — also retries `ReadTimeout` and 5xx. Applied to Supabase Storage (every operation there is an upsert-write, delete, or URL-sign — all safe to repeat) and Razorpay's `get_order_status` (a GET).

Tests: `tests/core/test_resilience.py` (11 cases covering both policies' retry/no-retry boundaries).

## Circuit-breaker considerations

`CircuitBreaker` in the same module — per-process, in-memory, one instance per external service (`supabase_auth_breaker`, `supabase_storage_breaker`, `razorpay_breaker`). Opens after 5 consecutive failures (exception or 5xx), refuses calls for 30s, then allows one half-open trial. **Explicitly not** a distributed breaker (no shared state across worker processes) — that needs a Redis-backed counter, not justified yet at this app's traffic volume; documented here as the concrete "considerations" this phase asked for, with the upgrade path noted for when it's needed.

## Health / readiness checks

`GET /health` already checked DB + Redis (a readiness check in substance). Added `GET /health/live` — no dependency checks, answers "is the process up" only. Split matters for container orchestration: a liveness-probe failure should restart the process; a readiness-probe failure (a downstream dependency blip) should just pull the instance out of rotation, not restart it. Tests: `tests/test_health.py`.

**Load-test finding, fixed**: `/health` was building a brand-new `Redis.from_url(...)` client on every single call instead of reusing the pooled client from `app/core/redis_client.py` — beyond the modest latency cost (see [Load test results](#load-test-results)), an unpooled connection per readiness check is a real file-descriptor-exhaustion risk under sustained polling from multiple orchestrator replicas. Fixed to reuse `get_redis_client()`.

## Background-job retries / dead-letter handling / idempotent tasks

- **AI jobs** (`app/services/ai/jobs.py`, Phase 20): already has in-process retry with exponential backoff up to `max_attempts`, then a terminal `failed` status — staff can filter `GET /admin/ai/jobs?status=failed`, which is this system's dead-letter queue (inspectable, not silently dropped). No change.
- **CLI jobs** (`reconcile_payments`, `process_subscriptions`, `process_account_deletions`): idempotent by query design — each only selects rows still in the state it acts on (`pending`, due-for-transition, `pending_deletion` past grace period), so re-running the whole script (the "retry" for these, since no in-process retry loop exists) is always safe. **New test** added: `tests/payments/test_reconciliation.py::test_reconcile_is_idempotent_when_run_twice` — explicitly verifies a second pass after settlement is a no-op, not previously covered.

## Database backup and restore test

`scripts/backup_restore_test.sh` — `pg_dump` (custom format) the running local/CI Postgres, restore into a throwaway database, compare per-table row counts, clean up. **Actually run** against the local dev database:

```text
Dump size: 207819 bytes
PASS: restored database matches source across 58 tables.
```

This exercises the real recovery path, not just "Supabase says backups are enabled" (that access-control side is covered in docs/security-review.md#backup-access-controls — this is the "do they actually work" side).

## Payment reconciliation test

Existing coverage (`tests/payments/test_reconciliation.py`) already exercised settle/fail/skip-within-grace-period. Added the missing idempotency case (see above).

## Load test results

`scripts/load_test.py` (self-contained, httpx + asyncio — no new dependency) against a local `uvicorn` instance, 20 concurrent, 200 requests/endpoint:

**Before the `/health` Redis-pooling fix:**
```text
GET /health:                    p50=75.0ms  p95=397.7ms  p99=417.5ms  errors=0  throughput=184.8 req/s
GET /api/v1/designs/published:  p50=40.7ms  p95=130.2ms  p99=172.1ms  errors=0  throughput=344.2 req/s
GET /api/v1/categories:         p50=39.7ms  p95=126.4ms  p99=159.1ms  errors=0  throughput=364.4 req/s
```

**After:**
```text
GET /health:                    p50=74.3ms  p95=367.2ms  p99=375.7ms  errors=0  throughput=191.0 req/s
GET /api/v1/designs/published:  p50=43.7ms  p95=139.1ms  p99=192.9ms  errors=0  throughput=323.3 req/s
GET /api/v1/categories:         p50=36.2ms  p95=129.2ms  p99=176.5ms  errors=0  throughput=365.2 req/s
```

The latency improvement was modest (~8% on p95) — smaller than the connection-setup overhead alone would suggest, since local Redis connect latency is already low. The `/health` fix is justified primarily by the file-descriptor-exhaustion risk under sustained load (see above), not by this benchmark's latency delta; recorded honestly rather than overclaiming. `/health`'s higher latency than the data endpoints is inherent — it does two sequential dependency checks (DB + Redis) vs. one DB query — not a bug. Zero errors across all runs at this concurrency; this is a local single-instance dev-DB benchmark, not a production-scale capacity test.

## Web: bundle size / lazy loading

`apps/web`'s dependency footprint is already minimal (no chart/rich-text/map libraries; 8 runtime dependencies total). No `next/dynamic`/`React.lazy` usage existed anywhere. `PreviewStudio` (534 lines, canvas-based photo compositing, `docs/hand-foot-preview.md`: "compositing is client-side only" — no SSR value) was statically imported into both `/previews/new` and `/previews/[id]`. Converted to `next/dynamic(..., { ssr: false })` via a small Client Component wrapper (`preview-studio-lazy.tsx` — `ssr:false` requires a Client Component boundary, and both call sites are Server Components). Verified: production build succeeds, all 351 vitest tests still pass, lint/typecheck clean.

## Web: image loading

`next/image` already used in 15 of 16 image-rendering components (the one raw `<img>`, in the canvas overlay editor, is justified — it's drawn onto a `<canvas>`, not displayed directly, so Next's optimization pipeline doesn't apply). No change needed.

## Mobile: findings (not applied — no Flutter/Dart toolchain available)

`flutter`/`dart` are not installed in this environment, so no `apps/mobile` source was edited — there was no way to run `flutter analyze`/`flutter test` to catch a mistake, and shipping unverifiable native-app source changes is worse than not making them. Findings, for a follow-up with a working Flutter toolchain:

- **Image loading**: `Image.network(...)` is used in 7 files (`gallery_widgets.dart`, `collections_screen.dart`, `collection_detail_screen.dart`, `artist_onboarding_screen.dart`, `conversation_detail_screen.dart`, `previews_list_screen.dart`, `preview_studio_screen.dart`). Flutter's built-in `Image.network` has no persistent disk cache — every screen revisit re-downloads. Recommend adding `cached_network_image` (widely used, well-maintained) and swapping these call sites; the simple ones (`Image.network(url, fit: BoxFit.cover)`, e.g. `collections_screen.dart:147`) are a direct `CachedNetworkImage(imageUrl: url, fit: BoxFit.cover)` swap. `gallery_widgets.dart:46-54` additionally uses `loadingBuilder`/`errorBuilder` — these map to `CachedNetworkImage`'s `placeholder`/`errorWidget` params but have a different callback signature (verify against the installed package version before converting).
- **Lazy loading**: `grep` found 25 non-`.builder` `ListView(...)` call sites. Most are small, fixed-structure screens (settings, error/empty states) where `.builder` wouldn't help; **not** audited item-by-item without a compiler to verify each conversion. Worth a follow-up pass specifically on data-driven, potentially-long lists (search results, notification lists) if not already using `.builder`.
- **Rebuilds**: not audited (would need `flutter analyze --no-fatal-infos` plus visual profiling via DevTools, neither available here).

## Reliability doc cross-references

- [docs/security-review.md#backup-access-controls](security-review.md#backup-access-controls) — the access-control side of backups; this doc covers the "do they work" side.
- [docs/ai-foundation.md](ai-foundation.md) — the AI job queue's retry/backoff design this phase's dead-letter review confirmed adequate.
- [docs/payments.md#10-reconciliation-command](payments.md) — the reconciliation command this phase added an idempotency test for.
