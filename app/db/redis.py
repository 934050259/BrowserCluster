"""
Redis 连接管理模块

提供 Redis 的单例连接管理，分别管理缓存和队列两个 Redis 实例
"""
import redis
from app.core.config import settings
from urllib.parse import urlparse, urlunparse

class RedisClient:
    """Redis 单例连接管理类"""

    _instance = None  # 单例实例
    _cache_client = None  # 缓存客户端
    _queue_client = None  # 队列客户端
    _proxy_client = None  # 代理池客户端

    def __new__(cls):
        """实现单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def connect_cache(self, force_reconnect: bool = False):
        """
        连接到缓存 Redis 实例

        Args:
            force_reconnect: 是否强制重新建立连接

        Returns:
            Redis: Redis 客户端实例
        """
        # 检查配置是否发生变化
        url_changed = getattr(self, '_current_cache_url', None) != settings.redis_cache_url
        
        if self._cache_client is None or url_changed or force_reconnect:
            if self._cache_client:
                try:
                    self._cache_client.close()
                except:
                    pass
                    
            self._cache_client = redis.from_url(
                settings.redis_cache_url, 
                decode_responses=True,
                health_check_interval=30,
                retry_on_timeout=True
            )
            self._current_cache_url = settings.redis_cache_url
            
        return self._cache_client

    def connect_queue(self, force_reconnect: bool = False):
        """
        连接到队列 Redis 实例

        Args:
            force_reconnect: 是否强制重新建立连接

        Returns:
            Redis: Redis 客户端实例
        """
        # 检查配置是否发生变化
        url_changed = getattr(self, '_current_queue_url', None) != settings.redis_url
        
        if self._queue_client is None or url_changed or force_reconnect:
            if self._queue_client:
                try:
                    self._queue_client.close()
                except:
                    pass
                    
            self._queue_client = redis.from_url(
                settings.redis_url, 
                decode_responses=True,
                health_check_interval=30,
                retry_on_timeout=True
            )
            self._current_queue_url = settings.redis_url
            
        return self._queue_client

    def connect_proxy(self):
        """
        连接到代理池 Redis 实例
        
        Returns:
            Redis: Redis 客户端实例
        """
        # 基于 redis_url，但修改 db

        url = urlparse(settings.redis_url)
        # 修改路径为新的 db
        new_path = f"/{settings.proxy_redis_db}"
        proxy_url = urlunparse((url.scheme, url.netloc, new_path, url.params, url.query, url.fragment))
        
        # 如果已经存在连接，先关闭
        if self._proxy_client:
            try:
                self._proxy_client.close()
            except:
                pass
                
        self._proxy_client = redis.from_url(
            proxy_url,
            decode_responses=True,
            health_check_interval=30,
            retry_on_timeout=True
        )
        # 记录当前连接的 DB 索引，用于后续检查是否需要重新连接
        self._current_proxy_db = settings.proxy_redis_db
        return self._proxy_client

    @property
    def cache(self):
        """
        获取缓存客户端，如果未连接则自动连接

        Returns:
            Redis: 缓存客户端
        """
        if self._cache_client is None:
            self.connect_cache()
        return self._cache_client

    @property
    def queue(self):
        """
        获取队列客户端，如果未连接则自动连接

        Returns:
            Redis: 队列客户端
        """
        if self._queue_client is None:
            self.connect_queue()
        return self._queue_client

    @property
    def proxy(self):
        """
        获取代理池客户端，如果未连接或配置已更改则自动连接

        Returns:
            Redis: 代理池客户端
        """
        if self._proxy_client is None or getattr(self, '_current_proxy_db', None) != settings.proxy_redis_db:
            self.connect_proxy()
        return self._proxy_client

    def close_cache(self):
        """关闭缓存连接"""
        if self._cache_client:
            self._cache_client.close()
            self._cache_client = None

    def close_queue(self):
        """关闭队列连接"""
        if self._queue_client:
            self._queue_client.close()
            self._queue_client = None

    def close_proxy(self):
        """关闭代理池连接"""
        if self._proxy_client:
            self._proxy_client.close()
            self._proxy_client = None

    def close_all(self):
        """关闭所有 Redis 连接"""
        self.close_cache()
        self.close_queue()
        self.close_proxy()


# 全局 Redis 客户端实例
redis_client = RedisClient()
