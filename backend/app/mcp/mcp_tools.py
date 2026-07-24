"""MCP 工具注册

将合同审查系统的核心能力注册为 MCP Tools，供外部 AI Agent 调用。
每个 Tool 包含：
- 参数校验（Pydantic 模型）
- 业务逻辑调用
- 结构化结果返回
"""


from loguru import logger
from pydantic import BaseModel, Field

from app.core.database import async_session_factory
from app.mcp.mcp_server import mcp
from app.services.approval.approval_service import ApprovalService
from app.services.parser.parser_service import DocumentParserService
from app.services.risk.risk_service import RiskReviewService
from app.workflow.contract_review_workflow import contract_review_workflow

# ==================== 工具1: 合同审查（完整流程） ====================

class ContractReviewInput(BaseModel):
    """合同审查工具输入参数"""
    approval_order_id: int = Field(..., description="OA 审批单 ID", ge=1)
    async_mode: bool = Field(default=False, description="是否异步执行（不等待结果）")


@mcp.tool(
    name="contract_review",
    description="对指定审批单的合同进行完整自动化审查。"
    "流程：拉取审批单 → 下载合同 → 解析文档 → 提取字段 → 风险审查 → 回写评论。"
    "返回审查结果，包括风险等级、风险项列表、综合评分。",
)
async def contract_review_tool(params: ContractReviewInput) -> dict:
    """合同审查工具 - 完整审查流程"""
    logger.info(f"[MCP Tool] contract_review | approval_order_id={params.approval_order_id}")

    async with async_session_factory() as db:
        task_id = await contract_review_workflow.create_task(db, params.approval_order_id)

    if params.async_mode:
        await contract_review_workflow.run_background(task_id, params.approval_order_id)
        return {
            "status": "started",
            "task_id": task_id,
            "message": f"审查任务已启动，task_id={task_id}，请稍后查询结果",
        }

    result = await contract_review_workflow.run(task_id, params.approval_order_id)
    return result


# ==================== 工具2: 查询审批单信息 ====================

class QueryApprovalInput(BaseModel):
    """查询审批单输入参数"""
    approval_order_id: int = Field(..., description="OA 审批单 ID", ge=1)


@mcp.tool(
    name="query_approval",
    description="查询审批单的详细信息，包括审批状态、合同附件列表、历史评论。",
)
async def query_approval_tool(params: QueryApprovalInput) -> dict:
    """查询审批单信息"""
    logger.info(f"[MCP Tool] query_approval | approval_order_id={params.approval_order_id}")

    async with async_session_factory() as db:
        approval_service = ApprovalService(db)
        approval = await approval_service.get_approval(params.approval_order_id)

        if not approval:
            return {"status": "not_found", "message": f"审批单 {params.approval_order_id} 不存在"}

        docs = await approval_service.get_documents(params.approval_order_id)
        comments = await approval_service.get_comments(params.approval_order_id)

        return {
            "status": "found",
            "approval": {
                "approval_order_id": approval.id,
                "title": approval.title,
                "status": approval.status,
                "applicant": approval.applicant,
                "created_at": str(approval.created_at) if approval.created_at else None,
            },
            "documents": [
                {
                    "doc_id": d.doc_id,
                    "file_name": d.file_name,
                    "file_type": d.file_type,
                    "parse_status": d.parse_status,
                }
                for d in docs
            ],
            "comment_count": len(comments),
        }


# ==================== 工具3: 查询风险报告 ====================

class QueryRiskReportInput(BaseModel):
    """查询风险报告输入参数"""
    approval_order_id: int = Field(..., description="OA 审批单 ID", ge=1)


@mcp.tool(
    name="query_risk_report",
    description="查询指定审批单的风险审查报告，包含风险等级、风险项列表、修改建议。",
)
async def query_risk_report_tool(params: QueryRiskReportInput) -> dict:
    """查询风险审查报告"""
    logger.info(f"[MCP Tool] query_risk_report | approval_order_id={params.approval_order_id}")

    async with async_session_factory() as db:
        risk_service = RiskReviewService(db)
        results = await risk_service.get_results_by_approval(params.approval_order_id)

        if not results:
            return {"status": "no_risks", "message": "未找到审查结果，请先执行 contract_review"}

        high_risks = [r for r in results if r.risk_level == "HIGH"]
        medium_risks = [r for r in results if r.risk_level == "MEDIUM"]
        low_risks = [r for r in results if r.risk_level == "LOW"]

        return {
            "status": "found",
            "approval_order_id": params.approval_order_id,
            "summary": {
                "total": len(results),
                "high": len(high_risks),
                "medium": len(medium_risks),
                "low": len(low_risks),
            },
            "risks": [
                {
                    "risk_id": r.risk_id,
                    "risk_level": r.risk_level,
                    "risk_description": r.risk_description,
                    "suggestion": r.suggestion,
                    "source_text": r.source_text,
                    "field_name": r.field_name,
                }
                for r in results
            ],
        }


# ==================== 工具4: 查询合同字段 ====================

class QueryFieldsInput(BaseModel):
    """查询合同字段输入参数"""
    approval_order_id: int = Field(..., description="OA 审批单 ID", ge=1)


