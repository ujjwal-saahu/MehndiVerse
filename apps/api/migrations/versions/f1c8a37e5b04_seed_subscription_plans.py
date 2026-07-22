"""seed subscription plans

A data-only migration (see docs/migration-guidelines.md#schema-vs-data-
migrations) that seeds the six plans Phase 18 requires — one free tier plus
a monthly/yearly paid tier for each of customers and artists. `features` is
the JSONB quota/entitlement bag `app/services/entitlements.py` reads at
enforcement time; see docs/subscriptions-and-entitlements.md#plan-
definitions for what each key means. `price_amount` stays a decimal major-
unit "list price" (like `artist_services.price_amount`), not the integer-
minor-unit ledger convention `payments.amount` uses — see
docs/payments.md#7-integer-minor-currency-units and
docs/subscriptions-and-entitlements.md#why-price-amount-stays-decimal.

Revision ID: f1c8a37e5b04
Revises: d4a29f8b6c31
Create Date: 2026-07-20 10:05:00.000000

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1c8a37e5b04"
down_revision: str | Sequence[str] | None = "d4a29f8b6c31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

subscription_plans_table = sa.table(
    "subscription_plans",
    sa.column("id", UUID(as_uuid=True)),
    sa.column("name", sa.String),
    sa.column("slug", sa.String),
    sa.column("target_role", sa.String),
    sa.column("price_amount", sa.Numeric),
    sa.column("currency", sa.String),
    sa.column("billing_interval", sa.String),
    sa.column("features", JSONB),
    sa.column("is_active", sa.Boolean),
)

# (name, slug, target_role, price_amount, billing_interval, features)
PLANS: list[tuple[str, str, str, float, str, dict]] = [
    (
        "Free",
        "free-customer",
        "customer",
        0.00,
        "monthly",
        {
            "premium_design_access": False,
            "download_limit_per_month": 5,
            "ai_credits_per_month": 3,
        },
    ),
    (
        "Premium Monthly",
        "premium-customer-monthly",
        "customer",
        199.00,
        "monthly",
        {
            "premium_design_access": True,
            "download_limit_per_month": 100,
            "ai_credits_per_month": 50,
        },
    ),
    (
        "Premium Yearly",
        "premium-customer-yearly",
        "customer",
        1999.00,
        "yearly",
        {
            "premium_design_access": True,
            "download_limit_per_month": 100,
            "ai_credits_per_month": 50,
        },
    ),
    (
        "Free Artist",
        "free-artist",
        "artist",
        0.00,
        "monthly",
        {
            "portfolio_limit": 10,
            "download_limit_per_month": 5,
            "ai_credits_per_month": 3,
        },
    ),
    (
        "Professional Monthly",
        "professional-artist-monthly",
        "artist",
        499.00,
        "monthly",
        {
            "portfolio_limit": None,
            "download_limit_per_month": 200,
            "ai_credits_per_month": 100,
        },
    ),
    (
        "Professional Yearly",
        "professional-artist-yearly",
        "artist",
        4999.00,
        "yearly",
        {
            "portfolio_limit": None,
            "download_limit_per_month": 200,
            "ai_credits_per_month": 100,
        },
    ),
]


def upgrade() -> None:
    op.bulk_insert(
        subscription_plans_table,
        [
            {
                "id": uuid.uuid4(),
                "name": name,
                "slug": slug,
                "target_role": target_role,
                "price_amount": price_amount,
                "currency": "INR",
                "billing_interval": billing_interval,
                "features": features,
                "is_active": True,
            }
            for name, slug, target_role, price_amount, billing_interval, features in PLANS
        ],
    )


def downgrade() -> None:
    slugs = [slug for _, slug, _, _, _, _ in PLANS]
    op.execute(subscription_plans_table.delete().where(subscription_plans_table.c.slug.in_(slugs)))
