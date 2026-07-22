"""Import every model module so they register with Base.metadata — required
for Alembic autogenerate to see the full schema (see migrations/env.py)."""

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
from app.db.models.artist import (
    ArtistAvailability,
    ArtistBlockedDate,
    ArtistDocument,
    ArtistProfile,
    ArtistService,
)
from app.db.models.booking import Booking, BookingAttachment, BookingQuote, BookingStatusHistory
from app.db.models.design import Category, Design, DesignCategory, DesignImage, DesignTag, Tag
from app.db.models.engagement import Collection, CollectionItem, Comment, Follow, Like
from app.db.models.marketing import Coupon, CouponRedemption
from app.db.models.messaging import Conversation, ConversationMember, Message
from app.db.models.moderation import Report
from app.db.models.notification import Notification
from app.db.models.payment import Payment, Payout, Refund
from app.db.models.promotions import (
    FeaturedCollection,
    FeaturedCollectionItem,
    NotificationCampaign,
    PromoBanner,
)
from app.db.models.review import Review
from app.db.models.search import SearchEvent
from app.db.models.subscription import Subscription, SubscriptionPlan, SubscriptionStatusHistory
from app.db.models.support import ConsentRecord, DataExportRequest, SupportRequest
from app.db.models.system import AuditLog, SystemSetting
from app.db.models.usage import UsageRecord
from app.db.models.user import Profile, User, UserBlock, UserDevice, UserPreference

__all__ = [
    "AiDesignRequest",
    "AiGeneration",
    "AiJob",
    "DesignDuplicateMatch",
    "DesignEmbedding",
    "DesignTagSuggestion",
    "PreviewProject",
    "AnalyticsEvent",
    "ArtistAvailability",
    "ArtistBlockedDate",
    "ArtistDocument",
    "ArtistProfile",
    "ArtistService",
    "Booking",
    "BookingAttachment",
    "BookingQuote",
    "BookingStatusHistory",
    "Category",
    "Design",
    "DesignCategory",
    "DesignImage",
    "DesignTag",
    "Tag",
    "Collection",
    "CollectionItem",
    "Comment",
    "Follow",
    "Like",
    "Coupon",
    "CouponRedemption",
    "Conversation",
    "ConversationMember",
    "Message",
    "Report",
    "Notification",
    "Payment",
    "Payout",
    "Refund",
    "PromoBanner",
    "FeaturedCollection",
    "FeaturedCollectionItem",
    "NotificationCampaign",
    "Review",
    "SearchEvent",
    "Subscription",
    "SubscriptionPlan",
    "SubscriptionStatusHistory",
    "ConsentRecord",
    "DataExportRequest",
    "SupportRequest",
    "AuditLog",
    "SystemSetting",
    "UsageRecord",
    "Profile",
    "User",
    "UserBlock",
    "UserDevice",
    "UserPreference",
]
