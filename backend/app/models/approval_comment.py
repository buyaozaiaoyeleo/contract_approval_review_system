"""审批评论表 (t_approval_comment)"""


from sqlalchemy import BigInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SnowflakePKMixin, TimestampMixin


class ApprovalComment(Base, SnowflakePKMixin, TimestampMixin):
    __tablename__ = "t_approval_comment"

    comment_id: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
        comment="评论业务 ID(幂等键)",
    )
    approval_order_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
        comment="关联审批单 ID",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        comment="评论内容",
    )
    risk_level: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        comment="综合风险等级",
    )
    risk_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="风险摘要",
    )
    is_ai_generated: Mapped[bool] = mapped_column(
        default=True,
        comment="是否 AI 生成",
    )
