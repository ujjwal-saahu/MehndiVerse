from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    database_url: str = "postgresql+psycopg://mehndiverse:mehndiverse@localhost:5432/mehndiverse"
    redis_url: str = "redis://localhost:6379/0"

    # Connection pool — see docs/performance-and-reliability.md#database-
    # connection-pooling. `pool_pre_ping` (already in use) costs one extra
    # round trip per checkout but avoids handing a request a dead connection
    # after a network blip/DB restart; these bound how many connections one
    # API process holds and how long a request waits for one under load.
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout_seconds: float = 30.0
    # Recycles a connection before a typical managed-Postgres idle-connection
    # cutoff (Supabase/most managed Postgres close idle connections well
    # under an hour) closes it out from under us.
    db_pool_recycle_seconds: int = 1800

    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]

    # Observability — see docs/observability.md. `metrics_token` gates
    # GET /metrics (defense-in-depth on top of the reverse-proxy/network-
    # level restriction that must also be in place — see that doc); the
    # local-dev default is a fixed, non-secret string precisely because it
    # protects nothing on a developer's own machine, unlike the
    # placeholder-then-real-secret pattern used for Supabase/Razorpay.
    metrics_token: str = "local-dev-metrics-token"
    # Sentry DSN — non-functional (Sentry SDK silently no-ops) until a real
    # project DSN is set via a real .env; see docs/observability.md#error-
    # tracking-sentry.
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.1
    # Slack-compatible incoming-webhook URL for send_alert() — see
    # app/core/alerts.py. Empty means alerts still log at ERROR (always
    # real, always visible to log aggregation) but skip the webhook POST.
    alert_webhook_url: str = ""

    # Supabase Authentication (see docs/authentication.md). Defaults are
    # non-functional placeholders — a real project's values go in apps/api/.env,
    # never committed. supabase_jwt_secret must match the project's JWT secret
    # so access tokens can be verified locally (no network round-trip).
    supabase_url: str = "https://placeholder.supabase.co"
    supabase_anon_key: str = "placeholder-anon-key"
    supabase_service_role_key: str = "placeholder-service-role-key"
    supabase_jwt_secret: str = "placeholder-jwt-secret-change-me"
    supabase_jwt_audience: str = "authenticated"

    auth_rate_limit: str = "5/minute"
    # Account-based login-abuse protection (on top of the IP-based rate
    # limit above) — see docs/security-review.md#login-abuse-protection.
    login_lockout_threshold: int = 5
    login_lockout_window_seconds: int = 900

    # How long a PENDING_DELETION account waits before
    # app/cli/process_account_deletions.py anonymizes it — a window to
    # cancel an accidental/coerced deletion request. See
    # docs/security-review.md#account-deletion.
    account_deletion_grace_period_days: int = 14
    search_rate_limit: str = "30/minute"
    message_rate_limit: str = "20/minute"

    # Which SearchProvider implementation app/services/search/factory.py
    # constructs — see docs/design-search.md#search-provider-abstraction.
    # "postgres" is the only implementation today; a future phase can add
    # "typesense"/"meilisearch" without changing any route code.
    search_provider: str = "postgres"

    # Which PaymentProvider implementation app/services/payments/factory.py
    # constructs — see docs/payments.md#1-payment-provider-abstraction.
    # `payment_region` picks the provider appropriate for where the project
    # operates (MehndiVerse is India-first, so "IN" -> Razorpay); a future
    # phase serving a different region can add another provider/region
    # mapping without changing any route code. `payment_provider` overrides
    # the region's default when set explicitly.
    payment_region: str = "IN"
    payment_provider: str | None = None

    # Razorpay sandbox/test-mode credentials (see
    # docs/payments.md#2-sandbox-integration-razorpay). Defaults are
    # non-functional placeholders — a real project's test-mode values go in
    # apps/api/.env, never committed and never hardcoded in source. The key
    # id is not a secret (Razorpay's client-side Checkout is initialized
    # with it) but the key secret and webhook secret must never reach a
    # client.
    razorpay_key_id: str = "rzp_test_placeholder"
    razorpay_key_secret: str = "placeholder-key-secret-change-me"
    razorpay_webhook_secret: str = "placeholder-webhook-secret-change-me"
    razorpay_api_base_url: str = "https://api.razorpay.com/v1"

    # Platform commission taken from every successful payment before the
    # artist's earning is recorded — see
    # docs/payments.md#8-platform-commission-and-artist-earnings.
    platform_commission_percent: float = 15.0

    payment_rate_limit: str = "10/minute"

    # Abuse-prevention rate limits — see
    # docs/community-and-trust.md#7-abuse-prevention.
    comment_rate_limit: str = "20/minute"
    report_rate_limit: str = "10/minute"
    support_request_rate_limit: str = "5/minute"

    # Subscriptions and entitlements — see
    # docs/subscriptions-and-entitlements.md#grace-period. How long a
    # subscription stays `past_due` (entitlements still active) after a
    # failed renewal before `process_due_subscriptions()` expires it.
    subscription_grace_period_days: int = 3
    subscription_rate_limit: str = "10/minute"

    # Hand/foot design preview — see docs/hand-foot-preview.md. Rate-limits
    # the image-processing-heavy endpoints (upload/export) as a performance
    # safeguard against abuse, not the cheap read/share/delete ones.
    preview_rate_limit: str = "20/minute"

    # AI foundation — see docs/ai-foundation.md#provider-abstraction. Which
    # AiProvider implementation app/services/ai/factory.py constructs;
    # "local" is the only implementation today (see
    # app/services/ai/local_provider.py) — a future phase can add a real
    # cloud provider without changing any caller. `ai_provider_api_key` is a
    # placeholder for that future provider: read only inside its own
    # provider module, never logged, never returned in any API response —
    # see docs/ai-foundation.md#never-expose-provider-keys.
    ai_provider: str = "local"
    ai_provider_api_key: str = "placeholder-ai-provider-key-change-me"
    # Per-call timeout enforced by the job worker around every provider
    # call (see app/services/ai/jobs.py) — not just a client-library
    # option, since the local provider has no client library to configure.
    ai_provider_timeout_seconds: float = 15.0
    ai_job_max_attempts: int = 3
    # How long an `ai_jobs` row may sit `running` before
    # `requeue_stuck_jobs()` treats its worker as dead and resets it — see
    # docs/ai-foundation.md#timeouts-are-soft.
    ai_job_stuck_after_seconds: int = 300
    ai_rate_limit: str = "20/minute"
    # Similarity/duplicate-detection thresholds — see
    # docs/ai-foundation.md#similar-design-search and
    # #duplicate-image-detection.
    ai_duplicate_similarity_threshold: float = 0.97
    ai_moderation_review_confidence_threshold: float = 0.5

    # Personalized AI design assistant — see docs/ai-design-assistant.md.
    # Separate (tighter) rate limit than `ai_rate_limit`: this endpoint
    # enqueues a real generation job and consumes a subscription quota
    # credit, so it deserves its own abuse-prevention ceiling rather than
    # sharing the lighter-weight AI-capability limit.
    ai_design_rate_limit: str = "10/minute"
    # See docs/ai-design-assistant.md#generation-failure-and-retry-flow —
    # the hard per-request cap that "prevents unlimited retries".
    ai_design_request_max_retries: int = 3

    # Product analytics and recommendations — see docs/analytics-and-
    # recommendations.md. Generous relative to other rate limits: a client
    # may legitimately fire `app_opened` once per cold start plus the
    # occasional `design_shared`, and this is a cheap append-only write, not
    # a job-enqueuing or provider-calling endpoint.
    analytics_rate_limit: str = "60/minute"


@lru_cache
def get_settings() -> Settings:
    return Settings()
