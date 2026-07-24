"""ORM 模型基类与公共字段"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """时间戳混入"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )


class SnowflakePKMixin:
    """雪花 ID 主键混入"""

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=False,
        comment="雪花 ID 主键",
    )


class SoftDeleteMixin:
    """软删除混入"""

    is_deleted: Mapped[bool] = mapped_column(
        default=False,
        comment="是否删除",
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="删除时间",
    )


from app.core.database import Base  # noqa: E402

__all__ = ["Base", "TimestampMixin", "SnowflakePKMixin", "SoftDeleteMixin"]
