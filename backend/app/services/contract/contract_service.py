"""合同文档服务 - 负责合同附件下载、MD5 去重、MinIO 存储"""

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.oa_client import oa_client
from app.common.snowflake import generate_id
from app.models.contract_document import ContractDocument
from app.repositories.contract_document_repo import ContractDocumentRepository
from app.utils.helpers import calculate_md5


class ContractService:
    """合同文档领域服务"""

    # 支持的文件类型
    SUPPORTED_EXTENSIONS = {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png", ".tiff"}

    def __init__(self, db: AsyncSession):
        self.db = db
        self.doc_repo = ContractDocumentRepository(db)

    # ==================== 附件下载与存储 ====================

    async def download_and_store(
        self,
        attachment_url: str,
        file_name: str,
        approval_order_id: int,
    ) -> ContractDocument | None:
        """从 OA 下载合同附件，MD5 去重后存入 MinIO"""
        # 1. 从 OA 下载附件
        content = await oa_client.download_attachment(attachment_url)
        if content is None:
            logger.error(f"合同附件下载失败 | url={attachment_url}")
            return None

        # 2. 计算 MD5，用于去重
        file_md5 = calculate_md5(content)

        # 3. 检查是否已存在相同文件（MD5 去重）
        existing = await self.doc_repo.get_by_md5(file_md5)
        if existing:
            logger.info(f"合同附件已存在(跳过上传) | md5={file_md5} | existing_path={existing.minio_path}")
            return existing

        # 4. 确定文件类型
        file_type = self._detect_file_type(file_name)

        # 5. 生成 MinIO 存储路径
        minio_path = self._generate_minio_path(approval_order_id, file_md5, file_name)

        # 6. 上传到 MinIO
        content_type = self._get_content_type(file_type)
        from app.infrastructure.minio_client import minio_client

        await minio_client.upload(minio_path, content, content_type)

        # 7. 创建本地数据库记录
        doc = await self.doc_repo.create(
            ContractDocument(
                id=generate_id(),
                doc_id=f"DOC_{generate_id()}",
                approval_order_id=approval_order_id,
                file_name=file_name,
                file_md5=file_md5,
                minio_path=minio_path,
                file_type=file_type,
                file_size=len(content),
                is_scanned=self._is_scanned_file(file_type),
            )
        )
        logger.info(f"合同附件存储完成 | file={file_name} | md5={file_md5} | minio={minio_path}")
        return doc

    async def download_file(self, doc_id: str) -> tuple[bytes, str, str] | None:
        """从 MinIO 下载合同文件内容"""
        doc = await self.doc_repo.get_by_doc_id(doc_id)
        if not doc:
            logger.warning(f"合同文档不存在 | doc_id={doc_id}")
            return None

        from app.infrastructure.minio_client import minio_client

        content = await minio_client.download(doc.minio_path)
        if content is None:
            logger.error(f"MinIO 文件下载失败 | path={doc.minio_path}")
            return None

        content_type = self._get_content_type(doc.file_type)
        return content, doc.file_name, content_type

    async def download_attachment(self, approval_order_id: int) -> dict | None:
        """根据审批单下载首个合同附件并入库，供工作流异步审查使用。"""
        from app.repositories.approval_order_repo import ApprovalOrderRepository

        order_repo = ApprovalOrderRepository(self.db)
        order = await order_repo.get_by_id(approval_order_id)
        if not order:
            logger.warning(f"审批单不存在，无法下载附件 | approval_order_id={approval_order_id}")
            return None

        oa_data = {}
        if order.raw_data:
            try:
                import ast

                oa_data = ast.literal_eval(order.raw_data)
            except Exception:
                logger.warning(f"审批单 raw_data 解析失败 | approval_order_id={approval_order_id}")

        attachments = oa_data.get("attachments") or []
        if not attachments:
            logger.warning(f"审批单无合同附件 | approval_order_id={approval_order_id}")
            return None

        attachment = attachments[0]
        attachment_url = attachment.get("attachment_url") or attachment.get("url") or attachment.get("file_url")
        file_name = attachment.get("file_name") or attachment.get("name") or "合同附件.pdf"
        if not attachment_url:
            logger.warning(f"审批单附件缺少下载地址 | approval_order_id={approval_order_id}")
            return None

        doc = await self.download_and_store(attachment_url, file_name, approval_order_id)
        if not doc:
            return None

        return {
            "doc_id": doc.doc_id,
            "file_md5": doc.file_md5,
            "minio_path": doc.minio_path,
            "exists": True,
        }

    # ==================== 查询方法 ====================

    async def get_documents_by_approval(self, approval_order_id: int) -> list[ContractDocument]:
        """获取审批单关联的所有合同文档"""
        return await self.doc_repo.list_by_approval_order(approval_order_id)

    async def get_by_doc_id(self, doc_id: str) -> ContractDocument | None:
        """按文档业务 ID 查询"""
        return await self.doc_repo.get_by_doc_id(doc_id)

    # ==================== 工具方法 ====================

    @staticmethod
    def _detect_file_type(file_name: str) -> str:
        """根据扩展名检测文件类型"""
        ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
        type_map = {
            "pdf": "pdf",
            "doc": "docx",
            "docx": "docx",
            "jpg": "image",
            "jpeg": "image",
            "png": "image",
            "tiff": "image",
        }
        return type_map.get(ext, "unknown")

    @staticmethod
    def _is_scanned_file(file_type: str) -> bool:
        """判断是否为扫描件（图片类型）"""
        return file_type == "image"

    @staticmethod
    def _get_content_type(file_type: str) -> str:
        """获取对应的 HTTP Content-Type"""
        type_map = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "image": "image/png",
        }
        return type_map.get(file_type, "application/octet-stream")

    @staticmethod
    def _generate_minio_path(approval_order_id: int, file_md5: str, file_name: str) -> str:
        """生成 MinIO 存储路径：contracts/{年月}/{审批单ID}/{MD5}_{文件名}"""
        from datetime import datetime

        year_month = datetime.now().strftime("%Y%m")
        # 保留原始扩展名
        ext = file_name.rsplit(".", 1)[-1] if "." in file_name else "bin"
        return f"contracts/{year_month}/{approval_order_id}/{file_md5}.{ext}"


# ==================== 合同服务工厂 ====================

def get_contract_service(db: AsyncSession) -> ContractService:
    """获取合同服务实例（FastAPI 依赖注入用）"""
    return ContractService(db)
