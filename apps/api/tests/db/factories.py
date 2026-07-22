"""Minimal valid-row builders shared across database model tests."""

import uuid
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.db.enums import (
    AiGenerationStatus,
    AiGenerationType,
    AiJobStatus,
    AnalyticsEventType,
    ArtistVerificationStatus,
    BodyPlacement,
    BookingEventType,
    BookingLocationType,
    BookingStatus,
    CategoryType,
    ConversationMemberRole,
    ConversationType,
    DesignDifficulty,
    MessageType,
    NotificationChannel,
    NotificationType,
    PatternDensity,
    PaymentStatus,
    PaymentType,
    PayoutStatus,
    PricingType,
    QuoteStatus,
    RefundStatus,
    ReportEntityType,
    ReportStatus,
    UserRole,
)
from app.db.models.ai import (
    AiDesignRequest,
    AiGeneration,
    AiJob,
    DesignDuplicateMatch,
    DesignEmbedding,
    DesignTagSuggestion,
    PreviewProject,
)
from app.db.models.analytics import AnalyticsEvent
from app.db.models.artist import ArtistAvailability, ArtistBlockedDate, ArtistProfile, ArtistService
from app.db.models.booking import Booking, BookingQuote
from app.db.models.design import Category, Design
from app.db.models.engagement import Collection, Comment
from app.db.models.marketing import Coupon
from app.db.models.messaging import Conversation, ConversationMember, Message
from app.db.models.moderation import Report
from app.db.models.notification import Notification
from app.db.models.payment import ArtistEarning, Payment, PaymentWebhookEvent, Payout, Refund
from app.db.models.review import Review
from app.db.models.search import SearchEvent
from app.db.models.subscription import Subscription, SubscriptionPlan
from app.db.models.user import User, UserBlock, UserDevice, UserPreference


def make_user(
    session: Session, *, role: str = UserRole.CUSTOMER.value, email: str | None = None
) -> User:
    user = User(email=email or f"{uuid.uuid4()}@example.com", role=role)
    session.add(user)
    session.flush()
    return user


def make_artist_profile(session: Session, *, user: User | None = None) -> ArtistProfile:
    artist_user = user or make_user(session, role=UserRole.ARTIST.value)
    profile = ArtistProfile(
        user_id=artist_user.id,
        verification_status=ArtistVerificationStatus.APPROVED.value,
    )
    session.add(profile)
    session.flush()
    return profile


def make_category(
    session: Session, *, name: str | None = None, category_type: str = CategoryType.STYLE.value
) -> Category:
    unique = uuid.uuid4().hex[:8]
    category = Category(
        name=name or f"Category {unique}", slug=f"category-{unique}", category_type=category_type
    )
    session.add(category)
    session.flush()
    return category


def make_design(
    session: Session, *, artist_profile: ArtistProfile | None = None, status: str | None = None
) -> Design:
    design = Design(
        artist_profile_id=artist_profile.id if artist_profile else None,
        title="Sample Design",
        **({"status": status} if status is not None else {}),
    )
    session.add(design)
    session.flush()
    return design


def make_collection(
    session: Session,
    *,
    user: User | None = None,
    name: str | None = None,
    is_private: bool = True,
    is_default: bool = False,
) -> Collection:
    unique = uuid.uuid4().hex[:8]
    collection = Collection(
        user_id=(user or make_user(session)).id,
        name=name or f"Collection {unique}",
        is_private=is_private,
        is_default=is_default,
    )
    session.add(collection)
    session.flush()
    return collection


def make_booking(
    session: Session,
    *,
    customer: User | None = None,
    artist_profile: ArtistProfile | None = None,
    status: str = BookingStatus.REQUESTED.value,
    requested_date: date | None = None,
    requested_time: time | None = None,
    service_id: uuid.UUID | None = None,
    location_type: str | None = BookingLocationType.ARTIST_STUDIO.value,
    contact_name: str | None = "Test Customer",
    contact_email: str | None = "customer@example.com",
    contact_phone: str | None = "+911234567890",
    deposit_amount: float | None = None,
    total_amount: float | None = None,
) -> Booking:
    booking = Booking(
        customer_id=(customer or make_user(session)).id,
        artist_profile_id=(artist_profile or make_artist_profile(session)).id,
        status=status,
        requested_date=requested_date if requested_date is not None else date.today(),
        requested_time=requested_time,
        service_id=service_id,
        location_type=location_type,
        contact_name=contact_name,
        contact_email=contact_email,
        contact_phone=contact_phone,
        deposit_amount=deposit_amount,
        total_amount=total_amount,
        currency="INR",
    )
    session.add(booking)
    session.flush()
    return booking


