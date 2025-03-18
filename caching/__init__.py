"""
Caching module for improving performance of frequently used operations.
"""
from .cache_manager import CacheManager

# Create a global cache manager instance for shared use
cache_manager = CacheManager()

def cached(func):
    """
    Decorator for caching function results.
    
    Args:
        func: Function to cache
        
    Returns:
        Decorated function
    """
    return cache_manager.cached(func)

__all__ = ['CacheManager', 'cache_manager', 'cached']