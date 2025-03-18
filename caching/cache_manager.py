"""
Cache manager for improving performance of frequently used operations.
"""
from typing import Dict, Any, Tuple, Callable, Optional, TypeVar
import functools
import hashlib
import time

# Type variable for generic caching
T = TypeVar('T')

class CacheManager:
    """
    Cache manager for storing results of expensive operations.
    Implements various caching strategies.
    """
    
    def __init__(self, max_size: int = 100, ttl: int = 300):
        """
        Initialize a cache manager.
        
        Args:
            max_size: Maximum number of items to store in the cache
            ttl: Time-to-live in seconds for cache items
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache: Dict[str, Tuple[Any, float]] = {}
        
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        if key not in self.cache:
            return None
            
        value, timestamp = self.cache[key]
        
        # Check if the item has expired
        if time.time() - timestamp > self.ttl:
            del self.cache[key]
            return None
            
        return value
        
    def set(self, key: str, value: Any) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        # If the cache is full, remove the oldest item
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.items(), key=lambda x: x[1][1])[0]
            del self.cache[oldest_key]
            
        self.cache[key] = (value, time.time())
        
    def clear(self) -> None:
        """
        Clear the cache.
        """
        self.cache.clear()
        
    def remove(self, key: str) -> None:
        """
        Remove an item from the cache.
        
        Args:
            key: Cache key
        """
        if key in self.cache:
            del self.cache[key]
            
    @staticmethod
    def get_hash_key(*args, **kwargs) -> str:
        """
        Generate a hash key from function arguments.
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Hash key as a string
        """
        # Convert args and kwargs to strings
        args_str = str(args)
        kwargs_str = str(sorted(kwargs.items()))
        
        # Generate a hash
        hash_obj = hashlib.md5((args_str + kwargs_str).encode())
        return hash_obj.hexdigest()
        
    def cached(self, func: Callable[..., T]) -> Callable[..., T]:
        """
        Decorator for caching function results.
        
        Args:
            func: Function to cache
            
        Returns:
            Decorated function
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate a cache key from the function name and arguments
            key = f"{func.__module__}.{func.__name__}.{self.get_hash_key(*args, **kwargs)}"
            
            # Check if the result is already cached
            cached_result = self.get(key)
            if cached_result is not None:
                return cached_result
                
            # Call the function and cache the result
            result = func(*args, **kwargs)
            self.set(key, result)
            return result
            
        return wrapper