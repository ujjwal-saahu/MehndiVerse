# MehndiVerse — Localization and Accessibility (Phase 23)

Phase 23 adds i18n/RTL infrastructure and an accessibility pass to `apps/web` (the customer-facing Next.js app) plus a small backend foundation in `apps/api`. Scope was explicitly narrowed to these two surfaces — `apps/admin` and `apps/mobile` are **not** touched by this phase (see [What this phase deliberately does not do](#what-this-phase-deliberately-does-not-do)).

Four locales are supported end to end: English (`en`), Hindi (`hi`), Urdu (`ur`), Arabic (`ar`) — the latter two right-to-left.

## Translation-file architecture

`apps/web/src/i18n/locales/{en,hi,ur,ar}.json` — one flat-nested JSON catalog per locale, all four sharing an identical key shape (enforced by a test, see [Missing-translation detection](#missing-translation-detection)). `en.json` is the base; its inferred TypeScript type (`typeof en`) is exported as `Messages` from `src/i18n/translations.ts`.

`translate(locale, key, params?)` (`src/i18n/translations.ts`) resolves a dot-path key (e.g. `"auth.login.title"`) against the target locale, falling back to `en` and then to the literal key string if nothing resolves — so a missing key degrades to visible-but-not-crashing rather than a blank UI. `{{param}}` placeholders are interpolated (used by `footer.rights` for the copyright year).

No i18n library (`next-intl`, `react-i18next`, etc.) was introduced. `apps/web/AGENTS.md` warns this Next.js version has training-data-breaking changes, and `next-intl`'s usual pattern — routing every page under a `[locale]` dynamic segment — would have meant restructuring the entire existing `app/(marketing)`/`app/(auth)` route tree, a large, high-risk diff for a foundation phase. The custom Context + cookie approach below achieves the same locale-switching UX without touching the route structure.

## Locale selection

`src/components/nav/language-switcher.tsx` — a `<select>` (native, so it's fully keyboard/screen-reader accessible without extra ARIA work) offering the four `SUPPORTED_LOCALES`, mounted in `PublicNav`. `src/app/(marketing)/account/settings/settings-form.tsx` has a second, equivalent selector (its pre-existing `LANGUAGES` array — a leftover from an earlier phase that offered `en/hi/mr/gu/ta`, none of which matched this phase's four supported locales — is now driven by the same `SUPPORTED_LOCALES` list).

Both call `useTranslation().setLocale()` (`src/i18n/locale-provider.tsx`), which updates the `mv_locale` cookie, updates every subscribed component immediately (no reload), and calls `router.refresh()` so server-rendered content (nav labels, `<html lang/dir>`) catches up.

## Persisted language preference

Two persistence layers, for two different situations:

- **`mv_locale` cookie** (`src/i18n/config.ts::LOCALE_COOKIE`, 1-year `max-age`) — works for signed-out visitors, read on every request so SSR renders in the right language/direction with no flash of the wrong locale. Deliberately *not* `httpOnly`: the language switcher writes it directly from the client for an instant switch.
- **`Profile.locale`** (pre-existing column from an earlier phase, `apps/api/app/db/models/user.py`) — the signed-in account's preference, so it follows the user to a new device/browser. `SettingsForm` PATCHes `/api/profile` (unchanged endpoint) *and* calls `setLocale()` so the change also applies to the current browser session immediately.

`resolveLocale()` (`src/i18n/resolve-locale.ts`) is the single place that decides which locale to render with, in priority order: `mv_locale` cookie → browser `Accept-Language` header → `DEFAULT_LOCALE` ("en"). `RootLayout` (`src/app/layout.tsx`) calls it once, server-side, to set `<html lang>`/`<html dir>` and seed `LocaleProvider`'s initial state — verified against a running dev server:

```text
curl -s http://localhost:3000/                                  -> <html lang="en" dir="ltr" ...>
curl -s -H "Accept-Language: ar" http://localhost:3000/          -> <html lang="ar" dir="rtl" ...>
curl -s -H "Cookie: mv_locale=ur" -H "Accept-Language: en" .../  -> <html lang="ur" dir="rtl" ...>  (cookie wins over header)
```

## RTL layout support

`<html dir="rtl">` is set server-side for `ur`/`ar` (see above) — no client-side flash. `apps/web/src/app/globals.css` adds:

- A `@media (prefers-reduced-motion: reduce)` block (see [Reduced-motion support](#reduced-motion-support)) and an `[dir="rtl"]` safety net (`text-align: right` plus logical margins on checkbox/radio inputs) for the handful of native form-control defaults that don't flip automatically under `dir="rtl"`.
- New/touched components in this phase use Tailwind's logical spacing utilities (`ms-`/`me-`/`ps-`/`pe-`) where directionality matters, so they flip automatically; this phase did not do a full sweep of every physical (`ml-`/`mr-`) utility class already in the wider app (dozens of pages, out of scope for a foundation phase — see [What this phase deliberately does not do](#what-this-phase-deliberately-does-not-do)) — a manual RTL visual pass over the rest of the app is listed under [Remaining manual accessibility checks](#remaining-manual-accessibility-checks).
- This CSS lives in `apps/web/src/app/globals.css`, **not** the shared `packages/design-tokens/src/tokens.css` (which both `apps/web` and `apps/admin` import) — keeping it scoped means it can't affect the out-of-scope admin app.

## Localized dates, numbers, and currencies

`src/i18n/format.ts` — thin wrappers over `Intl.DateTimeFormat`/`Intl.NumberFormat`, taking the current `Locale` explicitly rather than relying on browser defaults:

- `formatDate` / `formatShortDate` — long/short localized date strings.
- `formatNumber` — locale-appropriate grouping (e.g. `en` uses `en-IN`, so `1234567` → `"12,34,567"` Indian-style grouping, matching the app's primary market).
- `formatCurrency(amount, currency, locale)` — `Intl.NumberFormat` with `style: "currency"`; currency code is passed explicitly (e.g. `"INR"`) rather than inferred from locale, since a user's display language and their billing currency aren't the same thing.

These are new utilities, not yet wired into every price/date display across the app (see [What this phase deliberately does not do](#what-this-phase-deliberately-does-not-do)) — they establish the pattern for call sites to adopt incrementally.

## Localized validation messages

Two layers:

- **Frontend (primary)** — `src/i18n/validation-messages.ts::useValidationMessages()` returns the localized strings for the handful of Zod rules reused across forms (invalid email, password requirements, display-name-required, bio-too-long, invalid country code). The four existing Zod-schema forms (`(auth)/login`, `(auth)/register`, `(auth)/forgot-password`, `account/edit/edit-profile-form.tsx`) now build their `z.object(...)` schema inside a `useMemo` keyed on these messages, instead of a module-level schema with hardcoded English literals — so validation errors re-render in the active locale without a page reload.
- **Backend (foundation only)** — `apps/api/app/core/i18n.py`. FastAPI's `RequestValidationError` handler already only ever returned one fixed generic message ("Request validation failed.") — Pydantic's per-field error detail was never exposed to API clients, so there was no per-field backend message to localize. That message, plus `AuthenticationError`/`AuthorizationError`'s *default* messages and the generic 500 message, are now resolved through a small locale catalog keyed off the request's `Accept-Language` header (see [Backend message localization](#backend-message-localization) for the exact mechanics and its deliberately limited scope).

## Missing-translation detection

`apps/web/src/i18n/translations.test.ts` — for each of the four locales: flattens its JSON to a dot-path key set and asserts it's *exactly* the same set as `en.json`'s (both directions — reports both missing and extra keys), and separately asserts every value is a non-empty string. Runs as part of the normal `npm run test` (vitest) suite, so a translation drift fails CI the same way a broken test would, not silently.

## Backend message localization

`apps/api/app/core/i18n.py` — `SUPPORTED_LOCALES`, a small fixed catalog (`auth.required`, `auth.forbidden`, `validation.failed`, `error.internal`), `resolve_locale(accept_language)` (first supported primary-subtag match in the header, else `en`), and `translate(code, locale)`.

**Deliberately does not** retrofit the ~200+ existing `AppError("...")` call sites across the API — each already carries a specific, meaningful English message, and rewriting every one to a catalog key would be a large, high-risk diff disconnected from this phase's actual test surface (`apps/web` + a thin backend foundation, per the earlier scoping decision). Instead, `AppError` gained an optional `code: str | None` kwarg; `AuthenticationError`/`AuthorizationError` set it automatically **only when the caller didn't override the class's default message** — so `AuthenticationError()` (bare) localizes, but `AuthenticationError("Token expired, please log in again.")` (all 37 existing `AuthenticationError`/`AuthorizationError` call sites across the app pass a specific message today — none use the bare default) is left untouched, exactly as before. `register_exception_handlers`'s two fully system-owned messages — the generic validation-failure body and the unhandled-exception 500 — always localize, since they're never call-site-specific. `str(exc.detail)` on ad hoc `HTTPException`s is not localized (arbitrary per-call-site text, same reasoning as `AppError`).

Verified via a standalone test app (`tests/core/test_exceptions.py`) exercising all four locales end to end through real HTTP responses, plus unit tests for `resolve_locale`/`translate` (`tests/core/test_i18n.py`).

## Accessibility

### Screen-reader labels

`FormField` (pre-existing, `src/components/forms/form-field.tsx`) already associates label/input/error via `aria-invalid`/`aria-describedby` and renders errors with `role="alert"` — confirmed via its existing test, unchanged this phase. `LanguageSwitcher`'s `<select>` has a (visually hidden) `<label>`; the new `Dialog`'s close button has an `aria-label`.

### Keyboard navigation

The new `Dialog` component (below) traps Tab/Shift+Tab within itself while open. Everything else in this phase (language switcher, nav) is native `<select>`/`<a>`/`<button>` elements, which are keyboard-operable by default.

### Focus management

`Dialog` moves focus to its first focusable element (the close button) on open, and restores focus to whatever element was focused before it opened (typically the trigger) on close — both covered by tests in `dialog.test.tsx`.

### Accessible dialogs

`apps/web/src/components/a11y/dialog.tsx` — new; no dialog/modal component existed anywhere in `apps/web` before this phase (`preview-studio.tsx`/`image-gallery.tsx` render inline overlays without dialog semantics — unchanged, out of scope to retrofit this phase). `role="dialog"`, `aria-modal="true"`, `aria-labelledby` pointing at the title, Escape-to-close, backdrop-click-to-close, Tab focus trap, portal-rendered to `document.body`. No dependency added — implemented directly on `useRef`/`useEffect`/`createPortal`.

### Sufficient contrast

The design system's semantic color tokens (`packages/design-tokens/src/colors.ts`, pre-existing, unchanged) were already built around WCAG-conscious pairings (`text-primary` on `surface`/`background`, `text-on-primary` on `primary`) — this phase did not alter the palette. A full contrast audit of every token pairing (not just the ones this phase's components use) is listed under [Remaining manual accessibility checks](#remaining-manual-accessibility-checks).

### Large touch targets

The `Dialog` close button uses `p-3` (12px padding around a 20px icon → 44×44px), matching the WCAG 2.2 AA minimum target size. Existing components were not swept for touch-target size this phase (see [What this phase deliberately does not do](#what-this-phase-deliberately-does-not-do)).

### Reduced-motion support

`apps/web/src/app/globals.css` now has a `@media (prefers-reduced-motion: reduce)` block collapsing all animation/transition durations to near-zero and disabling smooth scrolling — scoped to `apps/web`'s own stylesheet (not the shared `tokens.css`) so `apps/admin` is unaffected.

### Image alternative text

Not newly introduced this phase; spot-checked the components this phase touched (`edit-profile-form.tsx`'s avatar `<Image>` already uses `alt=""` correctly, since the filename/context makes it decorative next to a labelled "Change photo" control).

### Form error announcements

Covered by `FormField`'s pre-existing `role="alert"` pattern (see [Screen-reader labels](#screen-reader-labels)) — confirmed still passing, not rebuilt.

## Automated accessibility checks

All new/touched interactive components have a `jest-axe` "no detectable accessibility violations" test, following the pattern already established elsewhere in `apps/web` (`forms.test.tsx`, etc.): `language-switcher.test.tsx`, `dialog.test.tsx`, `public-nav.test.tsx`, `settings-form.test.tsx`, `edit-profile-form.test.tsx`. These run as part of `npm run test`.

## Remaining manual accessibility checks

Not automatable, or out of this phase's scope to fully execute — tracked here for a future pass:

- **Real screen-reader testing** — NVDA/JAWS/VoiceOver walkthroughs of the login/register/settings/dialog flows in all four locales, including Urdu/Arabic (RTL screen-reader behavior can differ from LTR).
- **Full RTL visual review** — every page in the app under `dir="rtl"`, not just the components this phase touched, to catch physical (`ml-`/`mr-`/`left-`/`right-`) Tailwind utilities that don't flip automatically (see [RTL layout support](#rtl-layout-support)).
- **Full contrast audit** — every semantic color token pairing against WCAG AA/AAA, not just the pairings this phase's new components use.
- **Physical-device touch-target audit** — real mobile Safari/Chrome, not just computed CSS sizes.
- **Native-speaker translation review** — the Hindi/Urdu/Arabic strings in this phase were written to be accurate and natural, but weren't reviewed by native speakers of each language; this should happen before the four locales are presented as production-ready rather than foundation-complete.

## Do not auto-translate legal documents without review

No legal documents (terms of service, privacy policy, etc.) exist in the repository as of this phase — grepped for common filenames/routes (`terms`, `privacy-policy`, `legal`) and found none, so there was nothing to accidentally auto-translate. If/when such documents are added, they must go through human translation review before being added to the locale catalogs — the `translate()` fallback-to-English behavior described in [Translation-file architecture](#translation-file-architecture) means an untranslated legal document safely renders in English rather than a machine-translated draft, but this is not a substitute for an explicit review step.

## What this phase deliberately does not do

- **`apps/admin` and `apps/mobile`** — out of scope per this phase's explicit scoping decision; neither app's UI, forms, or routing were touched. (`packages/design-tokens/src/tokens.css`, shared by `apps/web` and `apps/admin`, was deliberately left unmodified for this reason — new CSS went into `apps/web/src/app/globals.css` instead.)
- **Translating every string in the app** — the four-locale catalog covers global nav/footer, the auth forms (login/register/forgot-password), and account/settings; the rest of the app (discover, search, booking flows, artist profiles, etc.) still renders in English. This phase's job was the *infrastructure* ("prepare support for" four languages, per the phase brief) — translation-file architecture, locale persistence, RTL, formatting utilities, missing-translation detection, validation-message localization, and the accessibility primitives — not an exhaustive copy pass over every page.
- **A full RTL sweep of pre-existing pages**, **a full contrast audit**, and **a full touch-target audit** of the whole app — see [Remaining manual accessibility checks](#remaining-manual-accessibility-checks).
- **Retrofitting every backend `AppError` call site** to a translation key — see [Backend message localization](#backend-message-localization) for why.
- **A new database migration** — `Profile.locale` already existed from an earlier phase; this phase reused it as-is (no schema change).
- **An i18n routing library** (`next-intl` et al.) — see [Translation-file architecture](#translation-file-architecture) for why a custom Context-based approach was chosen instead.

## Related documents

- [docs/analytics-and-recommendations.md](./analytics-and-recommendations.md) — the `record_event`/consent-flag pattern this phase's design decisions (e.g. never localizing a caller-overridden `AppError` message) took inspiration from for "small, additive foundation, not a full retrofit."
- [docs/ai-design-assistant.md](./ai-design-assistant.md) — the `AiProvider` abstraction, the precedent this codebase uses for "replaceable" provider-style abstractions (referenced conceptually while evaluating whether to introduce an i18n library).
