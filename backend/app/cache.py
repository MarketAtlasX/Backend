"""Redis caching layer for MarketAtlas.

Provides a simple async cache client for:
- Caching KG agent responses (expensive, 10-30s per call)
- Caching frequently-queried DB results (entities, events, prices)
- Caching market_agents analysis results (optional)

Usage:
    from app.cache import cache

    # In a service:
    cached = await cache.get(f"kg:{ticker}")
    if cached:
        return cached
    result = await expensive_call()
    await cache.set(f"kg:{ticker}", result, ttl=900)  # 15 min
"""

import json
import logging
from typing import Any, Optional

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)


class CacheClient:
    """Async Redis cache client for MarketAtlas.

    Gracefully handles Redis being unavailable — all methods return None/False
    on connection errors so the application continues without caching.
    """

    def __init__(self, redis_url: str = "") -> None:
        self._redis_url = redis_url or settings.redis_url
        self._redis: Optional[aioredis.Redis] = None

    async def connect(self) -> None:
        """Initialize the Redis connection pool."""
        try:
            self._redis = aioredis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            await self._redis.ping()
            logger.info("Redis connected at %s", self._redis_url)
        except Exception as e:
            logger.warning("Redis unavailable — caching disabled: %s", e)
            self._redis = None

    async def close(self) -> None:
        """Close the Redis connection pool."""
        if self._redis is not None:
            await self._redis.close()
            self._redis = None

    async def get(self, key: str) -> Optional[Any]:
        """Retrieve a cached value by key.

        Returns the deserialized value, or None if not found / unavailable.
        """
        if self._redis is None:
            return None
        try:
            val = await self._redis.get(key)
            return json.loads(val) if val is not None else None
        except Exception as e:
            logger.warning("Cache GET failed for key=%s: %s", key, e)
            return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Store a value in the cache with a TTL (seconds).

        Returns True on success, False if Redis is unavailable.
        """
        if self._redis is None:
            return False
        try:
            await self._redis.setex(key, ttl, json.dumps(value, default=str))
            return True
        except Exception as e:
            logger.warning("Cache SET failed for key=%s: %s", key, e)
            return False

    async def delete(self, key: str) -> bool:
        """Remove a key from the cache."""
        if self._redis is None:
            return False
        try:
            await self._redis.delete(key)
            return True
        except Exception as e:
            logger.warning("Cache DELETE failed for key=%s: %s", key, e)
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching a glob pattern (e.g. 'kg:*').

        Returns the number of deleted keys.
        """
        if self._redis is None:
            return 0
        try:
            cursor = 0
            deleted = 0
            while True:
                cursor, keys = await self._redis.scan(
                    cursor=cursor, match=pattern, count=100
                )
                if keys:
                    deleted += await self._redis.delete(*keys)
                if cursor == 0:
                    break
            return deleted
        except Exception as e:
            logger.warning("Cache CLEAR failed for pattern=%s: %s", pattern, e)
            return 0


cache = CacheClient()
