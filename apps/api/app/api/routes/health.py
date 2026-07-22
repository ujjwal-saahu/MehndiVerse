from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.alerts import send_alert
from app.core.logging import get_logger
from app.core.redis_client import get_redis_client
from app.db.session import get_engine

router = APIRouter(tags=["health"])
logger = get_logger(__name__)


class HealthStatus(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["ok", "unavailable"]
    cache: Literal["ok", "unavailable"]


class LivenessStatus(BaseModel):
    status: Literal["ok"]


@router.get("/health/live", response_model=LivenessStatus)
def liveness() -> LivenessStatus:
    """Pure liveness probe — no dependency checks. Answering at all means the
    process is up and able to serve a request; a container orchestrator
    should restart the process if *this* stops responding, not merely if a
    downstream dependency is briefly unavailable (that's what `/health`
    below, used as the readiness probe, is for — see
    docs/performance-and-reliability.md#health-and-readiness-checks)."""
    return LivenessStatus(status="ok")


@router.get("/health", response_model=HealthStatus)
def health() -> HealthStatus:
    """Readiness probe. Reports overall status plus dependency status —
    "unavailable" here should take the instance out of a load balancer's
    rotation, not restart it (that's the liveness probe's job)."""
    database_status: Literal["ok", "unavailable"] = "ok"
    cache_status: Literal["ok", "unavailable"] = "ok"

    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        # Database-health alert — see docs/observability.md#alerting.
        send_alert("database_unavailable", error=str(exc))
        database_status = "unavailable"

    try:
        # Reuses the process-wide pooled client (app/core/redis_client.py)
        # instead of opening a brand-new connection on every readiness
        # check — load-test evidence (docs/performance-and-reliability.md
        # #load-test-results) showed this endpoint's p95 latency was ~3x
        # the data endpoints' before this fix, entirely from Redis
        # connection setup on every single call.
        get_redis_client().ping()
    except RedisError as exc:
        send_alert("cache_unavailable", error=str(exc))
        cache_status = "unavailable"

    overall: Literal["ok", "degraded"] = (
        "ok" if database_status == "ok" and cache_status == "ok" else "degraded"
    )
    return HealthStatus(status=overall, database=database_status, cache=cache_status)