def make_booking_quote(
    session: Session,
    *,
    booking: Booking,
    amount: float = 5000,
    currency: str = "INR",
    status: str = QuoteStatus.PENDING.value,
    valid_until: datetime | None = None,
) -> BookingQuote:
    quote = BookingQuote(
        booking_id=booking.id,
        amount=amount,
        currency=currency,
        status=status,
        valid_until=valid_until,
    )
    session.add(quote)
    session.flush()
    return quote


def make_artist_service(
    session: Session,
    *,
    artist_profile: ArtistProfile | None = None,
    name: str | None = None,
    duration_minutes: int | None = 60,
    buffer_minutes: int | None = None,
    travel_buffer_minutes: int | None = None,
    is_active: bool = True,
    deposit_required: bool = False,
    deposit_amount: float | None = None,
) -> ArtistService:
    unique = uuid.uuid4().hex[:8]
    service = ArtistService(
        artist_profile_id=(artist_profile or make_artist_profile(session)).id,
        name=name or f"Service {unique}",
        pricing_type=PricingType.FIXED.value,
        price_amount=1000,
        currency="INR",
        deposit_required=deposit_required,
        deposit_amount=deposit_amount,
        duration_minutes=duration_minutes,
        buffer_minutes=buffer_minutes,
        travel_buffer_minutes=travel_buffer_minutes,
        is_active=is_active,
    )
    session.add(service)
    session.flush()
    return service


def make_availability_rule(
    session: Session,
    *,
    artist_profile: ArtistProfile | None = None,
    day_of_week: int = 1,
    start_time: time = time(9, 0),
    end_time: time = time(17, 0),
    is_active: bool = True,
) -> ArtistAvailability:
    rule = ArtistAvailability(
        artist_profile_id=(artist_profile or make_artist_profile(session)).id,
        day_of_week=day_of_week,
        start_time=start_time,
        end_time=end_time,
        is_active=is_active,
    )
    session.add(rule)
    session.flush()
    return rule


def make_blocked_date(
    session: Session,
    *,
    artist_profile: ArtistProfile | None = None,
    start_date: date,
    end_date: date | None = None,
    block_type: str = "other",
    start_time: time | None = None,
    end_time: time | None = None,
    reason: str | None = None,
) -> ArtistBlockedDate:
    block = ArtistBlockedDate(
        artist_profile_id=(artist_profile or make_artist_profile(session)).id,
        start_date=start_date,
        end_date=end_date or start_date,
        block_type=block_type,
        start_time=start_time,
        end_time=end_time,
        reason=reason,
    )
    session.add(block)
    session.flush()
    return block


def utc_now() -> datetime:
    return datetime.now(UTC)


def future(hours: int) -> datetime:
    return utc_now() + timedelta(hours=hours)


def make_conversation(
    session: Session,
    *,
    booking: Booking,
) -> Conversation:
    """Direct row construction (bypassing
    app/services/messaging.py::get_or_create_booking_conversation) for tests
    that need a pre-existing conversation+members without exercising the
    lazy-creation code path itself."""
    artist_profile = session.get(ArtistProfile, booking.artist_profile_id)
    assert artist_profile is not None

    conversation = Conversation(booking_id=booking.id, type=ConversationType.BOOKING.value)
    session.add(conversation)
    session.flush()
    session.add_all(
        [
            ConversationMember(
                conversation_id=conversation.id,
                user_id=booking.customer_id,
                role=ConversationMemberRole.CUSTOMER.value,
            ),
            ConversationMember(
                conversation_id=conversation.id,
                user_id=artist_profile.user_id,
                role=ConversationMemberRole.ARTIST.value,
            ),
        ]
    )
    session.flush()
    return conversation


