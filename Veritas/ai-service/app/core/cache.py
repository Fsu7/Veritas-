"""短期内存缓存，基于 cachetools TTLCache。

P1-18 修复: 为 Embedding 计算和搜索结果添加短期缓存，
减少重复的外部 API 调用和 ChromaDB 查询开销。

Task 12.2 修复: 使用 asyncio.Lock 包装 TTLCache，保证异步并发环境下
读写操作的线程/协程安全性（cachetools.TTLCache 本身非线程安全，
在 asyncio 事件循环中并发读写可能触发 "dictionary changed size during
iteration" 或键值错乱）。
"""
import asyncio
import hashlib
import json
from cachetools import TTLCache


class AsyncSafeTTLCache:
    """对 TTLCache 的异步安全封装。

    cachetools.TTLCache 的内部字典操作不具备原子性，在 asyncio 事件循环中
    并发 get/set 可能导致字典在迭代中被修改（RuntimeError）或 TTL 过期
    清理与写入产生竞态。本封装用 asyncio.Lock 串行化 get/set/delete 操作。
    """

    def __init__(self, maxsize: int = 1000, ttl: int = 300):
        self._cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self._lock = asyncio.Lock()

    async def get(self, key):
        async with self._lock:
            return self._cache.get(key)

    async def set(self, key, value):
        async with self._lock:
            self._cache[key] = value

    async def delete(self, key):
        async with self._lock:
            self._cache.pop(key, None)

    def clear(self):
        """同步清空（仅在清空全部缓存时使用，调用方需自行保证无并发读写）。"""
        self._cache.clear()


# Embedding 缓存: TTL=5min, maxsize=2000
_embedding_cache: AsyncSafeTTLCache = AsyncSafeTTLCache(maxsize=2000, ttl=300)

# 搜索结果缓存: TTL=2min, maxsize=500
_search_cache: AsyncSafeTTLCache = AsyncSafeTTLCache(maxsize=500, ttl=120)


def _make_cache_key(*args) -> str:
    """生成缓存 Key"""
    raw = json.dumps(args, sort_keys=True, default=str)
    return hashlib.md5(raw.encode()).hexdigest()


def get_embedding_cache() -> AsyncSafeTTLCache:
    return _embedding_cache


def get_search_cache() -> AsyncSafeTTLCache:
    return _search_cache


def clear_all_caches():
    """清空所有缓存"""
    _embedding_cache.clear()
    _search_cache.clear()
