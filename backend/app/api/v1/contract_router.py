"""合同文档 API 路由

提供合同文档的上传、查询、解析、字段提取、下载等功能。
"""

import hashlib

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_parser_service, verify_api_key
from app.common.response import ApiResponse
from app.common.snowflake import generate_id
from app.infrastructure.minio_client import minio_client
from app.models.contract_document import ContractDocument
from app.repositories.contract_document_repo import ContractDocumentRepository
from app.repositories.contract_field_repo import ContractFieldRepository
from app.services.parser.parser_service import DocumentParserService
from app.workflow.contract_review_workflow import contract_review_workflow

router = APIRouter(prefix="/contracts")

# 支持上传的文件类型
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png", ".tiff"}
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB


# ==================== 响应模型 ====================

class DocumentResponse(BaseModel):
    """合同文档响应"""
    doc_id: str
    file_name: str
    file_type: str
    file_md5: str | None
    file_size: int | None
    parse_status: str
    is_scanned: bool
    is_duplicate: bool
    created_at: str | None


class ParseStatusResponse(BaseModel):
    """解析状态响应"""
    doc_id: str
    file_name: str
    parse_status: str
    file_type: str
    is_scanned: bool
    has_text: bool
    text_length: int


# ==================== 路由 ====================

@router.post(
    "/upload",
    summary="上传合同文档",
    description="上传合同文件（PDF/Word/图片），自动存储到 MinIO 并创建数据库记录。",
)
async def upload_contract(
    file: UploadFile = File(..., description="合同文件"),
    approval_order_id: str = "0",
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_api_key),
):
    """上传合同文档

    1. 校验文件类型和大小
    2. 计算 MD5 去重
    3. 上传到 MinIO
    4. 创建数据库记录
    """
    # 校验文件名
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    # 校验文件类型
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    ext = f".{ext}" if ext else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {ext}，支持: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # 读取文件内容
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超出限制（最大 {MAX_UPLOAD_SIZE // 1024 // 1024}MB）",
        )

    # 计算 MD5 去重
    file_md5 = hashlib.md5(content).hexdigest()

    repo = ContractDocumentRepository(db)
    existing = await repo.get_by_md5(file_md5)
    if existing:
        # 如果旧记录的 approval_order_id=0，为其创建审批单
        actual_ao_id = existing.approval_order_id
        if actual_ao_id == 0:
            from app.models.approval_order import ApprovalOrder
            from app.repositories.approval_order_repo import ApprovalOrderRepository
            order_repo = ApprovalOrderRepository(db)
            order = ApprovalOrder(
                id=generate_id(),
                approval_id=f"UPLOAD_{existing.doc_id}",
                title=existing.file_name,
                status="reviewing",
                applicant="",
                department="",
            )
            await order_repo.create(order)
            existing.approval_order_id = order.id
            await repo.update(existing)
            await db.commit()
            actual_ao_id = order.id

        return ApiResponse.success(
            data={
                "doc_id": existing.doc_id,
                "file_name": existing.file_name,
                "file_type": existing.file_type,
                "file_md5": existing.file_md5,
                "file_size": existing.file_size,
                "is_duplicate": True,
                "approval_order_id": actual_ao_id,
            },
            message="文件已存在，跳过上传",
        )

    # 生成 doc_id 和 MinIO 路径
    doc_id = f"DOC_{generate_id()}"
    minio_path = f"contracts/{doc_id}/{file.filename}"

    # 检测文件类型
    file_type = _detect_file_type(file.filename)

    # 上传到 MinIO
    await minio_client.upload(
        object_name=minio_path,
        data=content,
        content_type=file.content_type or "application/octet-stream",
    )

    # 获取或创建审批单（上传合同时自动创建审批单记录，保证审批单列表有数据）
    actual_approval_order_id = int(approval_order_id) if approval_order_id.isdigit() else 0
    if actual_approval_order_id == 0:
        from app.models.approval_order import ApprovalOrder
        from app.repositories.approval_order_repo import ApprovalOrderRepository

        order_repo = ApprovalOrderRepository(db)
        order = ApprovalOrder(
            id=generate_id(),
            approval_id=f"UPLOAD_{doc_id}",
            title=file.filename,
            status="reviewing",
            applicant="",
            department="",
        )
        await order_repo.create(order)
        actual_approval_order_id = order.id

    # 创建数据库记录
    doc = ContractDocument(
        id=generate_id(),
        doc_id=doc_id,
        approval_order_id=actual_approval_order_id,
        file_name=file.filename,
        file_md5=file_md5,
        minio_path=minio_path,
        file_type=file_type,
        file_size=len(content),
        is_scanned=False,
        parse_status="pending",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    return ApiResponse.success(
        data={
            "doc_id": doc.doc_id,
            "file_name": doc.file_name,
            "file_type": doc.file_type,
            "file_md5": doc.file_md5,
            "file_size": doc.file_size,
            "is_duplicate": False,
            "approval_order_id": actual_approval_order_id,
        },
        message="上传成功",
    )


@router.get(
    "/",
    summary="合同文档列表",
    description="分页查询合同文档列表，支持关键词搜索。",
)
async def list_documents(
    page: int = 1,
    page_size: int = 20,
    keyword: str = "",
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_api_key),
):
    """查询合同文档列表"""
    repo = ContractDocumentRepository(db)
    result = await repo.paginate(
        page=page,
        page_size=page_size,
    )
    items = [
        {
            "doc_id": d.doc_id,
            "file_name": d.file_name,
            "file_type": d.file_type,
            "file_md5": d.file_md5,
            "file_size": d.file_size,
            "parse_status": d.parse_status,
            "is_scanned": d.is_scanned,
            "created_at": str(d.created_at) if d.created_at else None,
        }
        for d in result.items
    ]
    return ApiResponse.success(
        data={
            "items": items,
            "total": result.page_info.total,
            "page": result.page_info.page,
            "page_size": result.page_info.page_size,
            "total_pages": result.page_info.total_pages,
        }
    )


