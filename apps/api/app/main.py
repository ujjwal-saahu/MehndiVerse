from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.deps import limiter
from app.api.routes.account_export import router as account_export_router
from app.api.routes.admin_ai import router as admin_ai_router
from app.api.routes.admin_analytics import router as admin_analytics_router
from app.api.routes.admin_artist_verification import router as admin_artist_verification_router
from app.api.routes.admin_audit_log import router as admin_audit_log_router
from app.api.routes.admin_banners import router as admin_banners_router
from app.api.routes.admin_bookings import router as admin_bookings_router
from app.api.routes.admin_coupons import router as admin_coupons_router
from app.api.routes.admin_dashboard import router as admin_dashboard_router
from app.api.routes.admin_designs import router as admin_designs_router
from app.api.routes.admin_featured_collections import router as admin_featured_collections_router
from app.api.routes.admin_messaging import router as admin_messaging_router
from app.api.routes.admin_moderation import router as admin_moderation_router
from app.api.routes.admin_notification_campaigns import (
    router as admin_notification_campaigns_router,
)
from app.api.routes.admin_payments import router as admin_payments_router
from app.api.routes.admin_reviews import router as admin_reviews_router
from app.api.routes.admin_settings import router as admin_settings_router
from app.api.routes.admin_tags import router as admin_tags_router
from app.api.routes.admin_users import router as admin_users_router
from app.api.routes.ai import design_ai_router
from app.api.routes.ai import router as ai_router
from app.api.routes.ai_designs import router as ai_designs_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.artist_bookings import router as artist_bookings_router
from app.api.routes.artist_onboarding import router as artist_onboarding_router
from app.api.routes.artist_scheduling import router as artist_scheduling_router
from app.api.routes.artist_services import router as artist_services_router
from app.api.routes.artists import router as artists_router
from app.api.routes.auth import router as auth_router
from app.api.routes.bookings import router as bookings_router
from app.api.routes.categories import router as categories_router
from app.api.routes.collections import router as collections_router
from app.api.routes.comments import router as comments_router
from app.api.routes.coupons import router as coupons_router
from app.api.routes.designs import router as designs_router
from app.api.routes.engagement import router as engagement_router
from app.api.routes.health import router as health_router
from app.api.routes.legal import router as legal_router
from app.api.routes.messaging import router as messaging_router
from app.api.routes.metrics import router as metrics_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.payment_webhooks import router as payment_webhooks_router
from app.api.routes.payments import router as payments_router
from app.api.routes.previews import router as previews_router
from app.api.routes.profile import router as profile_router
from app.api.routes.reports import router as reports_router
from app.api.routes.reviews import router as reviews_router
from app.api.routes.search import router as search_router
from app.api.routes.subscriptions import router as subscriptions_router
from app.api.routes.support import router as support_router
from app.core.config import get_settings
from app.core.error_tracking import configure_error_tracking
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.request_context import add_request_context
from app.core.security_headers import add_security_headers

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    configure_error_tracking()
    logger = get_logger(__name__)

    app = FastAPI(title="MehndiVerse API", version="0.1.0")

    add_security_headers(app)
    add_request_context(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def handle_rate_limit_exceeded(request: Request, exc: Exception) -> Response:
        assert isinstance(exc, RateLimitExceeded)  # guaranteed by the handler registration below
        return _rate_limit_exceeded_handler(request, exc)

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, handle_rate_limit_exceeded)
    app.add_middleware(SlowAPIMiddleware)

    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(metrics_router)
    app.include_router(auth_router, prefix=API_PREFIX)
    app.include_router(admin_users_router, prefix=API_PREFIX)
    app.include_router(profile_router, prefix=API_PREFIX)
    # search_router and engagement_router must be included before
    # designs_router: `/designs/search` and `/designs/saved` are literal
    # paths that `/designs/{design_id}` would otherwise capture.
    app.include_router(search_router, prefix=API_PREFIX)
    app.include_router(engagement_router, prefix=API_PREFIX)
    app.include_router(designs_router, prefix=API_PREFIX)
    app.include_router(categories_router, prefix=API_PREFIX)
    app.include_router(collections_router, prefix=API_PREFIX)
    app.include_router(artist_onboarding_router, prefix=API_PREFIX)
    app.include_router(admin_artist_verification_router, prefix=API_PREFIX)
    app.include_router(artist_services_router, prefix=API_PREFIX)
    app.include_router(artist_scheduling_router, prefix=API_PREFIX)
    app.include_router(artists_router, prefix=API_PREFIX)
    app.include_router(bookings_router, prefix=API_PREFIX)
    app.include_router(artist_bookings_router, prefix=API_PREFIX)
    app.include_router(messaging_router, prefix=API_PREFIX)
    app.include_router(admin_messaging_router, prefix=API_PREFIX)
    app.include_router(notifications_router, prefix=API_PREFIX)
    app.include_router(payments_router, prefix=API_PREFIX)
    app.include_router(payment_webhooks_router, prefix=API_PREFIX)
    app.include_router(admin_payments_router, prefix=API_PREFIX)
    app.include_router(comments_router, prefix=API_PREFIX)
    app.include_router(reviews_router, prefix=API_PREFIX)
    app.include_router(reports_router, prefix=API_PREFIX)
    app.include_router(admin_moderation_router, prefix=API_PREFIX)
    app.include_router(admin_dashboard_router, prefix=API_PREFIX)
    app.include_router(admin_designs_router, prefix=API_PREFIX)
    app.include_router(admin_tags_router, prefix=API_PREFIX)
    app.include_router(admin_bookings_router, prefix=API_PREFIX)
    app.include_router(admin_reviews_router, prefix=API_PREFIX)
    app.include_router(admin_banners_router, prefix=API_PREFIX)
    app.include_router(admin_featured_collections_router, prefix=API_PREFIX)
    app.include_router(admin_notification_campaigns_router, prefix=API_PREFIX)
    app.include_router(admin_audit_log_router, prefix=API_PREFIX)
    app.include_router(admin_settings_router, prefix=API_PREFIX)
    app.include_router(subscriptions_router, prefix=API_PREFIX)
    app.include_router(coupons_router, prefix=API_PREFIX)
    app.include_router(admin_coupons_router, prefix=API_PREFIX)
    app.include_router(ai_router, prefix=API_PREFIX)
    app.include_router(design_ai_router, prefix=API_PREFIX)
    app.include_router(admin_ai_router, prefix=API_PREFIX)
    app.include_router(ai_designs_router, prefix=API_PREFIX)
    app.include_router(previews_router, prefix=API_PREFIX)
    app.include_router(analytics_router, prefix=API_PREFIX)
    app.include_router(legal_router, prefix=API_PREFIX)
    app.include_router(support_router, prefix=API_PREFIX)
    app.include_router(account_export_router, prefix=API_PREFIX)
    app.include_router(admin_analytics_router, prefix=API_PREFIX)

    logger.info("app_startup", environment=settings.environment)
    return app


app = create_app()