def make_message(
    session: Session,
    *,
    conversation: Conversation,
    sender: User,
    body: str | None = "Hello",
    attachment_url: str | None = None,
    message_type: str | None = None,
    created_at: datetime | None = None,
) -> Message:
    message = Message(
        conversation_id=conversation.id,
        sender_id=sender.id,
        body=body,
        attachment_url=attachment_url,
        message_type=message_type
        or (MessageType.IMAGE.value if attachment_url else MessageType.TEXT.value),
        **({"created_at": created_at} if created_at is not None else {}),
    )
    session.add(message)
    session.flush()
    return message


def make_notification(
    session: Session,
    *,
    user: User,
    notification_type: str = NotificationType.SYSTEM.value,
    channel: str = NotificationChannel.IN_APP.value,
    title: str = "Test notification",
    body: str = "Test body",
    is_read: bool = False,
) -> Notification:
    notification = Notification(
        user_id=user.id,
        type=notification_type,
        channel=channel,
        title=title,
        body=body,
        is_read=is_read,
    )
    session.add(notification)
    session.flush()
    return notification


def make_user_block(session: Session, *, blocker: User, blocked: User) -> UserBlock:
    block = UserBlock(blocker_id=blocker.id, blocked_id=blocked.id)
    session.add(block)
    session.flush()
    return block


def make_user_preference(
    session: Session,
    *,
    user: User,
    email_notifications: bool = True,
    push_notifications: bool = True,
    sms_notifications: bool = False,
    analytics_consent: bool = False,
) -> UserPreference:
    preference = UserPreference(
        user_id=user.id,
        email_notifications=email_notifications,
        push_notifications=push_notifications,
        sms_notifications=sms_notifications,
        analytics_consent=analytics_consent,
    )
    session.add(preference)
    session.flush()
    return preference


def make_search_event(
    session: Session,
    *,
    user: User | None = None,
    query: str | None = "bridal mehndi",
    filters: dict[str, object] | None = None,
    result_count: int = 5,
    created_at: datetime | None = None,
) -> SearchEvent:
    event = SearchEvent(
        user_id=(user or make_user(session)).id,
        query=query,
        filters=filters,
        result_count=result_count,
        **({"created_at": created_at} if created_at is not None else {}),
    )
    session.add(event)
    session.flush()
    return event


def make_consenting_user(session: Session, *, role: str = UserRole.CUSTOMER.value) -> User:
    """A user who has explicitly opted in to analytics — see
    docs/analytics-and-recommendations.md#provide-analytics-consent-where-
    legally-required. Most analytics/recommendation tests need this rather
    than a plain `make_user` (whose events would otherwise be recorded
    anonymized, since `UserPreference.analytics_consent` defaults `False`
    and a bare `make_user` doesn't create a preferences row at all)."""
    user = make_user(session, role=role)
    make_user_preference(session, user=user, analytics_consent=True)
    return user


def make_user_device(
    session: Session, *, user: User, device_token: str | None = None, is_active: bool = True
) -> UserDevice:
    device = UserDevice(
        user_id=user.id,
        device_token=device_token or f"device-{uuid.uuid4().hex[:12]}",
        platform="ios",
        is_active=is_active,
    )
    session.add(device)
    session.flush()
    return device


def make_payment(
    session: Session,
    *,
    booking: Booking | None = None,
    subscription: Subscription | None = None,
    payer: User | None = None,
    amount: int = 50000,
    currency: str = "INR",
    provider: str = "razorpay",
    provider_order_id: str | None = None,
    provider_payment_id: str | None = None,
    payment_type: str = PaymentType.DEPOSIT.value,
    status: str = PaymentStatus.PENDING.value,
    idempotency_key: str | None = None,
    commission_amount: int | None = None,
    net_amount: int | None = None,
    created_at: datetime | None = None,
) -> Payment:
    if subscription is None and booking is None:
        booking = make_booking(session)
    if payer is None:
        owner_id = booking.customer_id if booking is not None else subscription.user_id  # type: ignore[union-attr]
        payer = session.get(User, owner_id)
        assert payer is not None
    unique = uuid.uuid4().hex[:10]
    payment = Payment(
        booking_id=booking.id if booking is not None else None,
        subscription_id=subscription.id if subscription is not None else None,
        payer_id=payer.id,
        amount=amount,
        currency=currency,
        provider=provider,
        provider_order_id=provider_order_id or f"order_{unique}",
        provider_payment_id=provider_payment_id,
        payment_type=payment_type,
        status=status,
        idempotency_key=idempotency_key,
        commission_amount=commission_amount,
        net_amount=net_amount,
        **({"created_at": created_at} if created_at is not None else {}),
    )
    session.add(payment)
    session.flush()
    return payment


