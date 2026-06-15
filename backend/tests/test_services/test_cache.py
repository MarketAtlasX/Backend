"""Tests for the Redis cache client.

These test the cache logic without requiring a running Redis instance.
The CacheClient handles Redis being unavailable gracefully.
"""

import pytest

from app.cache import CacheClient


@pytest.mark.asyncio
async def test_cache_returns_none_when_disconnected():
    cache = CacheClient(redis_url="redis://localhost:19999/0")
    result = await cache.get("test_key")
    assert result is None


@pytest.mark.asyncio
async def test_cache_set_returns_false_when_disconnected():
    cache = CacheClient(redis_url="redis://localhost:19999/0")
    result = await cache.set("test_key", {"data": 123})
    assert result is False


@pytest.mark.asyncio
async def test_cache_delete_returns_false_when_disconnected():
    cache = CacheClient(redis_url="redis://localhost:19999/0")
    result = await cache.delete("test_key")
    assert result is False


@pytest.mark.asyncio
async def test_cache_clear_pattern_returns_zero_when_disconnected():
    cache = CacheClient(redis_url="redis://localhost:19999/0")
    result = await cache.clear_pattern("kg:*")
    assert result == 0


@pytest.mark.asyncio
async def test_cache_connect_does_not_raise_on_bad_url():
    cache = CacheClient(redis_url="redis://nonexistent:6379/0")
    await cache.connect()
    assert cache._redis is None
