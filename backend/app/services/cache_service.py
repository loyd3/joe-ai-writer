"""
缓存服务 - 简单的内存缓存
"""
import time
from typing import Any, Optional, Dict
from datetime import datetime, timedelta


class CacheService:
    """简单的内存缓存服务"""
    
    _instance = None
    _cache: Dict[str, Dict[str, Any]] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key in self._cache:
            item = self._cache[key]
            if item["expires"] > time.time():
                return item["value"]
            else:
                del self._cache[key]
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 3600
    ) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），默认1小时
        """
        self._cache[key] = {
            "value": value,
            "expires": time.time() + ttl
        }
    
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    async def clear(self) -> None:
        """清空所有缓存"""
        self._cache.clear()
    
    async def keys(self) -> list:
        """获取所有缓存键"""
        return list(self._cache.keys())
    
    @staticmethod
    def make_key(*args, **kwargs) -> str:
        """
        生成缓存键
        
        示例：
            make_key("hot_topics", date="2024-01-01")
            # 返回: "hot_topics:date=2024-01-01"
        """
        key_parts = list(args)
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={v}")
        return ":".join(map(str, key_parts))


# 创建单例实例
cache_service = CacheService()