def make_refund(
    session: Session,
    *,
    payment: Payment,
    amount: int | None = None,
    status: str = RefundStatus.PENDING.value,
    reason: str | None = None,
    provider_refund_id: str | None = None,
    processed_by: User | None = None,
    processed_at: datetime | None = None,
) -> Refund:
    refund = Refund(
        payment_id=payment.id,
        amount=amount if amount is not None else payment.amount,
        currency=payment.currency,
        reason=reason,
        status=status,
        provider_refund_id=provider_refund_id,
        processed_by=processed_by.id if processed_by is not None else None,
        requested_at=utc_now(),
        processed_at=processed_at,
    )
    session.add(refund)
    session.flush()
    return refund


def make_artist_earning(
    session: Session,
    *,
    payment: Payment,
    artist_profile: ArtistProfile,
    gross_amount: int | None = None,
    commission_amount: int = 0,
    net_amount: int | None = None,
) -> ArtistEarning:
    gross = gross_amount if gross_amount is not None else payment.amount
    net = net_amount if net_amount is not None else gross - commission_amount
    earning = ArtistEarning(
        artist_profile_id=artist_profile.id,
        booking_id=payment.booking_id,
        payment_id=payment.id,
        gross_amount=gross,
        commission_amount=commission_amount,
        net_amount=net,
        currency=payment.currency,
    )
    session.add(earning)
    session.flush()
    return earning


def make_payout(
    session: Session,
    *,
    artist_profile: ArtistProfile,
    amount: int = 10000,
    currency: str = "INR",
    status: str = PayoutStatus.PENDING.value,
) -> Payout:
    payout = Payout(
        artist_profile_id=artist_profile.id,
        amount=amount,
        currency=currency,
        status=status,
        requested_at=utc_now(),
    )
    session.add(payout)
    session.flush()
    return payout


def make_comment(
    session: Session,
    *,
    design: Design,
    user: User | None = None,
    body: str = "Lovely work!",
    parent_comment_id: uuid.UUID | None = None,
    deleted_at: datetime | None = None,
) -> Comment:
    comment = Comment(
        design_id=design.id,
        user_id=(user or make_user(session)).id,
        parent_comment_id=parent_comment_id,
        body=body,
        deleted_at=deleted_at,
    )
    session.add(comment)
    session.flush()
    return comment


def make_review(
    session: Session,
    *,
    booking: Booking,
    rating: int = 5,
    body: str | None = "Great experience.",
) -> Review:
    review = Review(
        booking_id=booking.id,
        customer_id=booking.customer_id,
        artist_profile_id=booking.artist_profile_id,
        rating=rating,
        body=body,
    )
    session.add(review)
    session.flush()
    return review


def make_report(
    session: Session,
    *,
    reporter: User,
    entity_type: str = ReportEntityType.DESIGN.value,
    entity_id: uuid.UUID,
    reason: str = "This is inappropriate.",
    status: str = ReportStatus.PENDING.value,
) -> Report:
    report = Report(
        reporter_id=reporter.id,
        reported_entity_type=entity_type,
        reported_entity_id=entity_id,
        reason=reason,
        status=status,
    )
    session.add(report)
    session.flush()
    return report


def make_webhook_event(
    session: Session,
    *,
    provider: str = "razorpay",
    event_type: str = "payment.captured",
    provider_reference: str,
    payload: dict[str, object] | None = None,
) -> PaymentWebhookEvent:
    event = PaymentWebhookEvent(
        provider=provider,
        event_type=event_type,
        provider_reference=provider_reference,
        payload=payload or {},
    )
    session.add(event)
    session.flush()
    return event


