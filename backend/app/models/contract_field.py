"""合同字段提取表 (t_contract_field)"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SnowflakePKMixin, TimestampMixin


class ContractField(Base, SnowflakePKMixin, TimestampMixin):
    __tablename__ = "t_contract_field"

    document_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
        comment="关联文档 ID",
    )
    contract_no: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="合同编号",
    )
    party_a_info: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="甲方信息(JSON)",
    )
    party_b_info: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="乙方信息(JSON)",
    )
    amount: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="合同金额",
    )
    start_date: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="合同开始日期",
    )
    end_date: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="合同结束日期",
    )
    payment_terms: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="付款条款",
    )
    liability_clause: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="违约责任",
    )
    confidentiality: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="保密条款",
    )
    dispute_resolution: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="争议解决方式",
    )
    raw_fields_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="原始字段 JSON(LLM 输出)",
    )
    extract_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="提取置信度 0-1",
    )
