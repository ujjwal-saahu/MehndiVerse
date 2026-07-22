# MehndiVerse — Design System (Phase 4)

Status: Draft (Phase 4)
Last updated: 2026-07-14

This document records the visual identity and shared design-token architecture introduced in Phase 4, and points to where each platform's component library lives. Phase 4 is UI shells and reusable components only — **no product data is connected**, and no screen is filled with invented sample data (see [feature-scope.md](feature-scope.md) for when each real feature lands).

## 1. Design direction

Elegant, premium, warm, and culturally resonant without leaning on literal/kitschy South-Asian-wedding clichés (gold-on-red, ornate borders). Concretely:

* **Color**: a deep wine/oxblood "henna" maroon as the brand primary (evokes henna stain without being literal orange-brown), a restrained marigold gold accent used sparingly, and a warm ivory/sand neutral scale for backgrounds and text instead of cold greys.
* **Typography**: a warm display serif (Fraunces) for headings paired with a clean geometric sans (Manrope) for body/UI text — editorial and premium rather than either "corporate SaaS" or "ornate wedding invitation."
* **Shape & elevation**: softly rounded corners (never sharp, never pill-heavy) and warm-tinted shadows (a brown-tinted rgba, not pure black) so elevation reads as soft rather than harsh.
* **Motion**: measured, decelerating transitions — no bounce/spring easing, which would read as playful rather than premium.
* **Layout**: image-forward. The design-grid components (web) and card-based layouts (Flutter) are built to let photography be the primary content, with minimal chrome around it.

## 2. Token architecture

Single source of truth: `packages/design-tokens/src/` (TypeScript). Categories: `color-palette.ts` (primitive scales), `colors.ts` (semantic light/dark mapping), `typography.ts`, `spacing.ts`, `radius.ts`, `shadows.ts`, `motion.ts`, `breakpoints.ts`, `icons.ts`.

Two consumers, no shared runtime code between them (Dart and TypeScript can't share a package directly):

* **Web/admin** (`apps/web`, `apps/admin`): `packages/design-tokens/src/tokens.css` is `@import`ed into each app's `globals.css` and feeds Tailwind v4's CSS-first `@theme`. Dark mode follows `prefers-color-scheme` by default, with an explicit `[data-theme="dark"|"light"]` override taking precedence (for a future theme toggle).
* **Flutter** (`apps/mobile`): `apps/mobile/lib/core/theme/design_tokens.dart` mirrors the same values by hand — **changes to the token source must be applied in both places**; there is no codegen bridging them yet. `AppTheme` (`app_theme.dart`) builds light/dark `ThemeData` from these tokens; `AppColors` (`app_colors.dart`) is a `ThemeExtension` exposing the semantic color set beyond what `ColorScheme` covers natively.

Fonts: web/admin load Fraunces/Manrope via `next/font/google`. Flutter intentionally uses the platform default font (Roboto/San Francisco) for now rather than bundling the same webfonts — see the comment in `design_tokens.dart` — to avoid a network-dependent font-fetch package in this phase; the type *scale* (sizes/weights/line-heights) still matches across platforms.

## 3. Component inventory

### Flutter (`apps/mobile/lib/core/widgets/`)
`AppPrimaryButton` / `AppSecondaryButton` / `AppTextActionButton`, `AppTextField`, `AppCard`, `showAppConfirmDialog`, `AppLoadingIndicator` / `AppLoadingView`, `AppSkeleton` (+ `.circle`), `AppEmptyState`, `AppErrorState`, `AppSnackBar` (success/error/info), `PlaceholderScreen` (a "not built yet" tab body).

Navigation: `CustomerShell` and `ArtistShell` (`apps/mobile/lib/core/navigation/`) are `StatefulShellRoute.indexedStack`-backed bottom-navigation shells with distinct tab sets, selected by the authenticated user's effective role in `app_router.dart`'s redirect logic (never client-trusted for anything beyond navigation UX — see [authentication.md](authentication.md)).

### Customer web (`apps/web/src/components/`)
`nav/PublicNav`, `nav/Footer`, `layout/SiteShell` (marketing route-group layout), `layout/AuthLayout` (auth route-group layout), `design-grid/DesignCard` + `DesignGrid` (loading/empty/populated states), `feedback/EmptyState` / `ErrorState` / `Skeleton`, `forms/FormField` / `SubmitButton`. Route-segment `loading.tsx`/`error.tsx` boundaries live in `src/app/(marketing)/`.

### Admin (`apps/admin/src/components/`)
`layout/Sidebar` (permission-aware — filters by the signed-in staff member's effective role, see `nav-items.ts`), `layout/Header`, `layout/DashboardShell` (responsive: fixed sidebar ≥ `lg`, drawer below it), `table/DataTable` (generic, typed by row shape; loading/empty states built in), `forms/FormField` / `SubmitButton`, `feedback/ComingSoon` (used by the five placeholder dashboard sections — Users, Verification, Moderation, Reports, Settings — none of which have real data or logic yet).

## 4. What Phase 4 deliberately does not do

* No API calls beyond what Phase 3 already wired (auth). Dashboard sections beyond the shell itself show `ComingSoon`/empty states, not fetched or invented data.
* No shared React component package between `apps/web` and `apps/admin` — each app owns its own local component set. They're intentionally similar (same tokens, same patterns) but not deduplicated into a `packages/ui` package in this phase; revisit if/when a third web surface needs the same primitives.
* Flutter's artist/customer navigation shells hold only placeholder tab bodies (`PlaceholderScreen`) — no booking, portfolio, or messaging logic yet (see [development-roadmap.md](development-roadmap.md) for when those phases land).

## 5. Accessibility

Every component library includes at least one automated accessibility check:

* **Flutter**: `flutter_test`'s built-in guidelines — `textContrastGuideline`, `androidTapTargetGuideline`, `labeledTapTargetGuideline` — run against interactive components and the login screen.
* **Web/admin**: `jest-axe` (`axe-core` under the hood) run against every component test file, plus semantic HTML (`role="alert"` for errors, `aria-invalid`/`aria-describedby` wiring on form fields, `aria-current="page"` on active nav links).

## 6. Related documents

* [product-requirements.md](product-requirements.md)
* [system-architecture.md](system-architecture.md)
* [authentication.md](authentication.md)
