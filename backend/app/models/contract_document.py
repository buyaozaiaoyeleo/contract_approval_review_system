"""合同文档表 (t_contract_document)"""


from sqlalchemy import BigInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SnowflakePKMixin, TimestampMixin


class ContractDocument(Base, SnowflakePKMixin, TimestampMixin):
    __tablename__ = "t_contract_document"

    doc_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        comment="文档业务 ID",
    )
    approval_order_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
        comment="关联审批单 ID",
    )
    file_name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        default="",
        comment="原始文件名",
    )
    file_md5: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="",
        index=True,
        comment="文件 MD5 值",
    )
    minio_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        default="",
        comment="MinIO 存储路径",
    )
    file_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="",
        comment="文件类型: pdf/word/image",
    )
    is_scanned: Mapped[bool] = mapped_column(
        default=False,
        comment="是否为扫描件",
    )
    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        comment="文件大小(字节)",
    )
    parse_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        index=True,
        comment="解析状态: pending/parsing/parsed/failed",
    )
    parse_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="解析出来的文本内容",
    )
