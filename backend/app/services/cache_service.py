# services/cache_service.py
"""
Cache service implementation using Redis
"""
import json
import pickle
from datetime import timedelta
from typing import Any, Optional, List, Dict
import logging

from .interfaces.cache_interface import CacheServiceInterface
from ..core.config import BaseSettings

logger = logging.getLogger(__name__)


class RedisCacheService(CacheServiceInterface):
    """Redis-based cache implementation"""

    def __init__(self, redis_client, settings: BaseSettings):
        self.redis = redis_client
        self.settings = settings
        self.default_expire = timedelta(seconds=settings.cache_ttl_seconds)

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis:
            return None

        try:
            value = await self.redis.get(key)
            if value is None:
                return None

            # Try to deserialize as JSON first, then pickle
            try:
                return json.loads(value)
            except (json.JSONDecodeError, UnicodeDecodeError):
                return pickle.loads(value)

        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            return None

    async def set(
        self, key: str, value: Any, expire: Optional[timedelta] = None
    ) -> bool:
        """Set value in cache with optional expiration"""
        if not self.redis:
            return False

        try:
            # Serialize value
            try:
                serialized_value = json.dumps(value)
            except (TypeError, ValueError):
                serialized_value = pickle.dumps(value)

            expire_seconds = None
            if expire:
                expire_seconds = int(expire.total_seconds())
            elif self.default_expire:
                expire_seconds = int(self.default_expire.total_seconds())

            await self.redis.set(key, serialized_value, ex=expire_seconds)
            return True

        except Exception as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if not self.redis:
            return False

        try:
            result = await self.redis.delete(key)
            return result > 0
        except Exception as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.redis:
            return False

        try:
            result = await self.redis.exists(key)
            return result > 0
        except Exception as e:
            logger.warning(f"Cache exists error for key {key}: {e}")
            return False

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter in cache"""
        if not self.redis:
            return 0

        try:
            return await self.redis.incrby(key, amount)
        except Exception as e:
            logger.warning(f"Cache increment error for key {key}: {e}")
            return 0

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache"""
        if not self.redis:
            return {}

        try:
            values = await self.redis.mget(keys)
            result = {}

            for key, value in zip(keys, values):
                if value is not None:
                    try:
                        result[key] = json.loads(value)
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        result[key] = pickle.loads(value)

            return result

        except Exception as e:
            logger.warning(f"Cache get_many error: {e}")
            return {}

    async def set_many(
        self, items: Dict[str, Any], expire: Optional[timedelta] = None
    ) -> bool:
        """Set multiple values in cache"""
        if not self.redis:
            return False

        try:
            pipe = self.redis.pipeline()

            expire_seconds = None
            if expire:
                expire_seconds = int(expire.total_seconds())
            elif self.default_expire:
                expire_seconds = int(self.default_expire.total_seconds())

            for key, value in items.items():
                try:
                    serialized_value = json.dumps(value)
                except (TypeError, ValueError):
                    serialized_value = pickle.dumps(value)

                pipe.set(key, serialized_value, ex=expire_seconds)

            await pipe.execute()
            return True

        except Exception as e:
            logger.warning(f"Cache set_many error: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        if not self.redis:
            return 0

        try:
            keys = await self.redis.keys(pattern)
            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Cache clear_pattern error for pattern {pattern}: {e}")
            return 0