@router.get(
    "/{doc_id}",
    summary="查询合同文档",
    description="查询指定合同文档的详细信息。",
)
async def get_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_api_key),
):
    """查询合同文档"""
    from app.repositories.contract_document_repo import ContractDocumentRepository

    repo = ContractDocumentRepository(db)
    doc = await repo.get_by_doc_id(doc_id)

    if not doc:
        raise HTTPException(status_code=404, detail=f"文档 {doc_id} 不存在")

    return ApiResponse.success(
        data={
            "doc_id": doc.doc_id,
            "file_name": doc.file_name,
            "file_type": doc.file_type,
            "file_md5": doc.file_md5,
            "file_size": doc.file_size,
            "parse_status": doc.parse_status,
            "is_scanned": doc.is_scanned,
            "approval_order_id": doc.approval_order_id,
            "created_at": str(doc.created_at) if doc.created_at else None,
        }
    )


@router.post(
    "/{doc_id}/parse",
    summary="解析合同文档",
    description="触发合同文档的解析（电子PDF→MinerU，扫描件→PaddleOCR）。",
)
async def parse_document(
    doc_id: str,
    service: DocumentParserService = Depends(get_parser_service),
    _auth: str = Depends(verify_api_key),
):
    """解析合同文档"""
    try:
        await service.parse_document(doc_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析失败: {e}") from e

    status = await service.get_parse_status(doc_id)
    return ApiResponse.success(data=status)


@router.get(
    "/{doc_id}/parse-status",
    summary="查询解析状态",
    description="查询指定文档的解析状态。",
)
async def get_parse_status(
    doc_id: str,
    service: DocumentParserService = Depends(get_parser_service),
    _auth: str = Depends(verify_api_key),
):
    """查询文档解析状态"""
    try:
        status = await service.get_parse_status(doc_id)
        return ApiResponse.success(data=status)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post(
    "/{doc_id}/extract-fields",
    summary="提取合同字段",
    description="从已解析的合同文本中提取关键字段（调用LLM）。",
)
async def extract_fields(
    doc_id: str,
    service: DocumentParserService = Depends(get_parser_service),
    _auth: str = Depends(verify_api_key),
):
    """提取合同字段"""
    try:
        fields = await service.extract_fields(doc_id)
        return ApiResponse.success(
            data={
                "status": "extracted",
                "contract_no": fields.contract_no,
                "party_a_info": fields.party_a_info,
                "party_b_info": fields.party_b_info,
                "amount": fields.amount,
                "start_date": fields.start_date,
                "end_date": fields.end_date,
                "payment_terms": fields.payment_terms,
                "liability_clause": fields.liability_clause,
                "extract_confidence": fields.extract_confidence,
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"字段提取失败: {e}") from e


@router.get(
    "/{doc_id}/fields",
    summary="查询合同字段",
    description="查询合同文档已经提取出的字段结果。",
)
async def get_contract_fields(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_api_key),
):
    doc_repo = ContractDocumentRepository(db)
    field_repo = ContractFieldRepository(db)

    doc = await doc_repo.get_by_doc_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"文档 {doc_id} 不存在")

    fields = await field_repo.get_by_document_id(doc.id)
    if not fields:
        return ApiResponse.success(data=[], message="暂无字段数据")

    confidence = fields.extract_confidence or 0.0
    field_items = [
        {"field_name": "contract_no", "field_label": "合同编号", "value": fields.contract_no, "confidence": confidence, "source": "llm"},
        {"field_name": "party_a_info", "field_label": "甲方信息", "value": fields.party_a_info, "confidence": confidence, "source": "llm"},
        {"field_name": "party_b_info", "field_label": "乙方信息", "value": fields.party_b_info, "confidence": confidence, "source": "llm"},
        {"field_name": "amount", "field_label": "合同金额", "value": fields.amount, "confidence": confidence, "source": "llm"},
        {"field_name": "start_date", "field_label": "开始日期", "value": str(fields.start_date) if fields.start_date else None, "confidence": confidence, "source": "llm"},
        {"field_name": "end_date", "field_label": "结束日期", "value": str(fields.end_date) if fields.end_date else None, "confidence": confidence, "source": "llm"},
        {"field_name": "payment_terms", "field_label": "付款条款", "value": fields.payment_terms, "confidence": confidence, "source": "llm"},
        {"field_name": "liability_clause", "field_label": "违约责任", "value": fields.liability_clause, "confidence": confidence, "source": "llm"},
        {"field_name": "confidentiality", "field_label": "保密条款", "value": fields.confidentiality, "confidence": confidence, "source": "llm"},
        {"field_name": "dispute_resolution", "field_label": "争议解决", "value": fields.dispute_resolution, "confidence": confidence, "source": "llm"},
    ]
    return ApiResponse.success(
        data=[item for item in field_items if item["value"] not in (None, "")],
        message="查询成功",
    )


