# MehndiVerse — Product Requirements Document

Status: Draft (Phase 0)
Last updated: 2026-07-14

## 1. Purpose

MehndiVerse is a marketplace and design-discovery platform connecting customers seeking mehndi (henna) designs and artist services with professional mehndi artists. The platform supports design discovery, artist portfolios, booking and quotation workflows, in-app communication, payments, reviews, and AI-assisted design discovery and preview.

This document defines the product requirements at a level independent of implementation phase. It is the source of truth for scope; [feature-scope.md](feature-scope.md) sequences these requirements into MVP / Post-MVP / Future delivery buckets.

## 2. Goals

* Let customers discover mehndi designs and artists quickly through browsing, search, and filtering.
* Let customers move from inspiration to a booked artist with minimal friction (design → artist → quote → deposit → booking).
* Give artists tools to present a professional portfolio, manage services/availability, and run their booking pipeline without needing external tools.
* Give administrators the controls needed to keep the marketplace trustworthy: artist verification, content moderation, payment oversight, dispute handling.
* Support the business with a premium subscription tier for customers and (post-MVP) monetizable visibility tools for artists.

## 3. Non-goals (for this document)

* Implementation details, file structure, or code — see [system-architecture.md](system-architecture.md).
* Exact UI/visual design — to be handled in a design phase, not architecture/planning.
* Pricing model specifics for subscriptions/commissions — flagged as a business decision to be made before Post-MVP payment phases, not defined here.

## 4. Personas

| Persona | Summary |
|---|---|
| Guest | Unauthenticated visitor browsing public content. |
| Customer | Registered user booking mehndi services. |
| Premium Customer | Customer on a paid subscription tier with enhanced discovery/booking features. |
| Artist | Registered mehndi professional, pending or without verification. |
| Verified Artist | Artist who has passed identity/quality verification and is fully visible in the marketplace. |
| Moderator | Staff responsible for content moderation and dispute triage. |
| Administrator | Staff responsible for user, artist, booking, payment, and catalog management. |
| Super Administrator | Highest-privilege staff role; manages other admins/moderators and system configuration. |

Full permission definitions live in [user-roles-and-permissions.md](user-roles-and-permissions.md).

## 5. Functional requirements by capability

### 5.1 Design discovery
* Browse a catalog of mehndi designs with images, tags, categories, and difficulty/style metadata.
* Search designs by keyword.
* Filter designs by category, style, occasion, body placement, and other taxonomy fields.
* View a design detail page including related artist(s) and similar designs.
* AI-assisted design discovery: natural-language or visual-similarity search over the design catalog.
* AI hand/foot photo preview: overlay a selected design onto a customer-supplied photo of a hand or foot.

### 5.2 Customer engagement
* Like designs.
* Save designs to personal collections.
* Create, rename, and delete collections.
* Follow artists and see followed-artist activity.
* Leave a review (rating + text) for a completed booking.

### 5.3 Artist presence
* Create and edit a professional profile (bio, location, contact preferences).
* Submit identity/professional verification documents for admin review.
* Upload and manage a portfolio of designs/work samples.
* Define services with pricing (fixed price, price range, or custom-quote-only).
* Set availability (working days/hours, blackout dates).
* View own performance: earnings, review history, booking history.

### 5.4 Booking lifecycle
* Customer submits a booking request to an artist (date, time, service, location details).
* Artist responds with a quotation (price, terms) or declines.
* Customer accepts a quotation and pays a deposit to confirm.
* Both parties can communicate via in-app messaging throughout.
* Booking status is tracked end-to-end (requested → quoted → confirmed → completed / cancelled). Full state machine in [system-architecture.md](system-architecture.md#booking-lifecycle).
* Customer leaves a review after a completed booking.

### 5.5 Payments
* Customer pays a booking deposit through an abstracted payment provider (provider-agnostic integration layer; no raw card data touches MehndiVerse servers).
* Artists can view payout/earnings status for completed bookings.
* Refunds are administrator-mediated, not self-service, at MVP.

### 5.6 Communication & notifications
* In-app messaging between customer and artist scoped to a booking or general inquiry.
* Push notifications (FCM) for booking status changes, new messages, and quotation events.
* Email notifications for account and booking lifecycle events.

### 5.7 Administration
* Manage user accounts (view, suspend, delete).
* Review and approve/reject artist verification submissions.
* Moderate design and portfolio content (approve/remove/flag).
* Manage design categories and taxonomy.
* Oversee bookings (view, intervene on disputes).
* Review payments, process/approve refunds.
* Handle reports and disputes raised by users.
* Manage customer/artist subscription plans (post-MVP monetization).
* View platform analytics (usage, conversion, GMV-equivalent booking value).
* Manage system configuration (feature flags, categories, notification templates).

## 6. Non-functional requirements

* **Security & privacy**: role-based authorization enforced server-side (never solely in UI or mobile client); verification documents and payment data handled per [security-baseline.md](security-baseline.md).
* **Availability**: backend and database designed for standard marketplace uptime expectations; no single-writer bottlenecks introduced without justification.
* **Performance**: design browse/search interactions should feel immediate (client-perceived, cached where reasonable via Redis).
* **Scalability**: background workers absorb non-interactive work (notification fan-out, image processing, AI inference calls) off the request path.
* **Observability**: errors captured via Sentry, product usage via PostHog, from MVP onward.
* **Portability**: payment and notification providers are abstracted behind internal interfaces so a provider can be swapped without touching business logic.
* **Data integrity**: booking, quotation, and payment state transitions are validated server-side and audit-logged for admin actions.

## 7. Open questions / decisions deferred

These are flagged, not resolved, in Phase 0:

* Exact commission/pricing model for the marketplace (per-booking fee vs. subscription-only monetization).
* Which payment provider(s) to integrate first (region-dependent).
* Which AI provider/model powers design discovery and photo preview.
* Legal/compliance requirements for storing verification documents (jurisdiction-dependent).

## 8. Related documents

* [user-roles-and-permissions.md](user-roles-and-permissions.md)
* [feature-scope.md](feature-scope.md)
* [system-architecture.md](system-architecture.md)
* [development-roadmap.md](development-roadmap.md)
* [security-baseline.md](security-baseline.md)
* [decisions/0001-technology-stack.md](decisions/0001-technology-stack.md)
