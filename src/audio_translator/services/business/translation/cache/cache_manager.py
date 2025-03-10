"""
翻译缓存管理模块，提供基于内存和Redis的缓存功能。

支持两种缓存模式：
1. 内存缓存：适用于单实例应用，重启后缓存会丢失
2. Redis缓存：适用于分布式环境，支持持久化和跨实例共享

主要功能：
- 保存翻译结果和上下文
- 根据源文本和上下文查询缓存
- 支持TTL和容量限制
- 支持按键过滤和清除
- 提供缓存命中率统计
"""

import json
import time
import hashlib
from typing import Dict, Any, Optional, List, Tuple, Union
from collections import OrderedDict
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    """翻译缓存管理器，提供内存和Redis两种缓存模式"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化缓存管理器
        
        Args:
            config: 缓存配置，包含以下选项：
                - enabled: 是否启用缓存
                - mode: 缓存模式，'memory'或'redis'
                - max_size: 最大缓存条目数
                - ttl: 缓存条目的生存时间(秒)
                - redis_url: Redis连接URL(redis模式需要)
                - persist_path: 内存缓存持久化路径(memory模式可选)
        """
        self.config = config or {}
        self.enabled = self.config.get('enabled', True)
        self.mode = self.config.get('mode', 'memory')
        self.max_size = self.config.get('max_size', 1000)
        self.ttl = self.config.get('ttl', 86400)  # 默认1天
        
        self.metrics = {
            'hits': 0,
            'misses': 0,
            'total_requests': 0,
            'hit_rate': 0.0,
            'size': 0,
            'evictions': 0,
            'last_cleanup': time.time()
        }
        
        self.memory_cache = None
        self.redis_client = None
        
        # 初始化缓存
        self._initialize_cache()
    
    def initialize(self) -> bool:
        """
        初始化缓存管理器
        
        Returns:
            初始化是否成功
        """
        try:
            # 确保缓存已初始化
            if self.mode == 'memory' and self.memory_cache is None:
                self.memory_cache = OrderedDict()
                
                # 尝试从文件加载缓存
                persist_path = self.config.get('persist_path')
                if persist_path:
                    self._load_from_file(persist_path)
            
            elif self.mode == 'redis' and self.redis_client is None:
                self._initialize_redis()
                
            logger.info(f"缓存管理器初始化成功，模式: {self.mode}")
            return True
        except Exception as e:
            logger.error(f"初始化缓存管理器失败: {e}")
            # 出错时回退到内存缓存
            self.mode = 'memory'
            self.memory_cache = OrderedDict()
            return False
    
    def _initialize_cache(self) -> None:
        """初始化缓存存储"""
        if self.mode == 'memory':
            self.memory_cache = OrderedDict()
            persist_path = self.config.get('persist_path')
            
            # 尝试从文件加载缓存
            if persist_path:
                self._load_from_file(persist_path)
        
        elif self.mode == 'redis':
            self._initialize_redis()
    
    def _initialize_redis(self) -> None:
        """初始化Redis客户端"""
        redis_url = self.config.get('redis_url')
        if not redis_url:
            logger.warning("Redis URL not configured, falling back to memory cache")
            self.mode = 'memory'
            self.memory_cache = OrderedDict()
            return
            
        try:
            import redis
            self.redis_client = redis.from_url(redis_url)
            logger.info("Redis cache initialized")
        except ImportError:
            logger.warning("Redis package not installed, falling back to memory cache")
            self.mode = 'memory'
            self.memory_cache = OrderedDict()
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            self.mode = 'memory'
            self.memory_cache = OrderedDict()
    
    def _load_from_file(self, file_path: str) -> None:
        """从文件加载缓存"""
        try:
            import os
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    
                    # 过滤掉过期的条目
                    current_time = time.time()
                    valid_entries = {
                        k: v for k, v in cache_data.items() 
                        if 'expiry' not in v or v['expiry'] > current_time
                    }
                    
                    for key, value in valid_entries.items():
                        self.memory_cache[key] = value
                    
                    self.metrics['size'] = len(self.memory_cache)
                    logger.info(f"Loaded {len(self.memory_cache)} cache entries from {file_path}")
        except Exception as e:
            logger.error(f"Failed to load cache from file {file_path}: {str(e)}")
    
    def _save_to_file(self, file_path: str) -> None:
        """将缓存保存到文件"""
        if not self.memory_cache:
            return
            
        try:
            import os
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.memory_cache, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Saved {len(self.memory_cache)} cache entries to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save cache to file {file_path}: {str(e)}")
    
    def _generate_key(self, text: str, context: Dict[str, Any] = None) -> str:
        """生成缓存键"""
        context_str = json.dumps(context or {}, sort_keys=True)
        key_data = f"{text}:{context_str}"
        return hashlib.md5(key_data.encode('utf-8')).hexdigest()
    
    def _update_metrics(self, hit: bool) -> None:
        """更新缓存指标"""
        self.metrics['total_requests'] += 1
        if hit:
            self.metrics['hits'] += 1
        else:
            self.metrics['misses'] += 1
            
        self.metrics['hit_rate'] = self.metrics['hits'] / self.metrics['total_requests'] if self.metrics['total_requests'] > 0 else 0
    
    def _check_and_cleanup(self) -> None:
        """检查并清理过期缓存"""
        current_time = time.time()
        
        # 每小时最多执行一次清理
        if current_time - self.metrics['last_cleanup'] < 3600:
            return
            
        if self.mode == 'memory':
            self._cleanup_memory_cache()
        elif self.mode == 'redis':
            # Redis会自动处理TTL，不需要手动清理
            pass
            
        self.metrics['last_cleanup'] = current_time
    
    def _cleanup_memory_cache(self) -> None:
        """清理内存缓存中的过期条目"""
        if not self.memory_cache:
            return
            
        current_time = time.time()
        expired_keys = [
            k for k, v in self.memory_cache.items() 
            if 'expiry' in v and v['expiry'] <= current_time
        ]
        
        for key in expired_keys:
            del self.memory_cache[key]
            
        self.metrics['size'] = len(self.memory_cache)
        logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def _evict_if_needed(self) -> None:
        """如果缓存超过最大大小，驱逐旧条目"""
        if self.mode == 'memory' and len(self.memory_cache) >= self.max_size:
            # 驱逐最早添加的条目(OrderedDict的第一个条目)
            self.memory_cache.popitem(last=False)
            self.metrics['evictions'] += 1
    
    def get(self, text: str, context: Dict[str, Any] = None) -> Optional[str]:
        """
        从缓存获取翻译结果
        
        Args:
            text: 原文文本
            context: 翻译上下文
            
        Returns:
            缓存的翻译结果，如果没有命中则返回None
        """
        if not self.enabled:
            self._update_metrics(False)
            return None
            
        key = self._generate_key(text, context)
        result = None
        
        if self.mode == 'memory':
            cache_entry = self.memory_cache.get(key)
            if cache_entry:
                # 检查是否过期
                if 'expiry' not in cache_entry or cache_entry['expiry'] > time.time():
                    result = cache_entry['translation']
                    # 移动到最近使用的位置
                    self.memory_cache.move_to_end(key)
                else:
                    # 移除过期条目
                    del self.memory_cache[key]
                    self.metrics['size'] = len(self.memory_cache)
        
        elif self.mode == 'redis' and self.redis_client:
            try:
                cached_data = self.redis_client.get(f"translation:{key}")
                if cached_data:
                    cache_entry = json.loads(cached_data)
                    result = cache_entry['translation']
            except Exception as e:
                logger.error(f"Redis get error: {str(e)}")
        
        self._update_metrics(result is not None)
        return result
    
    def set(self, text: str, translation: str, context: Dict[str, Any] = None) -> bool:
        """
        将翻译结果保存到缓存
        
        Args:
            text: 原文文本
            translation: 翻译结果
            context: 翻译上下文
            
        Returns:
            操作是否成功
        """
        if not self.enabled:
            return False
            
        self._check_and_cleanup()
        
        key = self._generate_key(text, context)
        timestamp = time.time()
        expiry = timestamp + self.ttl if self.ttl > 0 else None
        
        cache_entry = {
            'text': text,
            'translation': translation,
            'context': context,
            'timestamp': timestamp
        }
        
        if expiry:
            cache_entry['expiry'] = expiry
        
        if self.mode == 'memory':
            self._evict_if_needed()
            self.memory_cache[key] = cache_entry
            self.memory_cache.move_to_end(key)
            self.metrics['size'] = len(self.memory_cache)
            
            # 可选的持久化
            persist_path = self.config.get('persist_path')
            if persist_path:
                # 延迟持久化，每100次更新保存一次
                if self.metrics['total_requests'] % 100 == 0:
                    self._save_to_file(persist_path)
                    
            return True
        
        elif self.mode == 'redis' and self.redis_client:
            try:
                redis_key = f"translation:{key}"
                self.redis_client.set(
                    redis_key, 
                    json.dumps(cache_entry, ensure_ascii=False),
                    ex=self.ttl if self.ttl > 0 else None
                )
                return True
            except Exception as e:
                logger.error(f"Redis set error: {str(e)}")
                return False
        
        return False
    
    def delete(self, text: str, context: Dict[str, Any] = None) -> bool:
        """
        从缓存中删除特定条目
        
        Args:
            text: 原文文本
            context: 翻译上下文
            
        Returns:
            操作是否成功
        """
        if not self.enabled:
            return False
            
        key = self._generate_key(text, context)
        
        if self.mode == 'memory':
            if key in self.memory_cache:
                del self.memory_cache[key]
                self.metrics['size'] = len(self.memory_cache)
                return True
            return False
        
        elif self.mode == 'redis' and self.redis_client:
            try:
                return bool(self.redis_client.delete(f"translation:{key}"))
            except Exception as e:
                logger.error(f"Redis delete error: {str(e)}")
                return False
        
        return False
    
    def clear(self, pattern: str = None) -> int:
        """
        清除缓存
        
        Args:
            pattern: 可选的键模式过滤器，如果提供则只清除匹配的键
            
        Returns:
            清除的条目数量
        """
        if not self.enabled:
            return 0
            
        if self.mode == 'memory':
            if pattern:
                keys_to_delete = [
                    k for k in self.memory_cache.keys() 
                    if pattern in k or pattern in json.dumps(self.memory_cache[k], ensure_ascii=False)
                ]
                for k in keys_to_delete:
                    del self.memory_cache[k]
                count = len(keys_to_delete)
            else:
                count = len(self.memory_cache)
                self.memory_cache.clear()
                
            self.metrics['size'] = len(self.memory_cache)
            return count
        
        elif self.mode == 'redis' and self.redis_client:
            try:
                if pattern:
                    keys = self.redis_client.keys(f"translation:*{pattern}*")
                    if keys:
                        return self.redis_client.delete(*keys)
                    return 0
                else:
                    keys = self.redis_client.keys("translation:*")
                    if keys:
                        return self.redis_client.delete(*keys)
                    return 0
            except Exception as e:
                logger.error(f"Redis clear error: {str(e)}")
                return 0
        
        return 0
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        获取缓存性能指标
        
        Returns:
            缓存指标字典
        """
        # 更新大小指标
        if self.mode == 'memory':
            self.metrics['size'] = len(self.memory_cache)
        elif self.mode == 'redis' and self.redis_client:
            try:
                self.metrics['size'] = self.redis_client.dbsize()
            except Exception:
                pass
        
        # 确保指标完整
        # 'requests' 和 'total_requests' 确保至少有一个存在
        if 'requests' not in self.metrics:
            self.metrics['requests'] = self.metrics.get('total_requests', 0)
        if 'total_requests' not in self.metrics:
            self.metrics['total_requests'] = self.metrics.get('requests', 0)
            
        # 确保计算命中率
        if 'hit_rate' not in self.metrics and self.metrics.get('requests', 0) > 0:
            self.metrics['hit_rate'] = self.metrics.get('hits', 0) / self.metrics.get('requests', 1)
                
        return self.metrics
    
    def get_all_keys(self, pattern: str = None, limit: int = 100) -> List[str]:
        """
        获取缓存中的所有键
        
        Args:
            pattern: 可选的键模式过滤器
            limit: 返回键的最大数量
            
        Returns:
            键列表
        """
        if not self.enabled:
            return []
            
        if self.mode == 'memory':
            keys = list(self.memory_cache.keys())
            if pattern:
                keys = [k for k in keys if pattern in k]
            return keys[:limit]
        
        elif self.mode == 'redis' and self.redis_client:
            try:
                pattern_str = f"translation:*{pattern}*" if pattern else "translation:*"
                keys = self.redis_client.keys(pattern_str)
                # 移除前缀
                keys = [k.decode('utf-8').replace('translation:', '') for k in keys]
                return keys[:limit]
            except Exception as e:
                logger.error(f"Redis keys error: {str(e)}")
                return []
        
        return []
    
    def get_entry_details(self, key: str) -> Optional[Dict[str, Any]]:
        """
        获取特定缓存条目的详细信息
        
        Args:
            key: 缓存键
            
        Returns:
            缓存条目详情，如果不存在则返回None
        """
        if not self.enabled:
            return None
            
        if self.mode == 'memory':
            entry = self.memory_cache.get(key)
            if entry:
                return {**entry, 'ttl': entry.get('expiry', 0) - time.time() if 'expiry' in entry else -1}
            return None
        
        elif self.mode == 'redis' and self.redis_client:
            try:
                redis_key = f"translation:{key}"
                cached_data = self.redis_client.get(redis_key)
                if cached_data:
                    ttl = self.redis_client.ttl(redis_key)
                    entry = json.loads(cached_data)
                    return {**entry, 'ttl': ttl}
                return None
            except Exception as e:
                logger.error(f"Redis get entry error: {str(e)}")
                return None
        
        return None
    
    def shutdown(self) -> None:
        """
        关闭缓存管理器，保存数据并释放资源
        """
        if not self.enabled:
            return
            
        if self.mode == 'memory':
            persist_path = self.config.get('persist_path')
            if persist_path:
                self._save_to_file(persist_path)
        
        elif self.mode == 'redis' and self.redis_client:
            try:
                self.redis_client.close()
            except Exception:
                pass 