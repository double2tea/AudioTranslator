"""
翻译缓存管理包

提供翻译缓存服务，减少重复翻译请求
"""

from .cache_manager import CacheManager

__all__ = ['CacheManager'] 