"""任务重试日志表 (t_task_retry_log)"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SnowflakePKMixin, TimestampMixin


class TaskRetryLog(Base, SnowflakePKMixin, TimestampMixin):
    __tablename__ = "t_task_retry_log"

    task_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
        comment="关联任务 ID",
    )
    node_name: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="",
        comment="节点名称",
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="第几次重试",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="错误信息",
    )
    error_type: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="错误类型",
    )
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="下次重试时间",
    )