def make_subscription_plan(
    session: Session,
    *,
    target_role: str = "customer",
    billing_interval: str = "monthly",
    price_amount: float = 199.0,
    currency: str = "INR",
    features: dict[str, object] | None = None,
    is_active: bool = True,
    name: str | None = None,
) -> SubscriptionPlan:
    unique = uuid.uuid4().hex[:8]
    plan = SubscriptionPlan(
        name=name or f"Plan {unique}",
        slug=f"plan-{unique}",
        target_role=target_role,
        price_amount=price_amount,
        currency=currency,
        billing_interval=billing_interval,
        features=features if features is not None else {},
        is_active=is_active,
    )
    session.add(plan)
    session.flush()
    return plan


def make_subscription(
    session: Session,
    *,
    user: User | None = None,
    plan: SubscriptionPlan | None = None,
    status: str = "active",
    current_period_start: datetime | None = None,
    current_period_end: datetime | None = None,
    cancel_at_period_end: bool = False,
    grace_period_ends_at: datetime | None = None,
) -> Subscription:
    now = utc_now()
    subscription = Subscription(
        user_id=(user or make_user(session)).id,
        plan_id=(plan or make_subscription_plan(session)).id,
        status=status,
        current_period_start=current_period_start or now,
        current_period_end=current_period_end or (now + timedelta(days=30)),
        cancel_at_period_end=cancel_at_period_end,
        grace_period_ends_at=grace_period_ends_at,
        started_at=now,
    )
    session.add(subscription)
    session.flush()
    return subscription


def make_preview_project(
    session: Session,
    *,
    user: User | None = None,
    design: Design | None = None,
    source_storage_path: str | None = None,
    result_storage_path: str | None = None,
    overlay_transform: dict[str, object] | None = None,
    status: str = "completed",
    shared_with_booking_id: uuid.UUID | None = None,
) -> PreviewProject:
    unique = uuid.uuid4().hex[:10]
    preview = PreviewProject(
        user_id=(user or make_user(session)).id,
        design_id=design.id if design else None,
        source_storage_path=source_storage_path or f"user/{unique}/source.jpg",
        result_storage_path=result_storage_path,
        source_width=800,
        source_height=600,
        overlay_transform=overlay_transform,
        status=status,
        shared_with_booking_id=shared_with_booking_id,
    )
    session.add(preview)
    session.flush()
    return preview


def make_coupon(
    session: Session,
    *,
    code: str | None = None,
    discount_type: str = "percentage",
    discount_value: float = 10.0,
    max_redemptions: int | None = None,
    redemption_count: int = 0,
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
    is_active: bool = True,
    created_by: User | None = None,
) -> Coupon:
    coupon = Coupon(
        code=code or f"CODE{uuid.uuid4().hex[:8].upper()}",
        discount_type=discount_type,
        discount_value=discount_value,
        max_redemptions=max_redemptions,
        redemption_count=redemption_count,
        valid_from=valid_from or (utc_now() - timedelta(days=1)),
        valid_until=valid_until,
        is_active=is_active,
        created_by=(created_by or make_user(session)).id,
    )
    session.add(coupon)
    session.flush()
    return coupon


def make_ai_generation(
    session: Session,
    *,
    user: User | None = None,
    generation_type: str = AiGenerationType.EMBEDDING_GENERATION.value,
    entity_type: str | None = "design",
    entity_id: uuid.UUID | None = None,
    status: str = AiGenerationStatus.PENDING.value,
    request_payload: dict[str, object] | None = None,
) -> AiGeneration:
    generation = AiGeneration(
        user_id=(user or make_user(session)).id,
        generation_type=generation_type,
        entity_type=entity_type,
        entity_id=entity_id,
        status=status,
        request_payload=request_payload if request_payload is not None else {},
    )
    session.add(generation)
    session.flush()
    return generation


def make_ai_job(
    session: Session,
    *,
    generation: AiGeneration | None = None,
    job_type: str = "embedding_generation",
    payload: dict[str, object] | None = None,
    status: str = AiJobStatus.PENDING.value,
    attempt_count: int = 0,
    max_attempts: int = 3,
    next_run_at: datetime | None = None,
    started_at: datetime | None = None,
) -> AiJob:
    resolved_generation = generation or make_ai_generation(session)
    job = AiJob(
        generation_id=resolved_generation.id,
        job_type=job_type,
        payload=payload if payload is not None else {"design_id": str(uuid.uuid4())},
        status=status,
        attempt_count=attempt_count,
        max_attempts=max_attempts,
        started_at=started_at,
        **({"next_run_at": next_run_at} if next_run_at is not None else {}),
    )
    session.add(job)
    session.flush()
    return job


