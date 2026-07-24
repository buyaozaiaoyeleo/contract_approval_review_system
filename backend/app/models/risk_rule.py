"""风险规则表 (t_risk_rule)"""


from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SnowflakePKMixin, TimestampMixin


class RiskRule(Base, SnowflakePKMixin, TimestampMixin):
    __tablename__ = "t_risk_rule"

    rule_code: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        comment="规则编码",
    )
    rule_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="规则名称",
    )
    rule_category: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="",
        index=True,
        comment="规则分类: amount/term/clause/subject/compliance",
    )
    rule_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="field",
        comment="规则类型: field/llm/composite",
    )
    rule_config_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="规则配置 JSON",
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="优先级",
    )
    risk_level: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="MEDIUM",
        comment="风险等级: HIGH/MEDIUM/LOW",
    )
    is_enabled: Mapped[bool] = mapped_column(
        default=True,
        index=True,
        comment="是否启用",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="规则描述",
    )
