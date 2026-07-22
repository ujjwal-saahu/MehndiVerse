"""Enum strategy for MehndiVerse.

Every "enum-like" column (status, type, role, ...) is stored as a plain
``VARCHAR`` with a ``CHECK`` constraint, NOT a native PostgreSQL ``ENUM``
type. Native PG enums are cheap to query but expensive to evolve: adding a
value is fine, but renaming or removing one requires rebuilding the type
(`ALTER TYPE ... RENAME VALUE` only exists for the add case, and some
alterations cannot run inside a transaction). A young, fast-moving product
schema changes status vocabularies often, so we optimize for migration
simplicity: a CHECK constraint is dropped and recreated with a one-line
migration, same as any other constraint change.

Each Python `Enum` below is the single source of truth for one column's
allowed values. `check_in()` turns an enum into the SQL fragment for a
`CheckConstraint`, so the database and the application can never drift.
"""

from enum import Enum, StrEnum


def check_in(column: str, enum_cls: type[Enum]) -> str:
    values = ", ".join(f"'{member.value}'" for member in enum_cls)
    return f"{column} IN ({values})"


# --- Users -------------------------------------------------------------


class UserRole(StrEnum):
    """Guest has no row. Premium Customer / Verified Artist are *statuses*,
    not roles — see docs/user-roles-and-permissions.md."""

    CUSTOMER = "customer"
    ARTIST = "artist"
    MODERATOR = "moderator"
    ADMINISTRATOR = "administrator"
    SUPER_ADMINISTRATOR = "super_administrator"


class UserStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"
    PENDING_DELETION = "pending_deletion"


class DevicePlatform(StrEnum):
    IOS = "ios"
    ANDROID = "android"
    WEB = "web"


class ProfileVisibility(StrEnum):
    PUBLIC = "public"
    PRIVATE = "private"


# --- Artists -------------------------------------------------------------


class ArtistVerificationStatus(StrEnum):
    """See docs/artist-verification.md#verification-lifecycle for the full
    state diagram. `DRAFT`/`SUBMITTED` split what the old `PENDING` value
    conflated: an artist can edit their application freely before it's ever
    been seen by staff (`draft`), but once submitted it's locked pending
    review (`submitted` / `under_review`)."""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    MORE_INFORMATION_REQUIRED = "more_information_required"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class DocumentType(StrEnum):
    ID_PROOF = "id_proof"
    BUSINESS_LICENSE = "business_license"
    PORTFOLIO_SAMPLE = "portfolio_sample"
    OTHER = "other"


class DocumentStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PricingType(StrEnum):
    FIXED = "fixed"
    RANGE = "range"
    CUSTOM_QUOTE = "custom_quote"


class BlockedDateType(StrEnum):
    """Categorizes an `ArtistBlockedDate` row for calendar-view display —
    all four share one table/schema (see
    docs/artist-scheduling.md#blocked-dates-holidays-and-personal-leave)."""

    HOLIDAY = "holiday"
    PERSONAL_LEAVE = "personal_leave"
    VACATION = "vacation"
    OTHER = "other"


# --- Designs / catalog -----------------------------------------------------


