"""雪花算法 ID 生成器"""

import threading
import time


class SnowflakeGenerator:
    """雪花算法唯一 ID 生成器

    格式: 64 位
    ┌─┬─────────────────────────────────────────────────────────────┐
    │0│  timestamp(41) │ datacenter(5) │ worker(5) │ sequence(12)  │
    └─┴─────────────────────────────────────────────────────────────┘

    41 位毫秒时间戳可用约 69 年
    5 位数据中心 + 5 位工作节点 = 最多 1024 个节点
    12 位序号 = 每毫秒最多 4096 个 ID
    """

    # 起始时间戳 (2024-01-01 00:00:00)
    EPOCH = 1704067200000

    # 各部分位数
    WORKER_ID_BITS = 5
    DATACENTER_ID_BITS = 5
    SEQUENCE_BITS = 12

    # 最大值
    MAX_WORKER_ID = (1 << WORKER_ID_BITS) - 1
    MAX_DATACENTER_ID = (1 << DATACENTER_ID_BITS) - 1
    MAX_SEQUENCE = (1 << SEQUENCE_BITS) - 1

    # 左移位数
    WORKER_ID_SHIFT = SEQUENCE_BITS
    DATACENTER_ID_SHIFT = SEQUENCE_BITS + WORKER_ID_BITS
    TIMESTAMP_SHIFT = SEQUENCE_BITS + WORKER_ID_BITS + DATACENTER_ID_BITS

    def __init__(self, worker_id: int = 1, datacenter_id: int = 1):
        if worker_id < 0 or worker_id > self.MAX_WORKER_ID:
            raise ValueError(f"worker_id 必须在 0-{self.MAX_WORKER_ID} 之间")
        if datacenter_id < 0 or datacenter_id > self.MAX_DATACENTER_ID:
            raise ValueError(f"datacenter_id 必须在 0-{self.MAX_DATACENTER_ID} 之间")

        self._worker_id = worker_id
        self._datacenter_id = datacenter_id
        self._sequence = 0
        self._last_timestamp = -1
        self._lock = threading.Lock()

    def _current_millis(self) -> int:
        return int(time.time() * 1000)

    def _wait_next_millis(self, last_timestamp: int) -> int:
        timestamp = self._current_millis()
        while timestamp <= last_timestamp:
            timestamp = self._current_millis()
        return timestamp

    def next_id(self) -> int:
        with self._lock:
            timestamp = self._current_millis()

            if timestamp < self._last_timestamp:
                raise RuntimeError(
                    f"时钟回拨，拒绝生成 ID。当前时间戳 {timestamp} < 上次时间戳 {self._last_timestamp}"
                )

            if timestamp == self._last_timestamp:
                self._sequence = (self._sequence + 1) & self.MAX_SEQUENCE
                if self._sequence == 0:
                    timestamp = self._wait_next_millis(self._last_timestamp)
            else:
                self._sequence = 0

            self._last_timestamp = timestamp

            return (
                ((timestamp - self.EPOCH) << self.TIMESTAMP_SHIFT)
                | (self._datacenter_id << self.DATACENTER_ID_SHIFT)
                | (self._worker_id << self.WORKER_ID_SHIFT)
                | self._sequence
            )

    def next_str(self) -> str:
        return str(self.next_id())


_snowflake_instance: SnowflakeGenerator | None = None


def init_snowflake(worker_id: int = 1, datacenter_id: int = 1) -> SnowflakeGenerator:
    """初始化雪花 ID 生成器"""
    global _snowflake_instance
    _snowflake_instance = SnowflakeGenerator(worker_id=worker_id, datacenter_id=datacenter_id)
    return _snowflake_instance


def get_snowflake() -> SnowflakeGenerator:
    """获取雪花 ID 生成器实例"""
    global _snowflake_instance
    if _snowflake_instance is None:
        _snowflake_instance = SnowflakeGenerator()
    return _snowflake_instance


def generate_id() -> int:
    """生成唯一 ID"""
    return get_snowflake().next_id()


def generate_id_str() -> str:
    """生成唯一 ID 字符串"""
    return get_snowflake().next_str()
