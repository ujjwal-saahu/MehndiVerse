"""Effective-role computation and role-grant rules.

See docs/authentication.md#1 for why this mapping exists: the stored
`users.role` column (Phase 2) uses `administrator`/`super_administrator`;
this phase's API surface speaks `admin`/`super_admin` and additionally
exposes `premium_customer`/`verified_artist` as *derived* effective roles,
never stored.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.enums import ArtistVerificationStatus, SubscriptionStatus, UserRole
from app.db.models.artist import ArtistProfile
from app.db.models.subscription import Subscription
from app.db.models.user import User

# Stored users.role -> API-facing effective role (before status derivation).
_ROLE_LABELS: dict[str, str] = {
    UserRole.CUSTOMER.value: "customer",
    UserRole.ARTIST.value: "artist",
    UserRole.MODERATOR.value: "moderator",
    UserRole.ADMINISTRATOR.value: "admin",
    UserRole.SUPER_ADMINISTRATOR.value: "super_admin",
}

ALL_EFFECTIVE_ROLES = frozenset(
    {
        "customer",
        "premium_customer",
        "artist",
        "verified_artist",
        "moderator",
        "admin",
        "super_admin",
    }
)

# Who may grant which *stored* role via the admin role-management endpoint.
# A role never grants itself upward, and nobody can grant a role to themselves
# (enforced separately in the route, not here) — see docs/authentication.md#3.
GRANTABLE_ROLES_BY_GRANTOR: dict[str, frozenset[str]] = {
    UserRole.SUPER_ADMINISTRATOR.value: frozenset(
        {
            UserRole.CUSTOMER.value,
            UserRole.ARTIST.value,
            UserRole.MODERATOR.value,
            UserRole.ADMINISTRATOR.value,
            UserRole.SUPER_ADMINISTRATOR.value,
        }
    ),
    UserRole.ADMINISTRATOR.value: frozenset(
        {UserRole.CUSTOMER.value, UserRole.ARTIST.value, UserRole.MODERATOR.value}
    ),
}


def can_grant_role(*, grantor_role: str, target_role: str) -> bool:
    return target_role in GRANTABLE_ROLES_BY_GRANTOR.get(grantor_role, frozenset())


def get_effective_role(user: User, db: Session) -> str:
    """Never trust a client-sent role — this always re-derives from the
    database using the authenticated user's id."""
    base_role = _ROLE_LABELS.get(user.role, user.role)

    if user.role == UserRole.CUSTOMER.value:
        has_active_subscription = db.execute(
            select(Subscription.id).where(
                Subscription.user_id == user.id,
                Subscription.status == SubscriptionStatus.ACTIVE.value,
                Subscription.current_period_end > datetime.now(UTC),
            )
        ).first()
        if has_active_subscription:
            return "premium_customer"
        return base_role

    if user.role == UserRole.ARTIST.value:
        artist_profile = db.execute(
            select(ArtistProfile.verification_status).where(ArtistProfile.user_id == user.id)
        ).scalar_one_or_none()
        if artist_profile == ArtistVerificationStatus.APPROVED.value:
            return "verified_artist"
        return base_role

    return base_role
