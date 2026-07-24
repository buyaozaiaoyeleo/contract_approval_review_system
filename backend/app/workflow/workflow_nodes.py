"""合同审查工作流节点

每个节点是一个独立的业务步骤，接收 WorkflowState 并返回部分更新。
LangGraph 自动合并节点返回的 dict 到主状态中。

节点执行顺序：
  pull_approval → download_contract → parse_document → extract_fields → review_risks → write_comment
"""

from datetime import datetime

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.approval.approval_service import ApprovalService
from app.services.contract.contract_service import ContractService
from app.services.parser.parser_service import DocumentParserService
from app.services.risk.risk_service import RiskReviewService
from app.workflow.workflow_state import WorkflowState

# ==================== 节点1: 拉取审批单 ====================

async def pull_approval_node(state: WorkflowState, db: AsyncSession) -> dict:
    """拉取 OA 审批单并同步到本地数据库

    优先从 OA 同步；OA 不可用时降级为查本地数据库。
    返回: {"approval_data": ..., "approval_exists": True/False, "approval_status": ...}
    """
    logger.info(f"[节点1] 拉取审批单 | task_id={state['task_id']} | approval_order_id={state['approval_order_id']}")

    approval_service = ApprovalService(db)
    try:
        approval = await approval_service.sync_approval(state["approval_order_id"])
        return {
            "approval_data": approval.__dict__ if hasattr(approval, "__dict__") else {},
            "approval_exists": True,
            "approval_status": getattr(approval, "status", "unknown"),
            "current_node": "pull_approval",
            "node_statuses": {"pull_approval": "completed"},
        }
    except Exception as e:
        logger.warning(f"OA 拉取失败，尝试本地降级 | error={e}")

    # OA 不可用，降级为查询本地审批单
    local_order = await approval_service.get_approval(state["approval_order_id"])
    if local_order:
        logger.info(f"本地审批单已存在，跳过 OA 拉取 | approval_order_id={state['approval_order_id']}")
        return {
            "approval_data": local_order.__dict__ if hasattr(local_order, "__dict__") else {},
            "approval_exists": True,
            "approval_status": getattr(local_order, "status", "unknown"),
            "current_node": "pull_approval",
            "node_statuses": {"pull_approval": "completed"},
        }

    return {
        "approval_exists": False,
        "approval_status": "error",
        "error_message": f"OA 同步失败且本地审批单 {state['approval_order_id']} 不存在",
        "error_type": "ValueError",
        "current_node": "pull_approval",
        "node_statuses": {"pull_approval": "failed"},
        "failed_node": "pull_approval",
    }


# ==================== 节点2: 下载合同附件 ====================

async def download_contract_node(state: WorkflowState, db: AsyncSession) -> dict:
    """从 OA 下载合同附件，MD5 去重后存入 MinIO

    返回: {"doc_id": ..., "file_md5": ..., "minio_path": ..., "doc_exists": ...}
    """
    logger.info(f"[节点2] 下载合同附件 | task_id={state['task_id']}")

    contract_service = ContractService(db)
    try:
        attachment = await contract_service.download_attachment(state["approval_order_id"])
        if attachment is None:
            return {
                "doc_exists": False,
                "error_message": "审批单无合同附件",
                "error_type": "NoAttachmentError",
                "current_node": "download_contract",
                "node_statuses": {"download_contract": "failed"},
                "failed_node": "download_contract",
            }

        return {
            "doc_id": attachment.get("doc_id"),
            "file_md5": attachment.get("file_md5"),
            "minio_path": attachment.get("minio_path"),
            "doc_exists": attachment.get("exists", False),
            "current_node": "download_contract",
            "node_statuses": {"download_contract": "completed"},
        }
    except Exception as e:
        logger.error(f"下载合同附件失败 | error={e}")
        return {
            "doc_exists": False,
            "error_message": str(e),
            "error_type": type(e).__name__,
            "current_node": "download_contract",
            "node_statuses": {"download_contract": "failed"},
            "failed_node": "download_contract",
        }


# ==================== 节点3: 解析文档 ====================

async def parse_document_node(state: WorkflowState, db: AsyncSession) -> dict:
    """解析合同文档（电子 PDF → MinerU，扫描件 → PaddleOCR）

    返回: {"parse_text": ..., "parse_status": ..., "page_count": ..., "is_scanned": ...}
    """
    logger.info(f"[节点3] 解析文档 | task_id={state['task_id']} | doc_id={state.get('doc_id')}")

    parser_service = DocumentParserService(db)
    try:
        doc_id = state.get("doc_id")
        if not doc_id:
            return {
                "parse_status": "failed",
                "error_message": "缺少 doc_id，无法解析",
                "error_type": "MissingDocIdError",
                "current_node": "parse_document",
                "node_statuses": {"parse_document": "failed"},
                "failed_node": "parse_document",
            }

        # 如果文档已存在（去重命中），跳过解析
        if state.get("doc_exists") and state.get("parse_text"):
            return {
                "parse_status": "parsed",
                "parse_text": state["parse_text"],
                "current_node": "parse_document",
                "node_statuses": {"parse_document": "completed"},
            }

        parsed = await parser_service.parse_document(doc_id)
        if not isinstance(parsed, dict):
            raise RuntimeError(f"parse_document 返回类型异常: {type(parsed).__name__}")
        return {
            "parse_text": parsed.get("full_text", ""),
            "parse_status": "parsed",
            "page_count": parsed.get("page_count", 0),
            "is_scanned": parsed.get("is_scanned", False),
            "current_node": "parse_document",
            "node_statuses": {"parse_document": "completed"},
        }
    except Exception as e:
        logger.error(f"文档解析失败 | error={e}")
        return {
            "parse_status": "failed",
            "error_message": str(e),
            "error_type": type(e).__name__,
            "current_node": "parse_document",
            "node_statuses": {"parse_document": "failed"},
            "failed_node": "parse_document",
        }


