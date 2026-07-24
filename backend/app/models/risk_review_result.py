"""风险审查结果表 (t_risk_review_result)"""


from sqlalchemy import BigInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SnowflakePKMixin, TimestampMixin


class RiskReviewResult(Base, SnowflakePKMixin, TimestampMixin):
    __tablename__ = "t_risk_review_result"

    risk_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        comment="风险结果业务 ID",
    )
    approval_order_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
        comment="关联审批单 ID",
    )
    rule_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        index=True,
        comment="关联规则 ID",
    )
    risk_level: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="LOW",
        comment="风险等级: HIGH/MEDIUM/LOW",
    )
    risk_description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        comment="风险描述",
    )
    suggestion: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="修改建议",
    )
    source_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="原文引用",
    )
    field_name: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="关联字段名",
    )
    is_valid: Mapped[bool] = mapped_column(
        default=True,
        comment="是否有效(人工确认)",
    )