@router.post(
    "/{doc_id}/review",
    summary="发起合同审查",
    description="直接从已上传的合同文档发起审查（字段提取 + 风险审查 + 生成报告），无需 OA 审批单。",
)
async def review_contract(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_api_key),
):
    """发起合同审查

    1. 验证文档存在且已解析
    2. 创建审查任务并执行审查（由 workflow 内部管理数据库事务）
    """
    repo = ContractDocumentRepository(db)
    doc = await repo.get_by_doc_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"文档 {doc_id} 不存在")
    if doc.parse_status != "parsed":
        raise HTTPException(
            status_code=400,
            detail=f"文档尚未解析完成，当前状态: {doc.parse_status}。请先执行解析。",
        )

    task_id = f"TASK_{generate_id()}"

    # 执行直接审查（workflow 内部独立管理 DB 事务，避免锁竞争）
    try:
        result = await contract_review_workflow.run_direct_review(task_id, doc_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"审查失败: {e}") from e

    return ApiResponse.success(
        data={
            "task_id": task_id,
            "status": result.get("status"),
            "risk_count": result.get("risk_count", 0),
            "risk_level": result.get("risk_level", "NONE"),
            "has_risks": result.get("has_risks", False),
        },
        message=f"审查完成 | 风险数: {result.get('risk_count', 0)} | 等级: {result.get('risk_level', 'NONE')}",
    )


@router.delete(
    "/{doc_id}",
    summary="删除合同文档",
    description="删除指定合同文档及其 MinIO 文件。",
)
async def delete_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_api_key),
):
    """删除合同文档"""
    from loguru import logger

    repo = ContractDocumentRepository(db)
    doc = await repo.get_by_doc_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"文档 {doc_id} 不存在")

    # 删除 MinIO 文件
    try:
        await minio_client.delete(doc.minio_path)
    except Exception as e:
        logger.warning(f"MinIO 文件删除失败（可能已不存在）| path={doc.minio_path} | error={e}")

    # 删除数据库记录
    await db.delete(doc)
    await db.commit()

    return ApiResponse.success(
        data={"doc_id": doc_id, "deleted": True},
        message="文档已删除",
    )


@router.get(
    "/{doc_id}/download-url",
    summary="获取文档下载链接",
    description="获取合同文档的预签名下载 URL（有效期1小时）。",
)
async def get_download_url(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_api_key),
):
    """获取文档下载链接"""
    from app.repositories.contract_document_repo import ContractDocumentRepository

    repo = ContractDocumentRepository(db)
    doc = await repo.get_by_doc_id(doc_id)

    if not doc:
        raise HTTPException(status_code=404, detail=f"文档 {doc_id} 不存在")

    from app.infrastructure.minio_client import minio_client

    url = minio_client.get_presigned_url(doc.minio_path, expires=3600)
    return ApiResponse.success(
        data={"doc_id": doc_id, "download_url": url, "expires_in": 3600}
    )


# ==================== 工具函数 ====================

def _detect_file_type(file_name: str) -> str:
    """根据文件扩展名检测文件类型"""
    ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    if ext in ("pdf",):
        return "pdf"
    if ext in ("doc", "docx"):
        return "word"
    if ext in ("jpg", "jpeg", "png", "tiff", "tif", "bmp"):
        return "image"
    return "other"