# ==================== 节点4: 提取合同字段 ====================

async def extract_fields_node(state: WorkflowState, db: AsyncSession) -> dict:
    """从解析文本中提取合同关键字段（调用 LLM）

    返回: {"contract_no": ..., "amount": ..., "field_extracted": True, ...}
    """
    logger.info(f"[节点4] 提取合同字段 | task_id={state['task_id']}")

    parser_service = DocumentParserService(db)
    try:
        doc_id = state.get("doc_id")
        parse_text = state.get("parse_text", "")

        if not doc_id or not parse_text:
            return {
                "field_extracted": False,
                "error_message": "缺少解析文本，无法提取字段",
                "error_type": "MissingParseTextError",
                "current_node": "extract_fields",
                "node_statuses": {"extract_fields": "failed"},
                "failed_node": "extract_fields",
            }

        fields = await parser_service.extract_fields(doc_id, parse_text)

        return {
            "contract_no": fields.contract_no,
            "party_a_info": fields.party_a_info,
            "party_b_info": fields.party_b_info,
            "amount": fields.amount,
            "start_date": fields.start_date,
            "end_date": fields.end_date,
            "payment_terms": fields.payment_terms,
            "liability_clause": fields.liability_clause,
            "extract_confidence": fields.extract_confidence or 0.0,
            "field_extracted": True,
            "current_node": "extract_fields",
            "node_statuses": {"extract_fields": "completed"},
        }
    except Exception as e:
        logger.error(f"字段提取失败 | error={e}")
        return {
            "field_extracted": False,
            "error_message": str(e),
            "error_type": type(e).__name__,
            "current_node": "extract_fields",
            "node_statuses": {"extract_fields": "failed"},
            "failed_node": "extract_fields",
        }


# ==================== 节点5: 风险审查 ====================

async def review_risks_node(state: WorkflowState, db: AsyncSession) -> dict:
    """执行风险审查（规则匹配 + LLM 语义审查）

    返回: {"risk_results": [...], "risk_score": {...}, "has_risks": True/False}
    """
    logger.info(f"[节点5] 风险审查 | task_id={state['task_id']}")

    risk_service = RiskReviewService(db)
    try:
        approval_order_id = state["approval_order_id"]
        review_result = await risk_service.review_approval(approval_order_id)

        results = review_result.get("results", [])
        score = review_result.get("score", {})

        has_risks = len(results) > 0

        return {
            "risk_results": results,
            "risk_score": score,
            "risk_count": len(results),
            "has_risks": has_risks,
            "current_node": "review_risks",
            "node_statuses": {"review_risks": "completed"},
        }
    except Exception as e:
        logger.error(f"风险审查失败 | error={e}")
        return {
            "risk_results": [],
            "risk_score": {},
            "risk_count": 0,
            "has_risks": False,
            "error_message": str(e),
            "error_type": type(e).__name__,
            "current_node": "review_risks",
            "node_statuses": {"review_risks": "failed"},
            "failed_node": "review_risks",
        }


# ==================== 节点6: 回写评论 ====================

async def write_comment_node(state: WorkflowState, db: AsyncSession) -> dict:
    """将风险审查结果格式化后回写到 OA 审批评论区

    返回: {"comment_content": ..., "comment_written": True/False}
    """
    logger.info(f"[节点6] 回写审批评论 | task_id={state['task_id']}")

    risk_service = RiskReviewService(db)
    approval_service = ApprovalService(db)

    try:
        risk_results = state.get("risk_results", [])
        risk_score = state.get("risk_score", {})

        # 格式化评论内容
        comment_content = risk_service.format_comment_content(risk_results, risk_score)

        # 回写到 OA
        success = await approval_service.write_comment(
            state["approval_order_id"],
            comment_content,
        )

        return {
            "comment_content": comment_content,
            "comment_written": success,
            "current_node": "write_comment",
            "node_statuses": {"write_comment": "completed"},
        }
    except Exception as e:
        logger.error(f"评论回写失败 | error={e}")
        return {
            "comment_content": "",
            "comment_written": False,
            "error_message": str(e),
            "error_type": type(e).__name__,
            "current_node": "write_comment",
            "node_statuses": {"write_comment": "failed"},
            "failed_node": "write_comment",
        }


# ==================== 节点7: 完成任务 ====================

