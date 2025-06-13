# services/memory_cache_service.py
"""
In-memory cache service for testing/development
"""
import asyncio
from datetime import datetime, timedelta
from typing import Any, Optional, List, Dict
import threading

from .interfaces.cache_interface import CacheServiceInterface


class MemoryCacheService(CacheServiceInterface):
    """In-memory cache implementation for development/testing"""

    def __init__(self, settings):
        self.cache = {}
        self.expiry = {}
        self.lock = threading.RLock()
        self.default_expire = timedelta(seconds=settings.cache_ttl_seconds)

    def _cleanup_expired(self):
        """Remove expired keys"""
        now = datetime.utcnow()
        expired_keys = [
            key for key, expiry_time in self.expiry.items() if expiry_time < now
        ]

        for key in expired_keys:
            self.cache.pop(key, None)
            self.expiry.pop(key, None)

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self.lock:
            self._cleanup_expired()
            return self.cache.get(key)

    async def set(
        self, key: str, value: Any, expire: Optional[timedelta] = None
    ) -> bool:
        """Set value in cache with optional expiration"""
        with self.lock:
            self.cache[key] = value

            expire_time = expire or self.default_expire
            if expire_time:
                self.expiry[key] = datetime.utcnow() + expire_time

            return True

    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        with self.lock:
            deleted = key in self.cache
            self.cache.pop(key, None)
            self.expiry.pop(key, None)
            return deleted

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        with self.lock:
            self._cleanup_expired()
            return key in self.cache

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter in cache"""
        with self.lock:
            self._cleanup_expired()
            current = self.cache.get(key, 0)
            new_value = current + amount
            self.cache[key] = new_value
            return new_value

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache"""
        with self.lock:
            self._cleanup_expired()
            return {key: self.cache[key] for key in keys if key in self.cache}

    async def set_many(
        self, items: Dict[str, Any], expire: Optional[timedelta] = None
    ) -> bool:
        """Set multiple values in cache"""
        with self.lock:
            expire_time = expire or self.default_expire
            expiry_timestamp = datetime.utcnow() + expire_time if expire_time else None

            for key, value in items.items():
                self.cache[key] = value
                if expiry_timestamp:
                    self.expiry[key] = expiry_timestamp

            return True

    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern (simple prefix matching)"""
        with self.lock:
            # Simple prefix matching for development
            matching_keys = [
                key
                for key in self.cache.keys()
                if key.startswith(pattern.replace("*", ""))
            ]

            for key in matching_keys:
                self.cache.pop(key, None)
                self.expiry.pop(key, None)

            return len(matching_keys)
