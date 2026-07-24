"""审批单表 (t_approval_order)"""

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SnowflakePKMixin, TimestampMixin


class ApprovalOrder(Base, SnowflakePKMixin, TimestampMixin):
    __tablename__ = "t_approval_order"

    approval_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        comment="OA 审批单 ID",
    )
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        default="",
        comment="审批单标题",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        index=True,
        comment="审批状态: pending/approved/rejected/cancelled",
    )
    applicant: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="",
        comment="申请人",
    )
    department: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        default="",
        comment="申请部门",
    )
    oa_created_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="OA 系统创建时间",
    )
    raw_data: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="原始 JSON 数据",
    )
