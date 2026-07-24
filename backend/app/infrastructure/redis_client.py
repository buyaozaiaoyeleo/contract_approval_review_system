"""Redis 客户端封装"""


import redis.asyncio as aioredis
from loguru import logger

from app.core.config import settings


class RedisClient:
    """Redis 异步客户端，封装常用数据类型操作"""

    def __init__(self):
        self._redis: aioredis.Redis | None = None

    @property
    def client(self) -> aioredis.Redis:
        if self._redis is None:
            raise RuntimeError("Redis 客户端未初始化，请先调用 connect()")
        return self._redis

    # ==================== 连接管理 ====================

    async def connect(self) -> None:
        self._redis = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,       # 自动解码为字符串
        )
        await self._redis.ping()
        logger.info(f"Redis 客户端已连接 | host={settings.REDIS_HOST}:{settings.REDIS_PORT}")

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Redis 客户端已关闭")

    def _key(self, key: str) -> str:
        """统一添加前缀，避免 key 冲突"""
        return f"{settings.REDIS_PREFIX}{key}"

    # ==================== String 操作 ====================

    async def get(self, key: str) -> str | None:
        return await self.client.get(self._key(key))

    async def set(self, key: str, value: str, expire: int | None = None) -> bool:
        return await self.client.set(self._key(key), value, ex=expire)

    async def delete(self, key: str) -> int:
        return await self.client.delete(self._key(key))

    async def exists(self, key: str) -> bool:
        return await self.client.exists(self._key(key)) > 0

    async def expire(self, key: str, seconds: int) -> bool:
        return await self.client.expire(self._key(key), seconds)

    async def ttl(self, key: str) -> int:
        return await self.client.ttl(self._key(key))

    async def incr(self, key: str, amount: int = 1) -> int:
        """自增计数器"""
        return await self.client.incrby(self._key(key), amount)

    async def decr(self, key: str, amount: int = 1) -> int:
        """自减计数器"""
        return await self.client.decrby(self._key(key), amount)

    # ==================== Hash 操作 ====================

    async def hget(self, name: str, key: str) -> str | None:
        return await self.client.hget(self._key(name), key)

    async def hset(self, name: str, key: str, value: str) -> int:
        return await self.client.hset(self._key(name), key, value)

    async def hgetall(self, name: str) -> dict:
        return await self.client.hgetall(self._key(name))

    async def hdel(self, name: str, *keys: str) -> int:
        return await self.client.hdel(self._key(name), *keys)

    # ==================== Set 操作 ====================

    async def sadd(self, key: str, *values: str) -> int:
        return await self.client.sadd(self._key(key), *values)

    async def srem(self, key: str, *values: str) -> int:
        return await self.client.srem(self._key(key), *values)

    async def smembers(self, key: str) -> set:
        return await self.client.smembers(self._key(key))

    async def sismember(self, key: str, value: str) -> bool:
        return await self.client.sismember(self._key(key), value)

    # ==================== List 操作 ====================

    async def lpush(self, key: str, *values: str) -> int:
        return await self.client.lpush(self._key(key), *values)

    async def rpush(self, key: str, *values: str) -> int:
        return await self.client.rpush(self._key(key), *values)

    async def lrange(self, key: str, start: int, end: int) -> list:
        return await self.client.lrange(self._key(key), start, end)

    # ==================== 发布订阅 ====================

    async def publish(self, channel: str, message: str) -> int:
        """发布消息到指定频道"""
        return await self.client.publish(self._key(channel), message)

    async def keys(self, pattern: str) -> list:
        """按模式匹配查找 key（生产环境慎用）"""
        return await self.client.keys(self._key(pattern))


redis_client = RedisClient()
