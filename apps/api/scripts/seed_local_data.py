"""Local visual-testing seed data — see docs/visual-testing-guide.md.

Not a migration, not used in any automated test (tests use tests/db/
factories.py instead) and not run in CI. Safe to re-run: every insert is
guarded by a "does this already exist" check keyed on a fixed, human-
readable identifier (email, category slug, etc.), so running this twice
updates nothing and creates no duplicates.

Usage: .venv/Scripts/python scripts/seed_local_data.py
"""

import uuid
from datetime import date, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.enums import (
    ArtistVerificationStatus,
    BodyPlacement,
    BookingLocationType,
    BookingStatus,
    CategoryType,
    DesignDifficulty,
    DesignImageStatus,
    DesignStatus,
    PricingType,
    UserRole,
    UserStatus,
)
from app.db.models.artist import ArtistAvailability, ArtistProfile, ArtistService
from app.db.models.booking import Booking
from app.db.models.design import Category, Design, DesignCategory, DesignImage
from app.db.models.review import Review
from app.db.models.user import Profile, User, UserPreference
from app.db.session import get_sessionmaker

IMAGE_BASE = "http://localhost:3000/seed"

# --- Test personas -----------------------------------------------------

PERSONAS = [
    {"key": "customer", "email": "customer@mehndiverse.example", "role": UserRole.CUSTOMER.value},
    {"key": "artist", "email": "artist@mehndiverse.example", "role": UserRole.ARTIST.value},
    {
        "key": "verified_artist",
        "email": "verified-artist@mehndiverse.example",
        "role": UserRole.ARTIST.value,
    },
    {
        "key": "moderator",
        "email": "moderator@mehndiverse.example",
        "role": UserRole.MODERATOR.value,
    },
    {
        "key": "admin",
        "email": "admin@mehndiverse.example",
        "role": UserRole.ADMINISTRATOR.value,
    },
]

CATEGORIES = [
    ("Bridal", "bridal", CategoryType.STYLE.value),
    ("Arabic", "arabic", CategoryType.STYLE.value),
    ("Indo-Western", "indo-western", CategoryType.STYLE.value),
    ("Wedding", "wedding", CategoryType.OCCASION.value),
    ("Festival", "festival", CategoryType.OCCASION.value),
    ("Hand", "hand", CategoryType.BODY_PART.value),
    ("Foot", "foot", CategoryType.BODY_PART.value),
]

DESIGNS = [
    ("Bridal Mehndi Special", "design-bridal-mehndi.svg", ["bridal", "wedding", "hand"]),
    ("Arabic Floral Pattern", "design-arabic-floral.svg", ["arabic", "hand"]),
    ("Indo-Western Fusion", "design-indo-western.svg", ["indo-western", "wedding"]),
    ("Minimalist Hand Design", "design-minimalist-hand.svg", ["hand", "festival"]),
    ("Traditional Foot Art", "design-traditional-foot.svg", ["foot", "bridal"]),
    ("Geometric Arm Design", "design-geometric-arm.svg", ["indo-western"]),
    ("Peacock Motif", "design-peacock-motif.svg", ["bridal", "arabic"]),
    ("Rajasthani Back Design", "design-rajasthani-back.svg", ["festival"]),
]


def _get_or_create_user(db: Session, *, email: str, role: str, display_name: str) -> User:
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is not None:
        return user
    user = User(email=email, role=role, status=UserStatus.ACTIVE.value)
    db.add(user)
    db.flush()
    db.add(Profile(user_id=user.id, display_name=display_name))
    db.add(UserPreference(user_id=user.id))
    return user


def _get_or_create_category(db: Session, *, name: str, slug: str, category_type: str) -> Category:
    category = db.execute(select(Category).where(Category.slug == slug)).scalar_one_or_none()
    if category is not None:
        return category
    category = Category(name=name, slug=slug, category_type=category_type)
    db.add(category)
    db.flush()
    return category


