# services/interfaces/cache_service.py
"""
Cache service interface
"""
from abc import ABC, abstractmethod
from typing import Any, Optional, List
from datetime import timedelta
from typing import Dict


class CacheServiceInterface(ABC):
    """Abstract interface for caching operations"""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        pass

    @abstractmethod
    async def set(
        self, key: str, value: Any, expire: Optional[timedelta] = None
    ) -> bool:
        """Set value in cache with optional expiration"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        pass

    @abstractmethod
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter in cache"""
        pass

    @abstractmethod
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache"""
        pass

    @abstractmethod
    async def set_many(
        self, items: Dict[str, Any], expire: Optional[timedelta] = None
    ) -> bool:
        """Set multiple values in cache"""
        pass

    @abstractmethod
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        pass
