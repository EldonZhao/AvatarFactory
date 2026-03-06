"""
TTL Cache for API responses.

Provides in-memory caching with time-based expiration to reduce
repeated file I/O and computation for commonly accessed data.
"""

import time
from typing import Any, Dict, Optional
import threading


class TTLCache:
    """
    Thread-safe TTL (Time-To-Live) cache implementation.

    Cached items automatically expire after the specified TTL.
    """

    def __init__(self, ttl_seconds: int = 60):
        """
        Initialize the cache.

        Args:
            ttl_seconds: Time in seconds before cached items expire
        """
        self._cache: Dict[str, tuple[Any, float]] = {}
        self._ttl = ttl_seconds
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """
        Get a cached value if it exists and hasn't expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            if key not in self._cache:
                return None

            value, timestamp = self._cache[key]
            if time.time() - timestamp > self._ttl:
                # Expired, remove and return None
                del self._cache[key]
                return None

            return value

    def set(self, key: str, value: Any) -> None:
        """
        Store a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        with self._lock:
            self._cache[key] = (value, time.time())

    def invalidate(self, key: str) -> bool:
        """
        Remove a specific key from the cache.

        Args:
            key: Cache key to invalidate

        Returns:
            True if key was found and removed, False otherwise
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def invalidate_prefix(self, prefix: str) -> int:
        """
        Remove all keys starting with a given prefix.

        Args:
            prefix: Key prefix to match

        Returns:
            Number of keys removed
        """
        with self._lock:
            keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
            for key in keys_to_remove:
                del self._cache[key]
            return len(keys_to_remove)

    def clear(self) -> None:
        """Clear all cached items."""
        with self._lock:
            self._cache.clear()

    def cleanup_expired(self) -> int:
        """
        Remove all expired items from the cache.

        Returns:
            Number of expired items removed
        """
        with self._lock:
            now = time.time()
            expired = [
                key for key, (_, timestamp) in self._cache.items()
                if now - timestamp > self._ttl
            ]
            for key in expired:
                del self._cache[key]
            return len(expired)

    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats
        """
        with self._lock:
            now = time.time()
            total = len(self._cache)
            expired = sum(
                1 for _, timestamp in self._cache.values()
                if now - timestamp > self._ttl
            )
            return {
                "total_entries": total,
                "expired_entries": expired,
                "active_entries": total - expired,
                "ttl_seconds": self._ttl,
            }


# Global cache instances for different data types
# Dashboard data changes frequently, shorter TTL
dashboard_cache = TTLCache(ttl_seconds=30)

# Stats are relatively stable, longer TTL
stats_cache = TTLCache(ttl_seconds=60)

# Persona list changes rarely, longer TTL
persona_cache = TTLCache(ttl_seconds=120)

# Timeline events can be cached briefly
timeline_cache = TTLCache(ttl_seconds=30)


def get_or_set(cache: TTLCache, key: str, factory):
    """
    Get cached value or compute and cache it.

    Args:
        cache: TTLCache instance
        key: Cache key
        factory: Callable that returns the value to cache (can be sync or async)

    Returns:
        Cached or newly computed value
    """
    cached = cache.get(key)
    if cached is not None:
        return cached

    value = factory()
    cache.set(key, value)
    return value


async def get_or_set_async(cache: TTLCache, key: str, factory):
    """
    Async version of get_or_set.

    Args:
        cache: TTLCache instance
        key: Cache key
        factory: Async callable that returns the value to cache

    Returns:
        Cached or newly computed value
    """
    cached = cache.get(key)
    if cached is not None:
        return cached

    value = await factory()
    cache.set(key, value)
    return value
