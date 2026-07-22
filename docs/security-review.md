# MehndiVerse — Security Review (Phase 24)

Phase 24 security-hardening review across `apps/api`, `apps/web`, `apps/admin`. Each section states what was reviewed, what was found, and what changed. Findings with no code change are explicitly marked "no change" with the reasoning, not silently omitted.

## Authentication

Supabase Auth (GoTrue) is the sole identity provider; `app/core/security.py` verifies JWTs locally via the shared HS256 secret (docs/authentication.md#2). **Finding**: no account-level login-abuse protection existed — only IP-based rate limiting (`auth_rate_limit`, 5/minute), which doesn't stop credential stuffing spread across IPs. **Fixed**: account-keyed lockout, see [Login-abuse protection](#login-abuse-protection).

## Authorization

`app/api/deps.py::require_roles()` enforces RBAC server-side on every route; effective roles are derived server-side (`app/core/authz.py`), never trusted from a client. Reviewed a sample of admin/staff routes (`admin_users.py`, `admin_payments.py`, `admin_moderation.py`) — all gate through `require_roles`. **No change** — this layer was already sound.

## Row-Level Security

**Finding**: `3f28fa5a570a_auth_row_level_security_foundations` (Phase 14) covered only a first slice of tables (users, profiles, artist_profiles, designs, bookings, messages, notifications, payments). Every table added by a later phase — `conversations`, `conversation_members`, `reviews`, `collections`, `subscriptions`, `reports`, `preview_projects`, `ai_generations`, `ai_design_requests`, `audit_logs` — had RLS disabled entirely, unmet against docs/security-baseline.md#2's own "defense-in-depth for direct Supabase-mediated access" requirement. **Fixed**: new migration `58e26672bf4e_extend_row_level_security_coverage` adds owner/participant/staff policies to all of them, `audit_logs` staff-read-only with no write policy for any role. Verified in `tests/core/test_row_level_security.py` (checks `pg_tables.rowsecurity` and `pg_policies` directly, since the app's own DB role bypasses RLS and nothing else in the suite would catch a regression here).

Remaining tables without RLS (`likes`, `follows`, `collection_items`, `comments`, `notification_campaigns`, `system_settings`, plan/catalog tables): lower-sensitivity or effectively public-read data; deferred as a smaller follow-up rather than expanding this migration further.

## Storage policies

`infrastructure/supabase/storage_policies.sql` — reviewed all six buckets. `avatars`/`portfolio` are intentionally public-read (marketing/profile content) with owner-only write. `verification-documents`, `chat-attachments`, `preview-projects`, `ai-generated-designs` are private, path-prefixed by owner/conversation id, staff-readable where relevant (verification documents). **No change** — already correctly scoped, matches the RLS policies for the same data.

## Admin permissions

`require_roles("admin", "super_admin")` / `require_roles(*_VIEW_ROLES)` patterns reviewed across `admin_*.py` routes. Role changes (`admin_users.py::update_user_role`) additionally enforce who-can-change-whose-role beyond the base RBAC gate, and are audit-logged. **No change**.

## File uploads

`app/core/images.py` (avatars, design photos) and `app/core/documents.py` (verification documents) already: reject on file-size, decode-validate via Pillow regardless of client-claimed `Content-Type`, strip EXIF/ICC/XMP by re-encoding, cap decoded pixel count (decompression-bomb guard), and magic-byte-check PDFs. **No change** — this was already a strong implementation; see [Upload validation](#upload-validation) for the one addition (a regression test asserting these guards).

## Payment webhooks

`app/services/payments/razorpay_provider.py::verify_webhook_signature` uses `hmac.compare_digest` (constant-time), and `handle_webhook` requires a valid signature before parsing. `create_payment`'s `idempotency_key` prevents duplicate-charge processing. **No change** — already correct.

## Messaging

Message bodies are length-capped (`SendMessageRequest.body`, max 4000 chars) and never rendered via `dangerouslySetInnerHTML` anywhere in `apps/web`/`apps/admin` (grepped — zero matches), so React's default escaping is the XSS backstop. Attachments go through `chat-attachments`' private, conversation-member-scoped storage policy. **No change**.

## Rate limiting

Extensive per-feature `slowapi` limits already existed (`auth_rate_limit`, `search_rate_limit`, `payment_rate_limit`, `ai_rate_limit`, etc. — `app/core/config.py`), all IP-keyed. **Improved**: added an account-keyed lockout on top for login specifically (IP-based alone doesn't stop a distributed attack against one account). See [API rate limits](#api-rate-limits).

## Input validation

Every request body is a Pydantic model with explicit field constraints (`min_length`/`max_length`/regex) — reviewed a sample across auth, messaging, profile, reports schemas. `app/core/search_sanitize.py` strips control characters and clamps search-query length before it reaches Postgres's full-text parser. No raw SQL string interpolation found anywhere in `app/services`/`app/api` (grepped for `f"SELECT`/`.format(` near `execute(` — none). **No change**.

## Error responses

`app/core/exceptions.py::register_exception_handlers` already returns a fixed generic message for validation failures and unhandled exceptions — no stack traces or internal details ever reach the client; those are only in structured logs. **No change** (this phase's addition here is [Sensitive-log redaction](#sensitive-log-redaction), not the response shape).

## Secret handling

`.env.example` and `apps/api/.env.example`(via `Settings` defaults) list only placeholder, non-functional values; `.gitignore` excludes `.env`/`.env.*.local`. Grepped the working tree for common secret patterns (`sk_live`, `AKIA`, private-key headers) — none found. **Improved**: added gitleaks to both pre-commit and CI (see [Secret scanning](#secret-scanning)), and extended `.gitignore` for local DB dump files (see [Backup access controls](#backup-access-controls)).

## Logging

`app/core/logging.py` uses structured JSON logging (structlog) throughout. **Finding**: no redaction step existed — a call site that ever logged a token/password/signature by mistake would have written it to stdout in cleartext. **Fixed**: see [Sensitive-log redaction](#sensitive-log-redaction).

## CORS

`app/main.py`'s `CORSMiddleware` already restricts `allow_origins` to `settings.cors_origins` (explicit list, never `*`) with `allow_credentials=True`. **No change**.

## CSRF

Session cookies (`apps/web`, `apps/admin`) are already `httpOnly` + `SameSite=Lax` (`lib/session-cookies.ts`), which blocks the cookie from riding along on a cross-site POST in modern browsers. **Improved**: added explicit `Origin`/`Referer` validation in both apps' `middleware.ts` for every mutating (`POST`/`PUT`/`PATCH`/`DELETE`) request to `/api/*`, as defense-in-depth against `SameSite` misconfiguration/older-browser gaps. See [CSRF](#csrf-1) below for detail — apps/api itself uses Bearer-token auth (never cookies), so it has no CSRF surface of its own.

## Dependency vulnerabilities

`npm audit --audit-level=high` (root workspace): 0 high/critical (2 moderate, in `next`'s transitive `postcss`, no fix available without a breaking Next.js downgrade — tracked, not blocking). `pip-audit --skip-editable` (apps/api): 0 known vulnerabilities. **Added**: both now run in CI on every push/PR (see [Dependency scanning](#dependency-scanning)) plus Dependabot for ongoing updates.

## Account deletion

**Finding**: `POST /auth/account/deletion-request` only ever flagged the account (`status=pending_deletion`, `deletion_requested_at` set) — nothing ever processed that flag. `User.deleted_at` (via `SoftDeleteMixin`) already existed and `get_current_user` already rejected any account with it set, but nothing ever wrote to it — a dangling, never-finalized deletion request. **Fixed**: see [Account deletion](#account-deletion-1) below.

## Audit logs

`AuditLog` (`app/db/models/system.py`) + `record_audit_log()` existed since Phase 2/19 for admin actions. **Extended** to cover the new security-relevant events this phase adds (login lockout, session revoke-all, account deletion request/finalization) — reused rather than building a parallel "security events" table, since `AuditLog` already has everything needed (actor, ip, user-agent, before/after state) and is already staff-readable via `GET /admin/audit-logs` with no route changes required. See [Suspicious-activity events](#suspicious-activity-events).

---

# Implemented/improved

## API rate limits

Unchanged from the existing extensive per-feature `slowapi` config — reviewed and confirmed adequate; no gaps found beyond the login-lockout addition below.

## Login-abuse protection

`app/services/login_security.py` — Redis-backed, keyed by SHA-256 of the normalized email (never the raw address, so a Redis operator glance never reveals who's being targeted). After `login_lockout_threshold` (default 5) failed attempts within `login_lockout_window_seconds` (default 900s), further attempts for that email are rejected with the same generic "Invalid email or password." message — before Supabase is even called — regardless of source IP. Reaching the threshold writes an `AuditLog` row (`action="login.lockout_triggered"`). A successful login clears the counter. Tests: `tests/auth/test_login_lockout.py`.

## Upload validation

Confirmed already strong (see [File uploads](#file-uploads) above) — no code change; existing coverage in `tests/profile`/`tests/artist` already exercises the size/format/pixel-cap paths.

## Security headers

`app/core/security_headers.py` (apps/api) — middleware setting `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, a restrictive `Permissions-Policy`, and `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'` (a pure JSON API never needs to load or be framed by anything) on every response, plus `Strict-Transport-Security` when `environment=production`. `apps/web`/`apps/admin`'s `next.config.ts` `headers()` add the page-serving equivalent (`'unsafe-inline'` on `style-src` only, for Next.js's own injected styles — no nonce wiring exists yet, tracked as a follow-up). Tests: `tests/core/test_security_headers.py`.

## Sanitization

Confirmed already adequate (`app/core/search_sanitize.py`, Pydantic field constraints, React's default escaping) — no code change.

## Sensitive-log redaction

`app/core/logging.py::_redact_sensitive_fields` — a structlog processor replacing the value of any event-dict key matching `password`, `access_token`, `refresh_token`, `token`, `authorization`, `secret`, `signature`, `jwt`, `client_secret`, `api_key` (case-insensitive) with `[REDACTED]` before the JSON renderer runs. Matches by key name rather than value-content sniffing, since every call site already uses consistent, predictable kwarg names. Tests: `tests/core/test_log_redaction.py`.

## Privileged-action reauthentication

`app/api/routes/auth.py::_verify_reauth` — re-verifies the caller's current password against Supabase (`sign_in_with_password`) immediately before an irreversible/high-impact action. A valid bearer token alone only proves *a* session is live, not that whoever is driving it right now is the account holder (a hijacked/left-open session, or a stolen-but-not-yet-expired token). Applied to `POST /auth/account/deletion-request` and the new `POST /auth/sessions/revoke-all`. Tests: `tests/auth/test_account_deletion.py::test_account_deletion_requires_correct_password`, `tests/auth/test_session_revocation.py::test_revoke_all_requires_correct_password`.

## Session revocation

`POST /auth/sessions/revoke-all` (reauth-gated) calls `supabase_auth.sign_out(token, scope="global")` — revokes every session for the account, including the one making the request. `sign_out()` gained an explicit `scope` parameter (default `"local"`, matching the pre-existing `/auth/logout` behavior) rather than relying on GoTrue's own undocumented-in-code default. Audit-logged (`action="session.revoke_all"`). Tests: `tests/auth/test_session_revocation.py`.

## Suspicious-activity events

Reused `AuditLog`/`record_audit_log()` (see [Audit logs](#audit-logs) above) rather than building a parallel table — deliberately *not* the consent-gated `AnalyticsEvent` mechanism from Phase 22, since a user disabling analytics must never also disable fraud-relevant security logging of their own account. New event types: `login.lockout_triggered`, `session.revoke_all`, `account.deletion_requested`, `account.deletion_finalized`. All staff-readable via the existing `GET /admin/audit-logs` (filterable by `action`) with zero route changes.

## Dependency scanning

CI (`.github/workflows/ci.yml`, new `dependency-scan` job): `pip-audit --skip-editable` for `apps/api`, `npm audit --audit-level=high` for the JS workspaces. `.github/dependabot.yml`: weekly updates for `pip` (apps/api), `npm` (root workspace), `pub` (apps/mobile), `github-actions`, and `docker`.

## Secret scanning

`gitleaks` added to `.pre-commit-config.yaml` (local, pre-commit) and as a new `secret-scan` CI job (`gitleaks/gitleaks-action@v2`, full-history scan on every push/PR).

## Backup access controls

MehndiVerse has no local backup/dump tooling — database backups are entirely Supabase-managed (encrypted at rest, access gated by the Supabase project's own IAM, consistent with docs/security-baseline.md#4). The concrete local-repo risk is an operator's ad hoc `pg_dump` output getting committed by accident; `.gitignore` now excludes `*.sql.gz`, `*.dump`, `*.backup`, `*.bak` repo-wide. No application code touches backups, so there was nothing else in this codebase to restrict.

## Account deletion

`app/services/account_deletion.py::process_pending_deletions` — finds accounts whose `deletion_requested_at` is older than `account_deletion_grace_period_days` (default 14, a window to cancel an accidental/coerced request) and still `status=pending_deletion`, then: anonymizes `email` (deterministic `deleted-{id}@deleted.mehndiverse.invalid`, collision-free), clears `phone`, sets `deleted_at`; anonymizes the linked `Profile` (display name, avatar, bio, city, country); deletes `UserDevice` rows (push tokens); writes an `account.deletion_finalized` audit entry. Run via `python -m app.cli.process_account_deletions [--dry-run]`, mirroring the existing `process_subscriptions`/`process_ai_jobs` cron-style CLI pattern (no scheduler exists in this environment yet — same as those). Dependent records (bookings, reviews, messages) are deliberately left in place: once the account's own PII is scrubbed, those rows no longer identify the person, and cascading them away would corrupt other parties' own history.

**Deliberately not done**: calling Supabase's Admin API to delete the underlying `auth.users` row. That needs a service-role-authenticated GoTrue Admin API integration this codebase doesn't have yet — recommended as a follow-up phase. Until then, a "deleted" account's Supabase Auth credentials still technically exist, but can never be used to reach any of our own data or API surface again (`get_current_user` rejects any `deleted_at`-set account, and the login-lockout/rate-limit paths apply equally to it).

## CSRF (implementation detail)

`apps/web/src/middleware.ts` / `apps/admin/src/middleware.ts`: for any `POST`/`PUT`/`PATCH`/`DELETE` to `/api/*`, compares the request's `Origin` header (falling back to `Referer` if `Origin` is absent) against the request's own origin; mismatches get a `403`. `apps/web`'s middleware `matcher` was extended to include `/api/:path*` (previously only page prefixes). Tests: `middleware.test.ts` in both apps.

---

## Related documents

- [docs/threat-model.md](threat-model.md)
- [docs/incident-response.md](incident-response.md)
- [docs/security-baseline.md](security-baseline.md) — the Phase 0 policy this review checks the codebase against
- [docs/authentication.md](authentication.md)