class DesignDifficulty(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class BodyPlacement(StrEnum):
    HAND = "hand"
    FOOT = "foot"
    ARM = "arm"
    BACK = "back"
    OTHER = "other"


class DesignStatus(StrEnum):
    """Publishing status AND moderation state share one column: a `flagged`
    design is implicitly unpublished. See docs/design-catalog.md#moderation-state."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    FLAGGED = "flagged"


class CategoryType(StrEnum):
    """The taxonomy "axis" a category belongs to — see
    docs/design-catalog.md#category-taxonomy. A single `categories` table
    holds all six axes rather than six separate tables, distinguished by this
    column, so `design_categories` stays a single many-to-many join."""

    STYLE = "style"
    OCCASION = "occasion"
    BODY_PART = "body_part"
    DIFFICULTY = "difficulty"
    DENSITY = "density"
    REGION = "region"


class DesignImageStatus(StrEnum):
    """See docs/design-catalog.md#image-upload-pipeline for the full
    pending -> processing -> ready|failed lifecycle."""

    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


# --- Bookings ----------------------------------------------------------


class BookingStatus(StrEnum):
    """See docs/booking-lifecycle.md#1-states for what each status means and
    docs/booking-lifecycle.md#2-transition-table for the full state diagram
    this phase's `BOOKING_STATUS_TRANSITIONS` implements."""

    DRAFT = "draft"
    REQUESTED = "requested"
    ARTIST_REVIEWING = "artist_reviewing"
    QUOTATION_SENT = "quotation_sent"
    CUSTOMER_REVIEWING = "customer_reviewing"
    CONFIRMED = "confirmed"
    DEPOSIT_PENDING = "deposit_pending"
    DEPOSIT_PAID = "deposit_paid"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    REFUND_REQUESTED = "refund_requested"
    REFUNDED = "refunded"
    DISPUTED = "disputed"


class BookingEventType(StrEnum):
    WEDDING = "wedding"
    ENGAGEMENT = "engagement"
    FESTIVAL = "festival"
    BABY_SHOWER = "baby_shower"
    PARTY = "party"
    CORPORATE_EVENT = "corporate_event"
    OTHER = "other"


class BookingLocationType(StrEnum):
    CUSTOMER_LOCATION = "customer_location"
    ARTIST_STUDIO = "artist_studio"
    OTHER = "other"


class QuoteStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"


class AttachmentFileType(StrEnum):
    IMAGE = "image"
    DOCUMENT = "document"
    OTHER = "other"


# --- Messaging -----------------------------------------------------------


class ConversationType(StrEnum):
    BOOKING = "booking"
    INQUIRY = "inquiry"
    SUPPORT = "support"


class ConversationMemberRole(StrEnum):
    CUSTOMER = "customer"
    ARTIST = "artist"
    MODERATOR = "moderator"
    ADMIN = "admin"


class MessageType(StrEnum):
    TEXT = "text"
    IMAGE = "image"
    SYSTEM = "system"


# --- Payments ------------------------------------------------------------


class PaymentStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class PaymentType(StrEnum):
    DEPOSIT = "deposit"
    BALANCE = "balance"
    FULL = "full"
    SUBSCRIPTION = "subscription"


class RefundStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    PROCESSED = "processed"
    REJECTED = "rejected"


class PayoutStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    PAID = "paid"
    FAILED = "failed"


# --- Subscriptions -------------------------------------------------------


class SubscriptionTargetRole(StrEnum):
    CUSTOMER = "customer"
    ARTIST = "artist"


class BillingInterval(StrEnum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PAST_DUE = "past_due"
    TRIALING = "trialing"


class UsageType(StrEnum):
    DESIGN_DOWNLOAD = "design_download"
    AI_GENERATION = "ai_generation"


# --- Notifications ---------------------------------------------------------


class NotificationType(StrEnum):
    BOOKING_UPDATE = "booking_update"
    MESSAGE = "message"
    VERIFICATION = "verification"
    PAYMENT = "payment"
    SYSTEM = "system"
    MARKETING = "marketing"


class NotificationChannel(StrEnum):
    PUSH = "push"
    EMAIL = "email"
    SMS = "sms"
    IN_APP = "in_app"


# --- Moderation ------------------------------------------------------------


class ReportEntityType(StrEnum):
    """No DB foreign key backs (entity_type, entity_id) — see reports table
    docs in docs/database-relationships.md for why this is an intentional
    polymorphic reference validated at the application layer."""

    DESIGN = "design"
    COMMENT = "comment"
    MESSAGE = "message"
    USER = "user"
    ARTIST_PROFILE = "artist_profile"
    REVIEW = "review"


class ReportStatus(StrEnum):
    PENDING = "pending"
    REVIEWING = "reviewing"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


# --- Marketing -----------------------------------------------------------


class CouponDiscountType(StrEnum):
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"


# --- AI --------------------------------------------------------------------


class PreviewProjectStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AiGenerationType(StrEnum):
    DESIGN_DISCOVERY = "design_discovery"
    PHOTO_PREVIEW = "photo_preview"
    GENERATIVE_DESIGN = "generative_design"
    TAG_SUGGESTION = "tag_suggestion"
    EMBEDDING_GENERATION = "embedding_generation"
    DUPLICATE_DETECTION = "duplicate_detection"
    MODERATION_CHECK = "moderation_check"


class AiGenerationStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AiReviewStatus(StrEnum):
    """Whether an `AiGeneration`'s *outcome* (not its job status) needs a
    human to look at it — see docs/ai-foundation.md#human-review. Orthogonal
    to `AiGenerationStatus`: a moderation check can be `completed` as a job
    while its result is `pending` human review."""

    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AiJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TagSuggestionStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class DuplicateMatchStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"


class PatternDensity(StrEnum):
    """One field of the Phase 21 personalized-design structured form — see
    docs/ai-design-assistant.md#structured-form. Deliberately a small fixed
    vocabulary (unlike `style`/`occasion`-adjacent free-text fields) since a
    generative prompt benefits from a controlled density descriptor."""

    LIGHT = "light"
    MEDIUM = "medium"
    BOLD = "bold"
    INTRICATE = "intricate"


# --- Analytics ---------------------------------------------------------------


class AnalyticsEventType(StrEnum):
    """See docs/analytics-and-recommendations.md#privacy-safe-analytics-
    event-schema. `search_performed`/`filter_applied` are deliberately
    absent here: they're already tracked by the pre-existing `SearchEvent`
    table (`app/db/models/search.py`, Phase 8/9's search-history/analytics
    foundation) — every search request logs its query and the exact filter
    state that produced it, so a second, parallel event stream for the same
    action would just be duplicate bookkeeping. See docs/analytics-and-
    recommendations.md#search-analytics for how `SearchEvent` is read for
    reporting instead.

    This is also the direct successor to Phase 20's `RecommendationEvent`
    (`view`/`like`/`save`/`search_click`/`booking_request`) — that table was
    explicitly scoped as collection-only, with no consumer yet ("nothing
    reads this table yet" — its own docstring). This phase is the first to
    actually compute anything from collected events, and needed a schema
    broad enough to cover product analytics generally, not just
    recommendation inputs — so `AnalyticsEvent` replaces it outright rather
    than running two overlapping event logs side by side.
    """

    APP_OPENED = "app_opened"
    REGISTRATION_COMPLETED = "registration_completed"
    DESIGN_VIEWED = "design_viewed"
    DESIGN_LIKED = "design_liked"
    DESIGN_SAVED = "design_saved"
    ARTIST_VIEWED = "artist_viewed"
    BOOKING_STARTED = "booking_started"
    BOOKING_SUBMITTED = "booking_submitted"
    QUOTE_ACCEPTED = "quote_accepted"
    PAYMENT_COMPLETED = "payment_completed"
    SUBSCRIPTION_STARTED = "subscription_started"
    AI_GENERATION_REQUESTED = "ai_generation_requested"
    PREVIEW_CREATED = "preview_created"
    DESIGN_SHARED = "design_shared"


# --- Booking status transition rules ----------------------------------------
#
# Source of truth for docs/booking-lifecycle.md. Keys are the "from" status;
# values are the set of statuses that may follow. The initial transition
# (None -> DRAFT) is represented by the None key. Enforced by
# app/services/booking.py::transition_booking() — every write to
# `bookings.status` goes through that one function, which validates the hop
# against this table and records a `booking_status_history` row.

BOOKING_STATUS_TRANSITIONS: dict[BookingStatus | None, frozenset[BookingStatus]] = {
    None: frozenset({BookingStatus.DRAFT}),
    BookingStatus.DRAFT: frozenset({BookingStatus.REQUESTED, BookingStatus.CANCELLED}),
    BookingStatus.REQUESTED: frozenset(
        {
            BookingStatus.ARTIST_REVIEWING,
            BookingStatus.QUOTATION_SENT,
            BookingStatus.REJECTED,
            BookingStatus.CANCELLED,
        }
    ),
    BookingStatus.ARTIST_REVIEWING: frozenset(
        {BookingStatus.QUOTATION_SENT, BookingStatus.REJECTED, BookingStatus.CANCELLED}
    ),
    BookingStatus.QUOTATION_SENT: frozenset(
        {
            BookingStatus.CUSTOMER_REVIEWING,
            BookingStatus.CONFIRMED,
            BookingStatus.DEPOSIT_PENDING,
            BookingStatus.REJECTED,
            BookingStatus.CANCELLED,
        }
    ),
    BookingStatus.CUSTOMER_REVIEWING: frozenset(
        {
            BookingStatus.CONFIRMED,
            BookingStatus.DEPOSIT_PENDING,
            BookingStatus.REJECTED,
            BookingStatus.CANCELLED,
        }
    ),
    BookingStatus.CONFIRMED: frozenset(
        {
            BookingStatus.DEPOSIT_PENDING,
            BookingStatus.IN_PROGRESS,
            BookingStatus.CANCELLED,
            BookingStatus.DISPUTED,
        }
    ),
    BookingStatus.DEPOSIT_PENDING: frozenset(
        {BookingStatus.DEPOSIT_PAID, BookingStatus.CANCELLED, BookingStatus.DISPUTED}
    ),
    BookingStatus.DEPOSIT_PAID: frozenset(
        {BookingStatus.IN_PROGRESS, BookingStatus.CANCELLED, BookingStatus.DISPUTED}
    ),
    BookingStatus.IN_PROGRESS: frozenset(
        {BookingStatus.COMPLETED, BookingStatus.CANCELLED, BookingStatus.DISPUTED}
    ),
    BookingStatus.COMPLETED: frozenset({BookingStatus.REFUND_REQUESTED}),
    BookingStatus.CANCELLED: frozenset(),
    BookingStatus.REJECTED: frozenset(),
    BookingStatus.REFUND_REQUESTED: frozenset({BookingStatus.REFUNDED, BookingStatus.COMPLETED}),
    BookingStatus.REFUNDED: frozenset(),
    BookingStatus.DISPUTED: frozenset(
        {BookingStatus.COMPLETED, BookingStatus.CANCELLED, BookingStatus.REFUNDED}
    ),
}

TERMINAL_BOOKING_STATUSES: frozenset[BookingStatus] = frozenset(
    status
    for status, next_states in BOOKING_STATUS_TRANSITIONS.items()
    if status is not None and not next_states
)

# Statuses that "occupy" the artist's calendar for overlap-prevention
# purposes (see docs/booking-lifecycle.md#6-preventing-overlapping-confirmed-bookings
# and docs/artist-scheduling.md#available-slot-calculation). A booking still
# under negotiation (draft/requested/*_reviewing/quotation_sent) does not
# block other customers from requesting the same slot — only once a
# customer has actually accepted a quote (confirmed or later) is the slot
# considered taken.
BOOKING_OCCUPYING_STATUSES: frozenset[BookingStatus] = frozenset(
    {
        BookingStatus.CONFIRMED,
        BookingStatus.DEPOSIT_PENDING,
        BookingStatus.DEPOSIT_PAID,
        BookingStatus.IN_PROGRESS,
        BookingStatus.COMPLETED,
        BookingStatus.DISPUTED,
        BookingStatus.REFUND_REQUESTED,
        BookingStatus.REFUNDED,
    }
)

# String-valued mirror of the above for direct use in SQLAlchemy `.in_()`
# filters (column values are plain strings, not the enum type).
BOOKING_OCCUPYING_STATUS_VALUES: frozenset[str] = frozenset(
    s.value for s in BOOKING_OCCUPYING_STATUSES
)


def is_valid_booking_transition(
    from_status: BookingStatus | None, to_status: BookingStatus
) -> bool:
    """Pure validation of the state machine — see docs/booking-lifecycle.md."""
    return to_status in BOOKING_STATUS_TRANSITIONS.get(from_status, frozenset())


# --- Design status transition rules -----------------------------------------
#
# See docs/design-catalog.md#publishing-lifecycle. Owners may only toggle
# between draft and published themselves (enforced in
# app/api/routes/designs.py); archiving is a separate, one-way action
# (POST /designs/{id}/archive); `flagged` is staff-only moderation and is
# never reachable through the owner-facing update endpoint at all.

DESIGN_OWNER_STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    DesignStatus.DRAFT.value: frozenset({DesignStatus.PUBLISHED.value}),
    DesignStatus.PUBLISHED.value: frozenset({DesignStatus.DRAFT.value}),
}

DESIGN_ARCHIVABLE_STATUSES: frozenset[str] = frozenset(
    {DesignStatus.DRAFT.value, DesignStatus.PUBLISHED.value}
)


def is_valid_owner_design_transition(from_status: str, to_status: str) -> bool:
    """Pure validation of the owner-facing draft<->published toggle."""
    return to_status in DESIGN_OWNER_STATUS_TRANSITIONS.get(from_status, frozenset())


# --- Artist verification status transition rules ----------------------------
#
# See docs/artist-verification.md#verification-lifecycle. Two disjoint sets
# of transitions, enforced by different endpoints/roles:
# `ARTIST_VERIFICATION_SELF_TRANSITIONS` (the artist submitting/resubmitting
# their own application) and `ARTIST_VERIFICATION_STAFF_TRANSITIONS` (an
# admin/super_admin reviewing it — never the artist themselves, see
# docs/artist-verification.md#preventing-self-approval).

ARTIST_VERIFICATION_SELF_TRANSITIONS: dict[str, frozenset[str]] = {
    ArtistVerificationStatus.DRAFT.value: frozenset({ArtistVerificationStatus.SUBMITTED.value}),
    ArtistVerificationStatus.REJECTED.value: frozenset({ArtistVerificationStatus.SUBMITTED.value}),
    ArtistVerificationStatus.MORE_INFORMATION_REQUIRED.value: frozenset(
        {ArtistVerificationStatus.SUBMITTED.value}
    ),
}

ARTIST_VERIFICATION_STAFF_TRANSITIONS: dict[str, frozenset[str]] = {
    ArtistVerificationStatus.SUBMITTED.value: frozenset(
        {ArtistVerificationStatus.UNDER_REVIEW.value}
    ),
    ArtistVerificationStatus.UNDER_REVIEW.value: frozenset(
        {
            ArtistVerificationStatus.APPROVED.value,
            ArtistVerificationStatus.REJECTED.value,
            ArtistVerificationStatus.MORE_INFORMATION_REQUIRED.value,
        }
    ),
    ArtistVerificationStatus.APPROVED.value: frozenset({ArtistVerificationStatus.SUSPENDED.value}),
    ArtistVerificationStatus.SUSPENDED.value: frozenset({ArtistVerificationStatus.APPROVED.value}),
}

# Editing onboarding fields (profile data + documents) is only allowed while
# the application isn't locked pending a staff decision.
ARTIST_PROFILE_EDITABLE_STATUSES: frozenset[str] = frozenset(
    {
        ArtistVerificationStatus.DRAFT.value,
        ArtistVerificationStatus.REJECTED.value,
        ArtistVerificationStatus.MORE_INFORMATION_REQUIRED.value,
    }
)


def is_valid_artist_self_transition(from_status: str, to_status: str) -> bool:
    return to_status in ARTIST_VERIFICATION_SELF_TRANSITIONS.get(from_status, frozenset())


def is_valid_artist_staff_transition(from_status: str, to_status: str) -> bool:
    return to_status in ARTIST_VERIFICATION_STAFF_TRANSITIONS.get(from_status, frozenset())


# --- Legal, privacy, and support (Phase 29) ---------------------------------


class ConsentType(StrEnum):
    """See docs/legal-and-support.md#consent-records. `TERMS_OF_SERVICE`/
    `PRIVACY_POLICY` are recorded once at registration (app/api/routes/
    auth.py::register calls app/services/legal.py::record_consent()
    directly — the same function `POST /legal/consent` uses, just not
    through that HTTP route). `COOKIES_ANALYTICS` is a recognized value for
    that same general-purpose ledger but is **not** currently emitted by
    anything —
    the cookie-consent banner instead sets `UserPreference.analytics_consent`
    directly via the existing `PATCH /users/me/preferences` (Phase 22),
    since that's the actual flag `record_event()` checks. See
    docs/legal-and-support.md#consent-records for why these two consent
    types are wired differently."""

    TERMS_OF_SERVICE = "terms_of_service"
    PRIVACY_POLICY = "privacy_policy"
    COOKIES_ANALYTICS = "cookies_analytics"


class SupportRequestCategory(StrEnum):
    BUG_REPORT = "bug_report"
    ACCOUNT_ISSUE = "account_issue"
    BILLING_ISSUE = "billing_issue"
    ARTIST_ISSUE = "artist_issue"
    OTHER = "other"


class SupportRequestStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
