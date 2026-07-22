from functools import lru_cache

import redis

from app.core.config import get_settings


@lru_cache
def get_redis_client() -> redis.Redis:
    # `socket_timeout` (per-operation) was previously unset — an unresponsive
    # Redis could hang a request indefinitely on a plain GET/INCR, not just
    # on connect. See docs/performance-and-reliability.md#timeouts.
    return redis.Redis.from_url(
        get_settings().redis_url, socket_connect_timeout=2, socket_timeout=2
    )
