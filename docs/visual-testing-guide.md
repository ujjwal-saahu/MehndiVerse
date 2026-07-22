# MehndiVerse — Local Visual Testing Guide

How to stand up the whole system (backend, workers, customer web, admin dashboard, Flutter) on this machine for manual/visual testing. Not staging, not production — a local, disposable environment.

## Real registration/login now works locally

`SUPABASE_URL`/`SUPABASE_JWT_SECRET` in `apps/api/.env` are placeholders — there's no real Supabase project, so real registration/login would normally fail outright (it really calls Supabase's Auth API). This session adds `apps/api/scripts/fake_supabase_auth.py`, a small local stand-in implementing just the handful of Auth endpoints `app/integrations/supabase_auth.py` calls (signup, password login, refresh, logout, recover, resend) — not part of the product, a dev-only test double. `apps/api/.env`'s `SUPABASE_URL` now points at it (`http://localhost:9999`), so **typing a real email/password into the web, admin, or Flutter login/register form actually works** — this matters most for Flutter, whose session storage is encrypted (`flutter_secure_storage`, WebCrypto-backed on web) and can't be hand-edited via DevTools the way a plain cookie can.

Two things to know:
- **Email TLD matters.** Pydantic's `EmailStr` rejects RFC-2606-reserved TLDs (`.test`, `.invalid`, `.localhost`) as "not a valid email address" — this is why seed accounts use `@mehndiverse.example`, not `@mehndiverse.test`.
- **Web/admin still also support cookie injection** (see [Test accounts](#test-accounts)) — either sign in for real (email above + any password) or inject a minted cookie; both work now. Flutter only supports the real sign-in path.

The fake Auth server pre-seeds the 5 persona emails below mapped to their real seeded `User` row ids (`apps/api/scripts/.fake_supabase_users.json`, gitignored), so logging in as `customer@mehndiverse.example` (any password) resolves to the same account that already has bookings/reviews — it does not check the password.

## Prerequisites already satisfied on this machine

- Docker Desktop running; `docker compose ps` shows `postgres`/`redis` healthy on ports **15432**/**16379** (this project's `docker-compose.yml`, just non-default host ports — already up, nothing to start).
- `apps/api/.env` already exists and points at those ports. Two values were edited this session (both local-only, gitignored, no product code touched):
  - `CORS_ORIGINS` — added `http://localhost:5000` (Flutter web) alongside the existing `:3000`/`:3001`.
  - `SUPABASE_URL` — changed from the real-placeholder domain to `http://localhost:9999` (the fake Auth stand-in below), so registration/login actually work.
- Flutter SDK at `C:\src\flutter` (not on PATH by default — see [Flutter](#flutter)). Upgraded this session from 3.41.5 to **3.44.7** to satisfy `pubspec.yaml`'s `sdk: ^3.12.2`.

## Startup order

1. Docker services (postgres, redis) — already running; `docker compose up -d postgres redis` if they're ever down.
2. Database migrations.
3. Seed data.
4. Fake Supabase Auth stand-in (must be up *before* the backend, since the backend calls it during registration/login).
5. Backend API.
6. Background workers (the AI-job poll loop — see below).
7. Customer web app.
8. Admin dashboard.
9. Flutter (Chrome, or Android emulator once it boots).

## Exact commands

```bash
# 1-2. Migrations (already at head; safe to re-run)
cd apps/api && .venv/Scripts/python -m alembic upgrade head

# 3. Seed data — idempotent, safe to re-run any time
cd apps/api && .venv/Scripts/python scripts/seed_local_data.py

# 4. Fake Supabase Auth stand-in (http://localhost:9999) — start before the backend
cd apps/api && .venv/Scripts/python scripts/fake_supabase_auth.py

# 5. Backend API (http://localhost:8000)
cd apps/api && .venv/Scripts/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 6. Background workers — these are periodic CLI scripts, not daemons
# (see docs/performance-and-reliability.md#background-job-retries). Running
# process_ai_jobs on a loop matters if you use the AI Design Assistant
# sandbox during this session; the others (reconcile_payments,
# process_subscriptions, process_account_deletions) can just be run once.
cd apps/api && while true; do .venv/Scripts/python -m app.cli.process_ai_jobs; sleep 10; done
cd apps/api && .venv/Scripts/python -m app.cli.reconcile_payments
cd apps/api && .venv/Scripts/python -m app.cli.process_subscriptions
cd apps/api && .venv/Scripts/python -m app.cli.process_account_deletions

# 7. Customer web app (http://localhost:3000)
cd apps/web && npx next dev -p 3000

# 8. Admin dashboard (http://localhost:3001)
cd apps/admin && npx next dev -p 3001

# 9. Flutter — Chrome (works out of the box)
cd apps/mobile
export PATH="/c/src/flutter/bin:$PATH"   # or add C:\src\flutter\bin to PATH permanently
flutter run -d chrome --web-port 5000

# 9. Flutter — Android emulator (see "Flutter" section below for status)
flutter emulators --launch flutter_emulator
adb devices                    # wait until it shows "device", not "offline"
adb reverse tcp:8000 tcp:8000  # required — see "Android emulator networking"
flutter run -d emulator-5554
```

`apps/web/.env.local` and `apps/admin/.env.local` were created with `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` (gitignored, safe, no secrets — copy these two lines yourself if they're ever missing).

## URLs and ports

| Service | URL | Port |
|---|---|---|
| Backend API | http://localhost:8000 | 8000 |
| API docs (Swagger) | http://localhost:8000/docs | 8000 |
| Fake Supabase Auth stand-in | http://localhost:9999 | 9999 |
| Customer web | http://localhost:3000 | 3000 |
| Admin dashboard | http://localhost:3001 | 3001 |
| Flutter (Chrome) | http://localhost:5000 | 5000 |
| Postgres | localhost:15432 | 15432 |
| Redis | localhost:16379 | 16379 |
| Flutter DevTools | printed by `flutter run` at startup | varies |

## Test accounts

Seeded by `apps/api/scripts/seed_local_data.py` (re-run any time — it's idempotent). Printed persona **user IDs** feed into the session-minting script below.

| Persona | Email | Role | Notes |
|---|---|---|---|
| Customer | `customer@mehndiverse.example` | customer | Has 4 bookings (requested/quoted/confirmed/completed) with "Henna by Meera" and 1 review |
| Artist (unverified) | `artist@mehndiverse.example` | artist | `verification_status = submitted` — should be redirected to onboarding |
| Verified artist | `verified-artist@mehndiverse.example` | artist | `verification_status = approved`, business "Henna by Meera", 2 services, Mon-Fri availability, owns half the seeded designs |
| Moderator | `moderator@mehndiverse.example` | moderator | Can reach `/dashboard/reports` in admin |
| Admin | `admin@mehndiverse.example` | administrator | Full admin access |

**Signing in as one**: mint session tokens (never prints the JWT secret itself, only per-persona session tokens):

```bash
node scripts/mint_local_sessions.mjs <customerId> <artistId> <verifiedArtistId> <moderatorId> <adminId>
```

(the 5 UUIDs `seed_local_data.py` printed when you ran it). Then in the browser: **DevTools → Application → Cookies → localhost:3000** (or **:3001** for admin) **→ add cookie** `mv_access_token` (name it `mv_admin_access_token` instead, for admin) with the printed value, domain `localhost`, path `/`. Reload the page.

## Expected screens

- **Customer web, signed out** (`/`): public landing/discover browsing, login/register links in the header and footer (including the new `/legal/*`, `/faq`, `/support/*` pages).
- **Customer web, signed in as `customer`**: `/account` shows the profile; `/discover` and `/search` show the 8 seeded designs with their placeholder thumbnails; `/bookings` shows the 4 seeded bookings in different statuses.
- **Verified artist**: `/artist/bookings` shows a booking inbox with the same 4 bookings from the artist's side; `/artist/services` shows the 2 seeded services; `/artist/availability` shows Mon-Fri 10:00-18:00.
- **Unverified artist**: any `/artist/*` route redirects to `/artist/onboarding`.
- **Admin, signed in as `moderator`**: `/dashboard/reports` reachable, queue empty (no seeded reports).
- **Admin, signed in as `admin`**: full dashboard, `/dashboard/users` lists all 5+ seeded users.
- **Flutter (Chrome, `http://localhost:5000`)**: app boots to the home/gallery screen. Register or log in for real with any `@mehndiverse.example` persona email (or any new email) and any password — see [Real registration/login now works locally](#real-registrationlogin-now-works-locally).

## Flutter

A real Flutter SDK exists at `C:\src\flutter` (not on PATH) — this was not previously known/documented in this project; every prior phase's docs said no Flutter/Dart toolchain existed in the *sandbox this assistant runs commands from*, which is still true for that separate environment, but **this Windows host has one**.

- **Android**: Android SDK fully configured, licenses accepted, one AVD (`flutter_emulator`) exists. This session's emulator boot was very slow and never finished (`adb devices` showed `offline` for 20+ minutes; the `qemu-system-x86_64` process was genuinely running, not crashed). **Chrome was used instead** for this session, per the fallback the task allowed. To retry Android yourself: `flutter emulators --launch flutter_emulator`, wait (it may take several minutes), then `adb devices` until it reads `device`.
- **Android emulator networking**: the emulator's `localhost` refers to itself, not this machine. Run `adb reverse tcp:8000 tcp:8000` once the emulator is up, so the app's hardcoded `http://localhost:8000` (`lib/core/config/app_environment.dart`) actually reaches the backend. No code change needed.
- **Web (Chrome/Edge)**: required `flutter config --enable-web` (feature flag was off by default) — now enabled. `apps/mobile` has no `web/` directory scaffolded, and `flutter run -d chrome` prints a "not configured to build on the web" warning, but launches anyway using Flutter's default web scaffold; it served real content at `http://localhost:5000` with no runtime errors in this session.
- **Dependency versions**: `flutter upgrade` was required (3.41.5 → 3.44.7) to satisfy `pubspec.yaml`'s `environment.sdk: ^3.12.2` constraint — `flutter pub get` failed outright before this.

## Shutdown commands

```bash
# Stop dev servers/workers: Ctrl-C each foreground terminal, or if backgrounded:
# find the PID by port and stop it
netstat -ano | grep ":8000\|:9999\|:3000\|:3001\|:5000"   # Git Bash
# PowerShell equivalent:
# Get-NetTCPConnection -LocalPort 8000,9999,3000,3001,5000 -State Listen |
#   ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }

# Stop the Android emulator (if launched)
adb emu kill

# Docker services (only if you want them fully down — they're normally left running)
docker compose down
```

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Web/admin page loads but shows no data / 401s | Session cookie missing/expired | Re-mint with `mint_local_sessions.mjs` and re-add the cookie (7-day expiry) |
| Registering/logging in fails with a network error (`XMLHttpRequest onError` on Flutter web) | Backend CORS didn't allow the calling origin | `apps/api/.env`'s `CORS_ORIGINS` already includes `:3000`/`:3001`/`:5000`; add your port and restart uvicorn if you use a different one |
| Registering/logging in fails with "not a valid email address" | Pydantic's `EmailStr` rejects RFC-2606-reserved TLDs (`.test`, `.invalid`, `.localhost`) | Use `.example` or a normal-looking TLD, not `.test` |
| Login/register still fails after the above | `scripts/fake_supabase_auth.py` isn't running, or `apps/api/.env`'s `SUPABASE_URL` still points at the real placeholder domain | Start it (step 4) and confirm `SUPABASE_URL=http://localhost:9999`; restart uvicorn after changing `.env` — settings are cached per-process |
| Design/artist images don't render | `next.config.ts`'s `images.remotePatterns` doesn't allow the host the URL uses | Seeded images use `http://localhost:3000/seed/*.svg`, already allow-listed; a different host needs its own `remotePatterns` entry |
| `flutter pub get` fails with an SDK version error | Installed Flutter SDK older than `pubspec.yaml` requires | `flutter upgrade` (already done this session, now on 3.44.7) |
| Android emulator never leaves "offline" | Slow first boot / resource contention | Give it several more minutes; `adb kill-server` then re-run `adb devices` if it seems stuck; otherwise use Chrome |
| AI Design Assistant sandbox request never completes | The `process_ai_jobs` poll loop isn't running | Start the loop command from [Exact commands](#exact-commands) — jobs are processed by a periodic script, not automatically |
| `docker compose ps` shows nothing running | Containers were stopped | `docker compose up -d postgres redis` |

## Related documents

- `docs/test-matrix.md`, `docs/staging-deployment.md` — the equivalent automated (not manual/visual) verification this guide complements.
- `docs/authentication.md` — why real Supabase Auth can't be exercised without real credentials.
