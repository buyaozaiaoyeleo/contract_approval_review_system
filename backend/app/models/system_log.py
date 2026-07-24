"""系统操作日志表 (t_system_log)"""


from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SnowflakePKMixin, TimestampMixin


class SystemLog(Base, SnowflakePKMixin, TimestampMixin):
    __tablename__ = "t_system_log"

    level: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="INFO",
        index=True,
        comment="日志级别: INFO/WARNING/ERROR/DEBUG",
    )
    module: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="system",
        index=True,
        comment="模块名称: risk/workflow/contract/approval/system",
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="日志消息",
    )
    detail: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="详细信息（JSON 格式）",
    )