def seed() -> dict[str, uuid.UUID]:
    Session = get_sessionmaker()
    db = Session()
    user_ids: dict[str, uuid.UUID] = {}
    try:
        # --- Personas ---
        for persona in PERSONAS:
            display_name = persona["key"].replace("_", " ").title()
            user = _get_or_create_user(
                db, email=persona["email"], role=persona["role"], display_name=display_name
            )
            user_ids[persona["key"]] = user.id
        db.flush()

        # --- Artist profiles ---
        artist_profile = db.execute(
            select(ArtistProfile).where(ArtistProfile.user_id == user_ids["artist"])
        ).scalar_one_or_none()
        if artist_profile is None:
            artist_profile = ArtistProfile(
                user_id=user_ids["artist"],
                professional_name="Aisha (unverified)",
                bio="New artist, onboarding in progress.",
                verification_status=ArtistVerificationStatus.SUBMITTED.value,
            )
            db.add(artist_profile)
            db.flush()

        verified_profile = db.execute(
            select(ArtistProfile).where(ArtistProfile.user_id == user_ids["verified_artist"])
        ).scalar_one_or_none()
        if verified_profile is None:
            verified_profile = ArtistProfile(
                user_id=user_ids["verified_artist"],
                business_name="Henna by Meera",
                professional_name="Meera Sharma",
                headline="Bridal & festival mehndi specialist",
                bio="10 years of experience in bridal and Arabic mehndi.",
                years_experience=10,
                verification_status=ArtistVerificationStatus.APPROVED.value,
                rating_average=4.8,
                rating_count=12,
            )
            db.add(verified_profile)
            db.flush()

        # A couple of extra background artists so the directory isn't empty.
        for i, name in enumerate(["Priya Designs", "Fatima Art"], start=1):
            email = f"background-artist-{i}@mehndiverse.example"
            bg_user = _get_or_create_user(
                db, email=email, role=UserRole.ARTIST.value, display_name=name
            )
            db.flush()
            existing = db.execute(
                select(ArtistProfile).where(ArtistProfile.user_id == bg_user.id)
            ).scalar_one_or_none()
            if existing is None:
                db.add(
                    ArtistProfile(
                        user_id=bg_user.id,
                        professional_name=name,
                        verification_status=ArtistVerificationStatus.APPROVED.value,
                        rating_average=4.5,
                        rating_count=6,
                    )
                )
        db.flush()

        # --- Services + availability for the verified artist ---
        existing_services = (
            db.execute(
                select(ArtistService).where(ArtistService.artist_profile_id == verified_profile.id)
            )
            .scalars()
            .all()
        )
        if not existing_services:
            db.add(
                ArtistService(
                    artist_profile_id=verified_profile.id,
                    name="Bridal Full Hands & Feet",
                    description="Detailed bridal mehndi for both hands and feet.",
                    pricing_type=PricingType.FIXED.value,
                    price_amount=8000,
                    currency="INR",
                    duration_minutes=240,
                    deposit_required=True,
                    deposit_amount=2000,
                )
            )
            db.add(
                ArtistService(
                    artist_profile_id=verified_profile.id,
                    name="Simple Hand Design",
                    description="Quick festive hand design.",
                    pricing_type=PricingType.RANGE.value,
                    price_min=500,
                    price_max=1200,
                    currency="INR",
                    duration_minutes=45,
                )
            )
            db.flush()

        existing_availability = (
            db.execute(
                select(ArtistAvailability).where(
                    ArtistAvailability.artist_profile_id == verified_profile.id
                )
            )
            .scalars()
            .all()
        )
        if not existing_availability:
            for day in range(1, 6):  # Mon-Fri
                db.add(
                    ArtistAvailability(
                        artist_profile_id=verified_profile.id,
                        day_of_week=day,
                        start_time=time(10, 0),
                        end_time=time(18, 0),
                    )
                )
            db.flush()

        # --- Categories ---
        category_by_slug = {}
        for name, slug, category_type in CATEGORIES:
            category_by_slug[slug] = _get_or_create_category(
                db, name=name, slug=slug, category_type=category_type
            )
        db.flush()

        # --- Designs (split across the two artist profiles) ---
        design_owners = [verified_profile.id, artist_profile.id]
        design_titles = [d[0] for d in DESIGNS]
        existing_titles = {
            row[0]
            for row in db.execute(select(Design.title).where(Design.title.in_(design_titles)))
        }
        for i, (title, image_file, category_slugs) in enumerate(DESIGNS):
            if title in existing_titles:
                continue
            design = Design(
                artist_profile_id=design_owners[i % len(design_owners)],
                title=title,
                description=f"A beautiful {title.lower()} for your special occasion.",
                difficulty_level=[
                    DesignDifficulty.BEGINNER.value,
                    DesignDifficulty.INTERMEDIATE.value,
                    DesignDifficulty.ADVANCED.value,
                ][i % 3],
                body_placement=(
                    BodyPlacement.FOOT.value
                    if "foot" in category_slugs and "hand" not in category_slugs
                    else BodyPlacement.HAND.value
                ),
                status=DesignStatus.PUBLISHED.value,
                is_featured=(i == 0),
            )
            db.add(design)
            db.flush()
            db.add(
                DesignImage(
                    design_id=design.id,
                    status=DesignImageStatus.READY.value,
                    image_url=f"{IMAGE_BASE}/{image_file}",
                    thumbnail_small_url=f"{IMAGE_BASE}/{image_file}",
                    thumbnail_medium_url=f"{IMAGE_BASE}/{image_file}",
                    is_primary=True,
                    sort_order=0,
                )
            )
            for slug in category_slugs:
                db.add(DesignCategory(design_id=design.id, category_id=category_by_slug[slug].id))
        db.flush()

        # --- Bookings between customer and verified artist ---
        existing_bookings = (
            db.execute(
                select(Booking).where(
                    Booking.customer_id == user_ids["customer"],
                    Booking.artist_profile_id == verified_profile.id,
                )
            )
            .scalars()
            .all()
        )
        booking_by_status: dict[str, Booking] = {b.status: b for b in existing_bookings}

        def _ensure_booking(status: str, days_offset: int) -> Booking:
            if status in booking_by_status:
                return booking_by_status[status]
            booking = Booking(
                customer_id=user_ids["customer"],
                artist_profile_id=verified_profile.id,
                status=status,
                requested_date=date.today() + timedelta(days=days_offset),
                requested_time=time(11, 0),
                location_type=BookingLocationType.ARTIST_STUDIO.value,
                contact_name="Test Customer",
                contact_email="customer@mehndiverse.example",
                contact_phone="+911234567890",
                total_amount=8000,
                currency="INR",
            )
            db.add(booking)
            db.flush()
            return booking

        _ensure_booking(BookingStatus.REQUESTED.value, 7)
        _ensure_booking(BookingStatus.QUOTATION_SENT.value, 10)
        _ensure_booking(BookingStatus.CONFIRMED.value, 14)
        completed_booking = _ensure_booking(BookingStatus.COMPLETED.value, -3)
        db.flush()

        # --- Review on the completed booking ---
        existing_review = db.execute(
            select(Review).where(Review.booking_id == completed_booking.id)
        ).scalar_one_or_none()
        if existing_review is None:
            db.add(
                Review(
                    booking_id=completed_booking.id,
                    customer_id=user_ids["customer"],
                    artist_profile_id=verified_profile.id,
                    rating=5,
                    body="Beautiful bridal mehndi, exactly what I wanted!",
                )
            )

        db.commit()
        return user_ids
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    ids = seed()
    print("Seed complete. Persona user IDs:")
    for key, value in ids.items():
        print(f"  {key}: {value}")
