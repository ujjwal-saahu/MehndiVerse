# MehndiVerse — Security Baseline

Status: Draft (Phase 0)
Last updated: 2026-07-14

This document defines the security requirements that apply across every phase of MehndiVerse, not a one-time checklist. Every phase in [development-roadmap.md](development-roadmap.md) must satisfy the applicable sections below before it is considered complete.

## 1. Authentication

* Supabase Authentication is the sole identity provider for all three clients (Flutter, customer Next.js, admin Next.js). No parallel/custom auth system is introduced.
* Sessions are represented as short-lived JWTs; clients refresh via Supabase's standard mechanisms rather than long-lived static tokens.
* The admin dashboard requires staff-role accounts (Moderator/Administrator/Super Administrator); staff accounts are provisioned by administrative action, not public self-registration.

## 2. Authorization

* Authorization is enforced **server-side, in FastAPI**, on every request, based on the role and resource-ownership model in [user-roles-and-permissions.md](user-roles-and-permissions.md). Client-side role checks (hiding a button, disabling a route in GoRouter/Next.js middleware) are UX conveniences only and are never trusted as the security boundary.
* PostgreSQL Row-Level Security policies provide an independent second enforcement layer for any Supabase-mediated data access path (e.g., direct Storage or database access), so a defect in the API layer does not by itself expose data.
* Role elevation (e.g., Customer → Artist, Artist → Verified Artist, granting staff roles) always happens through an explicit, audit-logged administrative action — never a self-service field a user can set on their own record.
* Admin and super-admin actions that change another account's role, verification status, payments, or system configuration are audit-logged with actor, timestamp, and before/after state.

## 3. Secrets management

* No `.env` files, credentials, API keys, or service-role keys are ever committed to the repository.
* Every service that needs configuration ships a `.env.example` listing required variable names with placeholder (non-functional) values only.
* Supabase service-role keys, payment-provider secret keys, and AI-provider API keys are used only in backend/worker contexts, never bundled into the Flutter app or shipped to a browser.
* Production secrets are managed via the hosting platform's secret manager, not via files in the repository or CI logs.

## 4. Data protection

* All traffic between clients, the backend, and third-party providers uses TLS.
* PostgreSQL data at rest is encrypted via the underlying Supabase-managed infrastructure.
* Verification documents and other sensitive uploads are stored in access-controlled Supabase Storage buckets, never in publicly-readable buckets, and are only retrievable through backend-authorized, time-limited URLs.
* Personally identifiable information is scoped to what the product requires; analytics events sent to PostHog and error reports sent to Sentry are reviewed for PII and scrubbed/redacted before instrumentation ships in each phase.

## 5. Payment security

* MehndiVerse never handles or stores raw payment instrument data (card numbers, CVV). All card entry happens through the payment provider's hosted/tokenized flow.
* The backend stores only provider-issued references (charge/transaction IDs, status), consistent with the data-ownership boundary in [system-architecture.md](system-architecture.md#8-data-ownership-boundaries).
* Refunds at MVP are administrator-mediated and audit-logged, reducing the surface for self-service abuse until an automated flow is deliberately designed (Post-MVP).

## 6. API security

* All request payloads are validated against strict Pydantic schemas; no unvalidated input reaches business logic or the database.
* Rate limiting applies to public/guest-accessible endpoints (search, AI discovery/preview) to prevent abuse, per the "rate-limited" guest allowances in [user-roles-and-permissions.md](user-roles-and-permissions.md).
* CORS is restricted to known client origins (customer web app, admin dashboard); it is not left open (`*`) once real origins are known.
* File uploads (portfolio images, verification documents, chat attachments) are validated for type and size server-side before storage, regardless of client-side validation.

## 7. Dependency and supply-chain hygiene

* No dependency is added "for later" — every dependency introduced in a phase must be used by that phase's shipped code, per the project's engineering rules.
* Dependencies are pinned via each ecosystem's standard lockfile mechanism (e.g., `pubspec.lock`, `package-lock.json`/`pnpm-lock.yaml`, Python lockfile) once those ecosystems are introduced starting Phase 1.
* Security-relevant dependency updates are not deferred indefinitely; each phase that touches a package manager should leave dependencies in a currently-supported state.

## 8. Observability without leakage

* Sentry captures errors from all clients and the backend from MVP onward, configured to scrub sensitive fields (tokens, payment references, verification document contents) from breadcrumbs and payloads.
* PostHog captures product usage events; event payloads are reviewed to exclude sensitive personal data beyond what analysis requires.

## 9. Compliance posture

* Verification documents and personal data retention practices must account for applicable data-subject rights (access/deletion) once a jurisdiction is finalized — flagged as an open question in [product-requirements.md](product-requirements.md#7-open-questions--decisions-deferred), not resolved in Phase 0.
* Data deletion requests (account closure) must cascade or anonymize dependent records (bookings, reviews, messages) consistent with what the eventual compliance requirement demands — to be designed explicitly in the phase that introduces account deletion, not assumed.

## 10. Verification expectation per phase

Every phase's report (per the project's required response format) must confirm: no secrets were created or committed, authorization was implemented server-side (not only in UI), and no unnecessary dependencies were introduced.

## 11. Related documents

* [user-roles-and-permissions.md](user-roles-and-permissions.md)
* [system-architecture.md](system-architecture.md)
* [decisions/0001-technology-stack.md](decisions/0001-technology-stack.md)
