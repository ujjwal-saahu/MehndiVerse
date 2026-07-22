# MehndiVerse — Operational Runbook (Phase 28)

Companion to [docs/observability.md](observability.md) (what's measured) and [docs/incident-response.md](incident-response.md) (how to handle a security incident specifically). This is "what to actually do" for the operational alerts this phase wires up.

## How to check system health right now

1. `GET /health/live` — is the process up at all.
2. `GET /health` — is it ready to serve traffic (DB + Redis reachable).
3. `GET /metrics?token=<METRICS_TOKEN>` — the full current counter/histogram state.
4. Structured logs (whatever the deployment's log aggregator is) filtered to `level=error` for the last hour — the fastest way to see what's actually failing right now, since every alert this phase adds is also always a log line regardless of whether a webhook is configured.

## Alert: `database_unavailable`

**What it means**: `GET /health`'s `SELECT 1` against the primary database failed.

1. Check the database's own status page/console (Supabase project status, or the managed Postgres provider's).
2. Check connection count — `db_pool_size`/`db_max_overflow` (docs/performance-and-reliability.md#database-connection-pooling) exhaustion looks identical to real unavailability from the app's point of view. If the DB itself is healthy but connections are maxed, that's a traffic/leak problem, not a DB outage.
3. If the DB is genuinely down: this is provider-side, nothing to restart on our end. Monitor its status page; `GET /health` will clear itself once it recovers (no manual reset needed anywhere in this codebase).
4. If it recovers but background jobs missed their window (docs/deployment.md#background-workers): every one of them is idempotent by design, so simply let the next scheduled run catch up — do not manually re-run unless a specific job's failure alert (below) also fired.

## Alert: `cache_unavailable`

**What it means**: `GET /health`'s Redis `PING` failed.

1. Redis backs: rate limiting (`app/api/deps.py::limiter`), login-lockout counters (`app/services/login_security.py`), and the AI-job/analytics caching layer. None of these are safety-critical if Redis is briefly down — `slowapi` and the lockout check fail open in most client libraries' default behavior, meaning **reduced abuse protection**, not an outage, while Redis recovers.
2. Same provider-status-page check as the database alert.
3. No manual action needed once it recovers; nothing in this codebase caches state in a way that goes stale/wrong from a Redis restart (Redis here is rate-limit counters and a cache, never the system of record).

## Alert: `circuit_breaker_opened` (service: `supabase_auth` / `supabase_storage` / `razorpay`)

**What it means**: 5 consecutive failures calling that provider — see docs/performance-and-reliability.md#circuit-breaker-considerations. The breaker itself will attempt one trial call after 30s (half-open) and close again automatically if that succeeds — **no manual reset exists or is needed**.

1. Check that provider's own status page (Supabase, Razorpay).
2. If `supabase_auth`: users cannot log in/sign up/refresh their session while this is open — this is user-visible and severity-worthy.
3. If `supabase_storage`: uploads (avatars, portfolio, verification documents, previews) fail; existing signed URLs for already-uploaded files are unaffected (Storage's read path is separate from this app's own upload calls).
4. If `razorpay`: new payment orders/refunds fail; **do not** manually retry a payment creation from an admin tool without checking whether Razorpay actually received the original request first (docs/rollback.md's reasoning about non-idempotent operations applies here too).

## Alert: `ai_job_permanently_failed`

**What it means**: one specific AI job exhausted its retries (`max_attempts`) — not a systemic outage by itself (a single job can fail permanently for a job-specific reason, e.g. an unprocessable input image).

1. Check `job_id`/`job_type` in the alert payload; look it up via `GET /admin/ai/jobs?status=failed` (the dead-letter view, docs/performance-and-reliability.md#background-job-retries-dead-letter-handling-idempotent-tasks).
2. If many different jobs are failing in a short window: check `ai_provider` in `dependency_call_failures_total` — this usually means the same thing as a `circuit_breaker_opened` alert, just observed from the job-outcome side instead of the HTTP-call side.
3. A permanently-failed job is never silently retried again automatically — if it should be retried after a fix, that's a deliberate manual action (re-enqueue), not automatic.

## Alert: `background_job_failed` (job: `reconcile_payments` / `process_subscriptions` / `process_account_deletions` / `process_ai_jobs`)

**What it means**: the CLI's `main()` raised past its own try/except — i.e. something broke badly enough that even the job's own error handling didn't contain it (a bug, not an expected business-logic rejection).

1. Read the full traceback in the structured log (`exc_info=True` is always attached) — this is a code-level bug, not a data-level one.
2. **`reconcile_payments` failing repeatedly is the highest-severity case of this alert** — it's the fallback for a lost payment webhook; if it's also broken, a payment can get stuck `pending` indefinitely with no automatic path to resolution. Treat this as page-worthy, not just log-worthy.
3. Every job here is idempotent (docs/performance-and-reliability.md#idempotent-tasks) — once the underlying bug is fixed, simply re-run the CLI manually (`python -m app.cli.<name>`) rather than waiting for the next scheduled tick, especially for `reconcile_payments`.

## Alert: `payment_webhook_unreferenced_event` / high `payment_webhook_events_total{outcome="signature_invalid"}`

See docs/incident-response.md#payment-webhook-anomaly-signature-failures-unexpected-event-volume — this runbook doesn't duplicate that playbook, only points to it.

## Escalation

For anything above that looks like a genuine security incident (not just an operational blip) — unauthorized access, data exposure, a secret that may have leaked — stop following this runbook and switch to [docs/incident-response.md](incident-response.md) instead; that document's severity levels and containment-first process apply, not this one's "wait for auto-recovery" defaults.

## Related documents

- [docs/observability.md](observability.md)
- [docs/incident-response.md](incident-response.md)
- [docs/rollback.md](rollback.md)
- [docs/performance-and-reliability.md](performance-and-reliability.md)