@mcp.tool(
    name="query_contract_fields",
    description="查询指定审批单关联合同的提取字段，包括合同编号、金额、甲乙方信息、关键条款。",
)
async def query_contract_fields_tool(params: QueryFieldsInput) -> dict:
    """查询合同提取字段"""
    logger.info(f"[MCP Tool] query_contract_fields | approval_order_id={params.approval_order_id}")

    from app.repositories.contract_document_repo import ContractDocumentRepository
    from app.repositories.contract_field_repo import ContractFieldRepository

    async with async_session_factory() as db:
        doc_repo = ContractDocumentRepository(db)
        field_repo = ContractFieldRepository(db)

        docs = await doc_repo.list_by_approval_order(params.approval_order_id)
        if not docs:
            return {"status": "no_documents", "message": "未找到合同文档"}

        fields_list = []
        for doc in docs:
            field = await field_repo.get_by_document_id(doc.id)
            if field:
                fields_list.append({
                    "doc_id": doc.doc_id,
                    "contract_no": field.contract_no,
                    "party_a_info": field.party_a_info,
                    "party_b_info": field.party_b_info,
                    "amount": field.amount,
                    "start_date": field.start_date,
                    "end_date": field.end_date,
                    "payment_terms": field.payment_terms,
                    "extract_confidence": field.extract_confidence,
                })

        return {
            "status": "found",
            "approval_order_id": params.approval_order_id,
            "document_count": len(docs),
            "fields": fields_list,
        }


# ==================== 工具5: 重试失败任务 ====================

class RetryTaskInput(BaseModel):
    """重试任务输入参数"""
    task_id: str = Field(..., description="任务 ID", min_length=1)


@mcp.tool(
    name="retry_task",
    description="重试失败或阻塞的审查任务。",
)
async def retry_task_tool(params: RetryTaskInput) -> dict:
    """重试审查任务"""
    logger.info(f"[MCP Tool] retry_task | task_id={params.task_id}")

    try:
        result = await contract_review_workflow.resume(params.task_id)
        return {"status": "resumed", "task_id": params.task_id, "result": result}
    except Exception as e:
        logger.error(f"重试任务失败 | task_id={params.task_id} | error={e}")
        return {"status": "error", "task_id": params.task_id, "error": str(e)}


# ==================== 工具6: 查询任务状态 ====================

class QueryTaskInput(BaseModel):
    """查询任务状态输入参数"""
    task_id: str = Field(..., description="任务 ID", min_length=1)


@mcp.tool(
    name="query_task_status",
    description="查询指定审查任务的执行状态和进度。",
)
async def query_task_status_tool(params: QueryTaskInput) -> dict:
    """查询任务状态"""
    logger.info(f"[MCP Tool] query_task_status | task_id={params.task_id}")

    from app.repositories.workflow_task_repo import WorkflowTaskRepository

    async with async_session_factory() as db:
        task_repo = WorkflowTaskRepository(db)
        task = await task_repo.get_by_task_id(params.task_id)

        if not task:
            return {"status": "not_found", "task_id": params.task_id}

        return {
            "status": "found",
            "task_id": task.task_id,
            "task_status": task.status,
            "current_node": task.current_node,
            "retry_count": task.retry_count,
            "error_message": task.error_message,
            "started_at": str(task.started_at) if task.started_at else None,
            "completed_at": str(task.completed_at) if task.completed_at else None,
            "duration_ms": task.duration_ms,
        }


# ==================== 工具7: 同步审批单 ====================

class SyncApprovalInput(BaseModel):
    """同步审批单输入参数"""
    approval_order_id: int = Field(..., description="OA 审批单 ID", ge=1)


@mcp.tool(
    name="sync_approval",
    description="从 OA 系统同步审批单数据到本地。",
)
async def sync_approval_tool(params: SyncApprovalInput) -> dict:
    """同步审批单"""
    logger.info(f"[MCP Tool] sync_approval | approval_order_id={params.approval_order_id}")

    async with async_session_factory() as db:
        approval_service = ApprovalService(db)
        try:
            approval = await approval_service.sync_approval(params.approval_order_id)
            return {
                "status": "synced",
                "approval_order_id": approval.id,
                "title": approval.title,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}


# ==================== 工具8: 获取文档解析状态 ====================

class QueryDocParseInput(BaseModel):
    """查询文档解析状态输入参数"""
    doc_id: str = Field(..., description="文档业务 ID", min_length=1)


@mcp.tool(
    name="query_doc_parse_status",
    description="查询指定文档的解析状态和提取的文本内容。",
)
async def query_doc_parse_status_tool(params: QueryDocParseInput) -> dict:
    """查询文档解析状态"""
    logger.info(f"[MCP Tool] query_doc_parse_status | doc_id={params.doc_id}")

    async with async_session_factory() as db:
        parser_service = DocumentParserService(db)
        try:
            status = await parser_service.get_parse_status(params.doc_id)
            return {"status": "found", **status}
        except ValueError as e:
            return {"status": "not_found", "message": str(e)}


# ==================== 提示模板 ====================

@mcp.prompt(
    name="review_contract",
    description="生成合同审查的提示模板",
)
async def review_contract_prompt(approval_order_id: int) -> str:
    """生成合同审查提示"""
    return f"""请对审批单 {approval_order_id} 的合同进行审查。

步骤：
1. 使用 contract_review 工具启动审查
2. 使用 query_risk_report 查看风险结果
3. 根据风险等级给出建议

高风险项需要重点关注，中风险项建议复核。
"""
