"""系统配置表 (t_system_config)"""


from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SnowflakePKMixin, TimestampMixin


class SystemConfig(Base, SnowflakePKMixin, TimestampMixin):
    __tablename__ = "t_system_config"

    config_key: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
        comment="配置键",
    )
    config_value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        comment="配置值",
    )
    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="配置说明",
    )