def make_design_embedding(
    session: Session,
    *,
    design: Design,
    embedding: list[float] | None = None,
    provider: str = "local",
    model_name: str = "local-heuristic-v1",
) -> DesignEmbedding:
    vector = embedding if embedding is not None else [0.5] * 8
    row = DesignEmbedding(
        design_id=design.id,
        embedding=vector,
        dimension=len(vector),
        provider=provider,
        model_name=model_name,
    )
    session.add(row)
    session.flush()
    return row


def make_tag_suggestion(
    session: Session,
    *,
    design: Design,
    tag_name: str = "bold",
    confidence: float = 0.8,
    status: str = "pending",
) -> DesignTagSuggestion:
    suggestion = DesignTagSuggestion(
        design_id=design.id, tag_name=tag_name, confidence=confidence, status=status
    )
    session.add(suggestion)
    session.flush()
    return suggestion


def make_duplicate_match(
    session: Session,
    *,
    design: Design,
    matched_design: Design,
    similarity: float = 0.99,
    status: str = "pending",
) -> DesignDuplicateMatch:
    match = DesignDuplicateMatch(
        design_id=design.id,
        matched_design_id=matched_design.id,
        similarity=similarity,
        status=status,
    )
    session.add(match)
    session.flush()
    return match


def make_ai_design_request(
    session: Session,
    *,
    user: User | None = None,
    status: str = AiGenerationStatus.PENDING.value,
    style: str = "Arabic",
    occasion: str = BookingEventType.WEDDING.value,
    body_placement: str = BodyPlacement.HAND.value,
    difficulty_level: str = DesignDifficulty.INTERMEDIATE.value,
    density: str = PatternDensity.MEDIUM.value,
    is_symmetric: bool = True,
    pattern_elements: list[str] | None = None,
    theme: str | None = None,
    personalization_text: str | None = None,
    additional_instructions: str | None = None,
    allow_provider_training: bool = False,
    retry_count: int = 0,
    max_retries: int = 3,
    result_storage_path: str | None = None,
    requires_human_review: bool = False,
    review_status: str = "not_required",
) -> AiDesignRequest:
    owner = user or make_user(session)
    generation = AiGeneration(
        user_id=owner.id,
        generation_type=AiGenerationType.GENERATIVE_DESIGN.value,
        status=status,
        request_payload={"style": style},
        requires_human_review=requires_human_review,
        review_status=review_status,
    )
    session.add(generation)
    session.flush()

    request = AiDesignRequest(
        user_id=owner.id,
        generation_id=generation.id,
        style=style,
        occasion=occasion,
        body_placement=body_placement,
        difficulty_level=difficulty_level,
        density=density,
        is_symmetric=is_symmetric,
        pattern_elements=pattern_elements if pattern_elements is not None else [],
        theme=theme,
        personalization_text=personalization_text,
        additional_instructions=additional_instructions,
        allow_provider_training=allow_provider_training,
        prompt=f"A {density} {style} mehndi design for a {occasion}.",
        result_storage_path=result_storage_path,
        retry_count=retry_count,
        max_retries=max_retries,
    )
    session.add(request)
    session.flush()
    return request


def make_analytics_event(
    session: Session,
    *,
    event_type: str = AnalyticsEventType.DESIGN_VIEWED.value,
    user: User | None = None,
    session_id: str | None = None,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    properties: dict[str, object] | None = None,
    created_at: datetime | None = None,
) -> AnalyticsEvent:
    event = AnalyticsEvent(
        event_type=event_type,
        user_id=user.id if user is not None else None,
        session_id=session_id,
        entity_type=entity_type,
        entity_id=entity_id,
        properties=properties,
        **({"created_at": created_at} if created_at is not None else {}),
    )
    session.add(event)
    session.flush()
    return event