async def complete_task_node(state: WorkflowState, db: AsyncSession) -> dict:
    """标记任务完成，记录耗时"""
    logger.info(f"[节点7] 完成任务 | task_id={state['task_id']}")

    started_at_str = state.get("started_at", "")
    completed_at = datetime.now().isoformat()

    duration_ms = 0
    if started_at_str:
        try:
            started = datetime.fromisoformat(started_at_str)
            duration_ms = int((datetime.now() - started).total_seconds() * 1000)
        except (ValueError, TypeError):
            pass

    return {
        "completed_at": completed_at,
        "duration_ms": duration_ms,
        "current_node": "complete",
        "node_statuses": {"complete": "completed"},
    }


# ==================== 节点5.5: LLM 全面审核 ====================

async def llm_review_node(state: WorkflowState, db: AsyncSession) -> dict:
    """使用 LLM 对整份合同进行全面语义审核

    补充规则引擎只能检查字段存在性的局限，识别语义层面的风险。
    """
    logger.info(f"[节点5.5] LLM 全面审核 | task_id={state['task_id']}")

    try:
        parse_text = state.get("parse_text", "")
        if not parse_text:
            return {"current_node": "llm_review", "llm_risks": [], "node_statuses": {"llm_review": "completed"}}

        # 构建字段摘要传给 LLM
        field_data = {
            "contract_no": state.get("contract_no"),
            "party_a_info": state.get("party_a_info"),
            "party_b_info": state.get("party_b_info"),
            "amount": state.get("amount"),
            "start_date": state.get("start_date"),
            "end_date": state.get("end_date"),
            "payment_terms": state.get("payment_terms"),
            "liability_clause": state.get("liability_clause"),
        }

        from app.services.risk.risk_engine import risk_engine

        llm_risks = await risk_engine.comprehensive_llm_review(parse_text, field_data)

        # 合并 LLM 风险到总结果
        all_risks = list(state.get("risk_results", []))
        all_risks.extend(llm_risks)

        # 重新计算评分
        score = risk_engine.calculate_risk_score(all_risks)

        return {
            "risk_results": all_risks,
            "risk_score": score,
            "risk_count": len(all_risks),
            "has_risks": len(all_risks) > 0,
            "llm_risks": llm_risks,
            "current_node": "llm_review",
            "node_statuses": {"llm_review": "completed"},
        }
    except Exception as e:
        logger.error(f"LLM 审核失败 | error={e}")
        return {
            "current_node": "llm_review", "llm_risks": [],
            "node_statuses": {"llm_review": "failed"},
            "failed_node": "llm_review",
        }


# ==================== 节点8: 阻塞任务 ====================

async def block_task_node(state: WorkflowState, db: AsyncSession) -> dict:
    """将任务标记为阻塞状态，等待人工恢复"""
    logger.warning(f"[节点8] 阻塞任务 | task_id={state['task_id']} | reason={state.get('block_reason')}")

    return {
        "is_blocked": True,
        "block_reason": state.get("block_reason", state.get("error_message", "未知原因")),
        "current_node": "blocked",
        "node_statuses": {"blocked": "failed"},
        "failed_node": state.get("current_node", "blocked"),
    }


# ==================== 节点工具：持久化任务状态 ====================

async def persist_task_state(state: WorkflowState, db: AsyncSession) -> None:
    """将当前 WorkflowState 持久化到 t_workflow_task"""
    import json

    from app.repositories.workflow_task_repo import WorkflowTaskRepository

    task_repo = WorkflowTaskRepository(db)
    task = await task_repo.get_by_task_id(state["task_id"])

    if task:
        task.status = _derive_status(state)
        task.current_node = state.get("current_node", "")
        task.state_json = json.dumps(_serializable_state(state), ensure_ascii=False, default=str)
        task.error_message = state.get("error_message", "")
        task.retry_count = state.get("retry_count", 0)
        task.started_at = _parse_datetime(state.get("started_at"))
        task.completed_at = _parse_datetime(state.get("completed_at"))
        task.duration_ms = state.get("duration_ms")
        await task_repo.update(task)
        logger.debug(f"任务状态已持久化 | task_id={state['task_id']} | status={task.status}")


def _derive_status(state: WorkflowState) -> str:
    """根据状态推导任务状态"""
    if state.get("is_blocked"):
        return "blocked"
    if state.get("completed_at"):
        return "success"
    if state.get("error_message") and not state.get("has_risks"):
        return "failed"
    if state.get("current_node"):
        return "running"
    return "pending"


def _serializable_state(state: WorkflowState) -> dict:
    """过滤掉不可序列化的字段（保留 node_statuses 用于前端展示）"""
    skip_keys = {"messages", "risk_results", "approval_data"}
    result = {k: v for k, v in state.items() if k not in skip_keys}
    # 确保 node_statuses 和 failed_node 被包含
    if "node_statuses" in state:
        result["node_statuses"] = state["node_statuses"]
    if "failed_node" in state:
        result["failed_node"] = state["failed_node"]
    return result


def _parse_datetime(dt_str: str | None) -> datetime | None:
    """解析 ISO 时间字符串"""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str)
    except (ValueError, TypeError):
        return None
