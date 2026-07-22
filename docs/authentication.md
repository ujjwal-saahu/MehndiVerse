# MehndiVerse — Authentication & Authorization (Phase 3)

Status: Draft (Phase 3)
Last updated: 2026-07-14

## 1. Role naming — reconciling Phase 2 and Phase 3

Phase 3 specifies seven checkable roles: `customer`, `premium_customer`, `artist`, `verified_artist`, `moderator`, `admin`, `super_admin`. Phase 2's migrated schema (see [database-schema.md](database-schema.md#4-enum-strategy)) already defines `users.role` as one of `customer`, `artist`, `moderator`, `administrator`, `super_administrator`, with Premium Customer and Verified Artist modeled as **derived statuses** (an active subscription; `artist_profiles.verification_status = verified`) rather than stored role values — this matches [user-roles-and-permissions.md](user-roles-and-permissions.md), written in Phase 0.

Rather than re-migrate an already-shipped enum for a naming preference, this phase keeps the Phase 2 schema unchanged and introduces an **effective role** — computed at request time in `app/core/authz.py::get_effective_role()`, never stored:

| Effective role (API-facing) | Derived from |
|---|---|
| `customer` | `users.role = 'customer'`, no active subscription |
| `premium_customer` | `users.role = 'customer'` **and** an active `subscriptions` row |
| `artist` | `users.role = 'artist'`, `artist_profiles.verification_status != 'verified'` |
| `verified_artist` | `users.role = 'artist'` **and** `artist_profiles.verification_status = 'verified'` |
| `moderator` | `users.role = 'moderator'` |
| `admin` | `users.role = 'administrator'` |
| `super_admin` | `users.role = 'super_administrator'` |

All RBAC checks (`require_roles()` in `app/api/deps.py`) operate on this effective-role string. The stored `users.role` column is never exposed directly to clients as "the role" — `/auth/me` returns the effective role.

## 2. Architecture: FastAPI as the single Supabase integration point

Clients (Flutter, customer web, admin web) never talk to Supabase directly. All auth operations go through the FastAPI backend (`/api/v1/auth/*`), which proxies to Supabase's GoTrue REST API using `httpx` (see `app/integrations/supabase_auth.py`). This keeps rate limiting, input validation, and local-profile provisioning in one place, and lets every client use the same battle-tested token-storage strategy the backend hands back rather than each embedding a Supabase SDK with its own default (often `localStorage`-based) session persistence.

Access tokens are Supabase-issued JWTs. The backend validates them locally (HS256, `SUPABASE_JWT_SECRET`) on every request — no network call to Supabase is needed to authenticate a request. **The JWT's own `role` claim (Supabase's internal `authenticated`/`anon` Postgres role selector) is never used for application authorization** — the application role is always re-derived from the `users` table by the token's `sub` (user id). See `app/core/security.py`.

## 3. Registration and role assignment

`POST /auth/register` always creates the local `users` row with `role = customer`, regardless of any `role` field a client might send (the request schema doesn't even accept one). There is no self-service path to `artist`, `moderator`, `admin`, or `super_admin`:

* Becoming an Artist is a distinct onboarding flow (Phase 4 — artist profiles).
* Becoming Moderator/Administrator/Super Administrator is exclusively via `PATCH /api/v1/admin/users/{user_id}/role`, itself gated by RBAC, with two extra guards baked into the endpoint (not just the general RBAC dependency):
  1. A caller can never change their own role.
  2. Only `super_admin` may grant `admin` or `super_admin`; `admin` may grant `moderator` (and, later, verify artists) but not another admin.

## 4. Row-Level Security

Migration `<see migrations/versions/>` enables RLS and adds baseline policies (own-row read/write, admin-full-access) on: `users`, `profiles`, `user_preferences`, `user_devices`, `artist_profiles`, `designs` (public read for published rows), `bookings`, `messages`, `notifications`, `payments` (read-only, no client insert/update). This is a defense-in-depth backstop for any direct Supabase-mediated access path (Storage, or a future direct-to-Postgres client read) — **not** the primary authorization mechanism, which is the FastAPI RBAC layer above (see [security-baseline.md](security-baseline.md)). RLS policies read `auth.uid()`, Supabase's helper reading the JWT `sub` claim.

## 5. Storage-access policy foundations

No file upload endpoints exist yet (portfolio/verification-document upload is Phase 4+). This phase establishes the intended bucket layout and the Storage policies that will apply once buckets are created against a real Supabase project — see `infrastructure/supabase/storage_policies.sql`. The convention: every object path is prefixed `{user_id}/...`, and policies restrict `INSERT`/`UPDATE`/`DELETE` on `storage.objects` to the owning `auth.uid()` (or role-gated for moderation buckets).

## 6. Rate limiting

`register`, `login`, `password-reset/request`, and `verify-email/resend` are rate-limited via `slowapi` (Redis-backed) — 5 requests/minute per client IP. Exceeding the limit returns `429`.

## 7. Token storage per client

| Client | Storage | Why |
|---|---|---|
| Flutter | `flutter_secure_storage` (Keychain / EncryptedSharedPreferences-backed Keystore) | Never plaintext on disk. |
| Next.js customer web | httpOnly, `Secure`, `SameSite=Lax` cookies set by the web app's own `/api/auth/*` route handlers | Never touches `localStorage`/`sessionStorage`, not readable by client-side JS (mitigates XSS token theft). |
| Next.js admin web | Same cookie strategy as customer web, plus role-gated middleware. | Same. |

## 8. Known limitations of this phase

* Not tested against a live Supabase project — no real project credentials were available in this environment. `app/integrations/supabase_auth.py` is exercised in tests via mocked HTTP (`respx`); the JWT validation logic is exercised with real HS256 signing/verification using a test secret, which is genuine cryptographic behavior, not a stub. Wiring a real project only requires setting `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET` in `.env`.
* Social login is explicitly out of scope for this phase (no credentials available).
* RLS policies cover a representative set of tables, not all 41 — the same pattern (own-row + admin-override) extends to the rest as those tables gain direct-access use cases.

## 9. Related documents

* [database-schema.md](database-schema.md)
* [user-roles-and-permissions.md](user-roles-and-permissions.md)
* [security-baseline.md](security-baseline.md)
