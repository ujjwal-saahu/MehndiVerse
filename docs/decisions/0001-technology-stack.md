# ADR 0001 — Technology Stack Selection

Status: Accepted
Date: 2026-07-14

## Context

MehndiVerse needs a mobile app, a customer-facing web app, an admin dashboard, and a backend API, backed by a relational database, cache/queue, object storage, and integrations for auth, push notifications, payments, and AI. The stack must support a small team shipping incrementally in well-scoped phases (per [development-roadmap.md](../development-roadmap.md)), with strict server-side authorization (per [security-baseline.md](../security-baseline.md)) and no placeholder/mock production flows.

## Decision

Adopt the following stack:

**Mobile**: Flutter, Dart, Riverpod (state management), GoRouter (navigation), Dio (HTTP client), Freezed (immutable models/unions), Firebase Cloud Messaging (push).

**Web and admin**: Next.js with TypeScript and the App Router, Tailwind CSS, TanStack Query (server state), React Hook Form + Zod (forms/validation). Customer web app and admin dashboard are separate Next.js applications sharing the same conventions, not a single app with role-gated routes.

**Backend**: FastAPI (Python), Pydantic (validation), SQLAlchemy (ORM), Alembic (migrations), PostgreSQL (primary datastore), Redis (cache + queue), background worker processes for async jobs.

**Platform services**: Supabase for PostgreSQL hosting, Authentication, and Storage, with Row-Level Security as a data-layer authorization backstop. Firebase Cloud Messaging for push delivery. Sentry for error monitoring. PostHog for product analytics. Payment provider integrated behind an internal abstraction (concrete provider selection deferred — see [product-requirements.md](../product-requirements.md#7-open-questions--decisions-deferred)).

## Rationale

* **Flutter** gives a single codebase for iOS and Android, appropriate for a small team covering both customer and artist mobile experiences. Riverpod + GoRouter + Freezed + Dio is a cohesive, widely-adopted combination for typed, testable state/navigation/networking rather than mixing paradigms.
* **Next.js App Router + TypeScript** gives the web and admin apps a shared, modern React foundation with strong typing end-to-end when paired with Zod schemas that can mirror backend Pydantic models conceptually. TanStack Query standardizes server-state caching/invalidation instead of ad hoc fetch logic. Separate customer and admin apps keep the higher-trust admin surface isolated from the public-facing app (different deployment, different auth posture, smaller blast radius if either is compromised).
* **FastAPI + Pydantic + SQLAlchemy + Alembic** gives strict request/response validation, a mature ORM/migration pairing, and async support suited to a backend fronting three clients and multiple external providers. Centralizing business logic and authorization here (rather than in any client) is required by [security-baseline.md](../security-baseline.md).
* **PostgreSQL via Supabase** provides a managed relational database with built-in Row-Level Security, Auth, and Storage as a coherent platform, reducing the number of separate vendors/services a small team must operate.
* **Redis** is a standard, low-overhead choice for both caching hot reads (design catalog/search) and acting as a broker for background job processing, avoiding a heavier dedicated message-queue product before scale demands it.
* **Sentry + PostHog** are industry-standard, quick-to-integrate choices for error monitoring and product analytics respectively, needed from MVP per [product-requirements.md](../product-requirements.md#6-non-functional-requirements).
* **Abstracting payment and AI providers** behind internal interfaces defers a vendor commitment that depends on business/region decisions not yet made (see open questions in [product-requirements.md](../product-requirements.md)), while still letting architecture and phased delivery proceed now.

## Alternatives considered

* **React Native instead of Flutter** — rejected: Flutter's single-codebase widget model and the team's stated stack preference give more consistent cross-platform behavior for a design-heavy, image-centric app.
* **A single Next.js app with role-gated routes instead of separate customer/admin apps** — rejected: mixing public and staff-only surfaces in one deployable increases blast radius and complicates auth posture; separate apps sharing conventions is a small operational cost for meaningfully better isolation.
* **Django REST Framework or Node/Express instead of FastAPI** — rejected: FastAPI's native Pydantic validation and async support fit the strict-validation and background-worker requirements directly, without bolting on separate validation layers.
* **Self-hosted Postgres + custom auth instead of Supabase** — rejected at this stage: Supabase bundles Postgres, Auth, and Storage with Row-Level Security, reducing operational surface for a small team; this can be revisited later if platform limitations emerge, but that would be a future ADR, not a Phase 0 change.
* **A dedicated message queue (e.g., RabbitMQ, SQS) instead of Redis-backed jobs** — rejected for now: Redis already serves as the cache, and using it as the queue broker too avoids operating an additional service before there's a demonstrated need for a heavier queue.

## Consequences

* Every phase that touches these layers should reuse this stack rather than introducing alternatives; any deviation should be recorded as a new ADR, not a silent substitution.
* The payment and AI provider decisions remain open and must be resolved (and recorded in a future ADR) before Phase 7 (Payments) and Phase 13 (AI-assisted discovery) respectively, per [development-roadmap.md](../development-roadmap.md).
* Operating this stack requires accounts/projects with Supabase, Firebase, Sentry, and PostHog at minimum before Phase 1 scaffolding begins; none of these are provisioned yet as of Phase 0.

## Related documents

* [system-architecture.md](../system-architecture.md)
* [security-baseline.md](../security-baseline.md)
* [development-roadmap.md](../development-roadmap.md)
