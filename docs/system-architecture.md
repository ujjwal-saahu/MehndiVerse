# MehndiVerse — System Architecture

Status: Draft (Phase 0)
Last updated: 2026-07-14

This document describes the target architecture for MehndiVerse at a component level. No code exists yet — this is the plan that later phases implement against. Nothing here should contradict [product-requirements.md](product-requirements.md) or [decisions/0001-technology-stack.md](decisions/0001-technology-stack.md).

## 1. Components

| Component | Technology | Responsibility |
|---|---|---|
| Mobile app | Flutter, Dart, Riverpod, GoRouter, Dio, Freezed, FCM | Customer and artist experience on iOS/Android. |
| Customer web app | Next.js, TypeScript, App Router, Tailwind CSS, TanStack Query, React Hook Form, Zod | Customer and artist experience on the web. |
| Admin dashboard | Next.js, TypeScript, App Router, Tailwind CSS, TanStack Query, React Hook Form, Zod | Moderator/Administrator/Super Administrator tooling. Separate app from the customer web app — different auth posture and audience. |
| Backend API | FastAPI, Python, Pydantic, SQLAlchemy, Alembic | Single source of business logic and authorization for all clients. Owns the domain: users, designs, artists, bookings, quotations, payments, messaging, reviews, admin operations. |
| Database | PostgreSQL (via Supabase) | System of record. Row-Level Security policies provide a data-layer authorization backstop. |
| Cache & queue | Redis | Read-through caching for hot catalog/search data; broker for background job queue. |
| Background workers | Python (worker processes consuming the Redis-backed queue) | Async work off the request path: notification fan-out, image/thumbnail processing, AI inference calls, scheduled/report jobs. |
| Object storage | Supabase Storage | Design images, portfolio media, verification documents, chat attachments. |
| Auth | Supabase Authentication | Identity, session/JWT issuance for all three clients. |
| Notification providers | FCM (push), transactional email provider | Booking/message/verification event delivery. |
| Payment provider | Abstracted behind an internal interface (concrete provider TBD per [product-requirements.md](product-requirements.md#7-open-questions--decisions-deferred)) | Deposit collection, refund initiation. |
| AI service | Abstracted behind an internal interface (concrete provider TBD) | Design discovery (search/recommendation) and hand/foot photo preview. Post-MVP per [feature-scope.md](feature-scope.md). |
| Observability | Sentry (errors), PostHog (product analytics) | Cross-cutting, wired into all clients and the backend from MVP. |

## 2. Architectural principles

* **One backend, three clients.** All business logic and authorization live in FastAPI. Flutter, the customer Next.js app, and the admin Next.js app are presentation layers that call the same API surface (admin-only endpoints are a distinct, separately authorized route group, not a separate service, at MVP).
* **Supabase Auth issues identity; FastAPI enforces authorization.** Clients authenticate against Supabase and attach the resulting token to API calls; the backend independently validates role/ownership on every request per [user-roles-and-permissions.md](user-roles-and-permissions.md) — client-side role checks are UX only, never the security boundary.
* **RLS is a second, independent layer**, not a replacement for backend checks — defense in depth for the case where Supabase-mediated access (e.g., direct storage access) bypasses the API.
* **Non-interactive work is asynchronous.** Anything that doesn't need to block a client response (notification delivery, image processing, AI calls) goes through Redis to a background worker.
* **External providers are abstracted.** Payment and AI providers sit behind internal interfaces so a provider swap is a config/adapter change, not a rewrite of business logic.

## 3. System architecture diagram

```mermaid
graph TB
    subgraph Clients
        Mobile["Flutter Mobile App<br/>(Customer + Artist)"]
        WebCustomer["Next.js Customer Web App"]
        WebAdmin["Next.js Admin Dashboard"]
    end

    subgraph Platform["Supabase"]
        Auth["Supabase Authentication"]
        Storage["Supabase Storage"]
    end

    subgraph Backend["Backend"]
        API["FastAPI Backend API"]
        Workers["Background Workers"]
    end

    DB[("PostgreSQL<br/>(Supabase, with RLS)")]
    Cache[("Redis<br/>Cache + Queue")]

    subgraph External["External Providers"]
        Push["FCM Push"]
        Email["Email Provider"]
        Payment["Payment Provider"]
        AI["AI Service"]
    end

    subgraph Observability
        Sentry
        PostHog
    end

    Mobile -->|REST/JSON, JWT| API
    WebCustomer -->|REST/JSON, JWT| API
    WebAdmin -->|REST/JSON, JWT| API

    Mobile -.->|auth| Auth
    WebCustomer -.->|auth| Auth
    WebAdmin -.->|auth| Auth

    API --> DB
    API --> Cache
    API --> Storage
    API -->|enqueue jobs| Cache
    Workers -->|dequeue jobs| Cache
    Workers --> DB
    Workers --> Storage
    Workers --> Push
    Workers --> Email
    Workers --> AI

    API --> Payment
    API -.->|validate token| Auth

    Mobile --> Sentry
    WebCustomer --> Sentry
    WebAdmin --> Sentry
    API --> Sentry
    Mobile --> PostHog
    WebCustomer --> PostHog
    WebAdmin --> PostHog
```

## 4. Customer journey

```mermaid
flowchart TD
    A[Guest opens app/web] --> B[Browse / search / filter designs]
    B --> C{AI discovery or\nphoto preview used?}
    C -->|Yes, post-MVP| D[AI service: recommend / preview]
    C -->|No| E
    D --> E[View design detail + artist profile]
    E --> F{Signed in?}
    F -->|No| G[Register / log in via Supabase Auth]
    G --> E
    F -->|Yes| H[Like / save design / follow artist]
    H --> I[Submit booking request to artist]
    I --> J[Await quotation]
    J --> K{Quotation received?}
    K -->|Declined| B
    K -->|Received| L[Review quotation, message artist]
    L --> M{Accept?}
    M -->|No| B
    M -->|Yes| N[Pay deposit via payment provider]
    N --> O[Booking confirmed]
    O --> P[Service delivered by artist]
    P --> Q[Leave review]
```

## 5. Artist journey

```mermaid
flowchart TD
    A[Register as Artist] --> B[Create profile]
    B --> C[Submit verification documents]
    C --> D{Admin review}
    D -->|Rejected| C
    D -->|Approved| E[Verified Artist status granted]
    B --> F[Upload portfolio]
    B --> G[Define services & pricing]
    B --> H[Set availability]
    F --> I
    G --> I
    H --> I
    E --> I[Fully visible in marketplace search]
    I --> J[Receive booking request from customer]
    J --> K[Send quotation]
    K --> L{Customer accepts?}
    L -->|No| J
    L -->|Yes, deposit paid| M[Booking confirmed]
    M --> N[Message customer, deliver service]
    N --> O[Booking marked complete]
    O --> P[Receive review]
    O --> Q[Earnings updated]
```

## 6. Booking lifecycle

```mermaid
stateDiagram-v2
    [*] --> Requested: Customer submits booking request
    Requested --> Quoted: Artist sends quotation
    Requested --> Declined: Artist declines
    Quoted --> Confirmed: Customer accepts + pays deposit
    Quoted --> Expired: Quotation not accepted in time
    Quoted --> Declined: Customer declines
    Confirmed --> Completed: Service delivered, marked complete
    Confirmed --> Cancelled: Cancelled by customer or artist
    Confirmed --> Disputed: Either party raises a dispute
    Disputed --> Completed: Admin resolves in favor of completion
    Disputed --> Cancelled: Admin resolves as cancelled/refunded
    Completed --> [*]
    Declined --> [*]
    Expired --> [*]
    Cancelled --> [*]
```

## 7. Deployment architecture

```mermaid
graph TB
    subgraph UserDevices["User Devices"]
        iOS["iOS / Android<br/>(Flutter app via App Store / Play Store)"]
        Browser["Browser"]
    end

    subgraph Edge["Edge / Hosting"]
        CDN["CDN / Edge Network"]
        WebHostCustomer["Next.js Customer App<br/>(hosted, SSR/edge)"]
        WebHostAdmin["Next.js Admin Dashboard<br/>(hosted, SSR/edge, restricted access)"]
    end

    subgraph Compute["Backend Compute (containerized)"]
        APIInstances["FastAPI instances<br/>(horizontally scalable)"]
        WorkerInstances["Background worker instances"]
    end

    subgraph SupabaseCloud["Supabase Cloud"]
        PG[("PostgreSQL + RLS")]
        SupaAuth["Supabase Auth"]
        SupaStorage["Supabase Storage"]
    end

    RedisHost[("Managed Redis")]

    subgraph Providers["Third-Party Providers"]
        FCMSvc["FCM"]
        EmailSvc["Email Provider"]
        PaymentSvc["Payment Provider"]
        AISvc["AI Service"]
    end

    subgraph Monitoring["Monitoring"]
        SentrySvc["Sentry"]
        PostHogSvc["PostHog"]
    end

    iOS --> APIInstances
    Browser --> CDN --> WebHostCustomer
    Browser --> CDN --> WebHostAdmin
    WebHostCustomer --> APIInstances
    WebHostAdmin --> APIInstances

    iOS -.-> SupaAuth
    WebHostCustomer -.-> SupaAuth
    WebHostAdmin -.-> SupaAuth

    APIInstances --> PG
    APIInstances --> RedisHost
    APIInstances --> SupaStorage
    APIInstances --> PaymentSvc
    WorkerInstances --> RedisHost
    WorkerInstances --> PG
    WorkerInstances --> SupaStorage
    WorkerInstances --> FCMSvc
    WorkerInstances --> EmailSvc
    WorkerInstances --> AISvc

    APIInstances --> SentrySvc
    WorkerInstances --> SentrySvc
    WebHostCustomer --> SentrySvc
    WebHostAdmin --> SentrySvc
    iOS --> SentrySvc

    APIInstances --> PostHogSvc
    WebHostCustomer --> PostHogSvc
    iOS --> PostHogSvc
```

## 8. Data ownership boundaries

* **PostgreSQL (Supabase)** is the single system of record for users, designs, artist profiles, bookings, quotations, reviews, and messaging metadata.
* **Redis** holds no data that cannot be reconstructed from PostgreSQL — it is cache and queue only, never a durability boundary.
* **Supabase Storage** holds binary media (images, documents, attachments); PostgreSQL stores references (URLs/keys), not blobs.
* **Payment provider** is the system of record for raw payment instrument data; MehndiVerse stores only provider-issued references (charge IDs, status), never raw card data — see [security-baseline.md](security-baseline.md).

## 9. Related documents

* [product-requirements.md](product-requirements.md)
* [user-roles-and-permissions.md](user-roles-and-permissions.md)
* [feature-scope.md](feature-scope.md)
* [security-baseline.md](security-baseline.md)
* [decisions/0001-technology-stack.md](decisions/0001-technology-stack.md)
