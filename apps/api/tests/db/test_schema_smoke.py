"""One minimal valid row per remaining table, proving the full 41-table schema
is wired correctly end to end (FKs resolve, CHECK constraints accept valid
data, JSONB columns round-trip). Domain-specific constraint/cascade behavior
is covered in the other test_*.py files in this package."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.ai import AiGeneration, PreviewProject
from app.db.models.artist import ArtistDocument
from app.db.models.booking import BookingAttachment, BookingQuote
from app.db.models.design import Category, DesignCategory, DesignImage, DesignTag, Tag
from app.db.models.engagement import Collection, CollectionItem, Comment, Follow
from app.db.models.marketing import Coupon, CouponRedemption
from app.db.models.messaging import Conversation, ConversationMember, Message
from app.db.models.moderation import Report
from app.db.models.notification import Notification
from app.db.models.payment import Payout
from app.db.models.review import Review
from app.db.models.subscription import Subscription, SubscriptionPlan
from app.db.models.system import AuditLog, SystemSetting
from app.db.models.user import UserDevice, UserPreference

from .factories import make_artist_profile, make_booking, make_design, make_user


def test_user_preference_and_device(db_session: Session) -> None:
    user = make_user(db_session)
    db_session.add(UserPreference(user_id=user.id))
    db_session.add(UserDevice(user_id=user.id, device_token="tok-123", platform="ios"))
    db_session.flush()


def test_artist_document(db_session: Session) -> None:
    artist_profile = make_artist_profile(db_session)
    doc = ArtistDocument(
        artist_profile_id=artist_profile.id,
        document_type="id_proof",
        storage_path=f"{artist_profile.user_id}/doc.pdf",
        content_type="application/pdf",
        file_size_bytes=1024,
        status="pending",
    )
    db_session.add(doc)
    db_session.flush()
    assert doc.id is not None


def test_catalog_taxonomy(db_session: Session) -> None:
    design = make_design(db_session)
    category = Category(name="Smoke Category", slug="smoke-category", category_type="style")
    tag = Tag(name="Smoke Tag", slug="smoke-tag")
    db_session.add_all([category, tag])
    db_session.flush()

    db_session.add(DesignImage(design_id=design.id, image_url="https://example.test/a.jpg"))
    db_session.add(DesignCategory(design_id=design.id, category_id=category.id))
    db_session.add(DesignTag(design_id=design.id, tag_id=tag.id))
    db_session.flush()


def test_comments_collections_follows(db_session: Session) -> None:
    user = make_user(db_session)
    design = make_design(db_session)
    artist_profile = make_artist_profile(db_session)

    db_session.add(Comment(design_id=design.id, user_id=user.id, body="Lovely work!"))
    collection = Collection(user_id=user.id, name="Smoke Collection")
    db_session.add(collection)
    db_session.flush()
    db_session.add(CollectionItem(collection_id=collection.id, design_id=design.id))
    db_session.add(Follow(follower_user_id=user.id, artist_profile_id=artist_profile.id))
    db_session.flush()


def test_booking_quote_and_attachment(db_session: Session) -> None:
    booking = make_booking(db_session)
    uploader = make_user(db_session)

    db_session.add(
        BookingQuote(booking_id=booking.id, amount=750, currency="INR", status="pending")
    )
    db_session.add(
        BookingAttachment(
            booking_id=booking.id,
            uploaded_by=uploader.id,
            file_url="https://example.test/ref.jpg",
            file_type="image",
        )
    )
    db_session.flush()


def test_conversation_and_message(db_session: Session) -> None:
    booking = make_booking(db_session)
    conversation = Conversation(booking_id=booking.id, type="booking")
    db_session.add(conversation)
    db_session.flush()

    db_session.add(
        ConversationMember(
            conversation_id=conversation.id, user_id=booking.customer_id, role="customer"
        )
    )
    db_session.add(
        Message(conversation_id=conversation.id, sender_id=booking.customer_id, body="Hello!")
    )
    db_session.flush()


def test_payout(db_session: Session) -> None:
    artist_profile = make_artist_profile(db_session)
    payout = Payout(
        artist_profile_id=artist_profile.id,
        amount=1000,
        currency="INR",
        status="pending",
        requested_at=datetime.now(UTC),
    )
    db_session.add(payout)
    db_session.flush()
    assert payout.id is not None


def test_subscription_plan_and_subscription(db_session: Session) -> None:
    user = make_user(db_session)
    plan = SubscriptionPlan(
        name="Smoke Plan",
        slug="smoke-plan",
        target_role="customer",
        price_amount=299,
        currency="INR",
        billing_interval="monthly",
    )
    db_session.add(plan)
    db_session.flush()

    now = datetime.now(UTC)
    db_session.add(
        Subscription(
            user_id=user.id,
            plan_id=plan.id,
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            started_at=now,
        )
    )
    db_session.flush()


def test_review(db_session: Session) -> None:
    booking = make_booking(db_session, status="completed")
    db_session.add(
        Review(
            booking_id=booking.id,
            customer_id=booking.customer_id,
            artist_profile_id=booking.artist_profile_id,
            rating=5,
            body="Beautiful work!",
        )
    )
    db_session.flush()


def test_notification(db_session: Session) -> None:
    user = make_user(db_session)
    db_session.add(
        Notification(
            user_id=user.id,
            type="booking_update",
            channel="push",
            title="Booking confirmed",
            body="Your booking has been confirmed.",
        )
    )
    db_session.flush()


def test_report(db_session: Session) -> None:
    reporter = make_user(db_session)
    design = make_design(db_session)
    db_session.add(
        Report(
            reporter_id=reporter.id,
            reported_entity_type="design",
            reported_entity_id=design.id,
            reason="Inappropriate content",
        )
    )
    db_session.flush()


def test_coupon_and_redemption(db_session: Session) -> None:
    admin = make_user(db_session, role="administrator")
    user = make_user(db_session)
    coupon = Coupon(
        code="SMOKE10",
        discount_type="percentage",
        discount_value=10,
        valid_from=datetime.now(UTC),
        created_by=admin.id,
    )
    db_session.add(coupon)
    db_session.flush()

    db_session.add(
        CouponRedemption(
            coupon_id=coupon.id,
            user_id=user.id,
            discount_applied=25,
            redeemed_at=datetime.now(UTC),
        )
    )
    db_session.flush()


def test_preview_project_and_ai_generation(db_session: Session) -> None:
    user = make_user(db_session)
    design = make_design(db_session)

    db_session.add(
        PreviewProject(
            user_id=user.id, design_id=design.id, source_storage_path=f"{user.id}/hand.jpg"
        )
    )
    db_session.add(
        AiGeneration(
            user_id=user.id,
            generation_type="design_discovery",
            request_payload={"query": "floral bridal design"},
        )
    )
    db_session.flush()


def test_audit_log_and_system_setting(db_session: Session) -> None:
    admin = make_user(db_session, role="administrator")
    db_session.add(
        AuditLog(
            actor_id=admin.id,
            action="artist.verify",
            entity_type="artist_profiles",
        )
    )
    db_session.add(SystemSetting(key="smoke.setting", value={"enabled": True}, updated_by=admin.id))
    db_session.flush()


def test_seeded_categories_are_present(db_session: Session) -> None:
    slugs = set(db_session.execute(select(Category.slug)).scalars().all())
    assert "bridal" in slugs
    assert "minimalist" in slugs
