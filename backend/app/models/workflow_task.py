"""工作流任务表 (t_workflow_task)"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SnowflakePKMixin, TimestampMixin


class WorkflowTask(Base, SnowflakePKMixin, TimestampMixin):
    __tablename__ = "t_workflow_task"

    task_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        comment="任务业务 ID",
    )
    approval_order_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
        comment="关联审批单 ID",
    )
    workflow_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default="contract_review",
        comment="工作流名称",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        index=True,
        comment="任务状态: pending/running/success/failed/blocked",
    )
    current_node: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="当前执行节点",
    )
    state_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="状态快照 JSON",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="错误信息",
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="已重试次数",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="开始时间",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="完成时间",
    )
    duration_ms: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        comment="耗时(毫秒)",
    )
