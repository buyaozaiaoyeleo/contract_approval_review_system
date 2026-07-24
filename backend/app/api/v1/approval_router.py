"""Approval order API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_approval_service, get_db, verify_api_key
from app.common.response import ApiResponse
from app.repositories.contract_document_repo import ContractDocumentRepository
from app.repositories.workflow_task_repo import WorkflowTaskRepository
from app.services.approval.approval_service import ApprovalService
from app.workflow.contract_review_workflow import contract_review_workflow

router = APIRouter(prefix="/approvals")


class ReviewRequest(BaseModel):
    async_mode: bool = False


class SyncRequest(BaseModel):
    auto_review: bool = True
    async_mode: bool = True


def _is_report_file(file_name: str | None) -> bool:
    if not file_name:
        return False
    upper_name = file_name.upper()
    return upper_name.startswith("HIGH_") or upper_name.startswith("MEDIUM_") or upper_name.startswith("LOW_")


async def _start_review_for_approval(
    approval_order_id: int,
    async_mode: bool,
    db: AsyncSession,
    service: ApprovalService,
) -> dict:
    task_repo = WorkflowTaskRepository(db)

    order = await service.get_approval(approval_order_id)
    if not order:
        raise HTTPException(status_code=404, detail="审批单不存在")

    existing = await task_repo.get_running_by_approval(approval_order_id)
    if existing:
        await service.refresh_order_status_from_workflow(approval_order_id)
        return {
            "task_id": existing.task_id,
            "status": "running",
            "message": f"审批单已有进行中的审查任务: {existing.task_id}",
            "reused": True,
        }

    task_id = await contract_review_workflow.create_task(db, approval_order_id)
    await db.commit()

    if async_mode:
        await contract_review_workflow.run_background(task_id, approval_order_id)
        await service.refresh_order_status_from_workflow(approval_order_id)
        return {
            "task_id": task_id,
            "status": "started",
            "message": "审查任务已启动，请稍后查看结果",
            "reused": False,
        }

    result = await contract_review_workflow.run(task_id, approval_order_id)
    await service.refresh_order_status_from_workflow(approval_order_id)
    return {
        "task_id": task_id,
        "status": result.get("status", "unknown"),
        "message": f"审查完成 | 风险数 {result.get('risk_count', 0)} | 等级: {result.get('risk_level', 'NONE')}",
        "risk_count": result.get("risk_count", 0),
        "risk_level": result.get("risk_level", "NONE"),
        "has_risks": result.get("has_risks", False),
        "reused": False,
    }


@router.post("/{approval_order_id}/sync", summary="Sync approval order")
async def sync_approval(
    approval_order_id: str,
    body: SyncRequest = SyncRequest(),
    db: AsyncSession = Depends(get_db),
    service: ApprovalService = Depends(get_approval_service),
    _auth: str = Depends(verify_api_key),
):
    try:
        approval = await service.sync_approval(approval_order_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Sync approval failed: {exc}") from exc

    if not approval:
        raise HTTPException(status_code=404, detail="审批单不存在，且无法从 OA 同步")

    approval = await service.refresh_order_status_from_workflow(approval.id) or approval

    response_data: dict[str, object] = {
        "status": "synced",
        "approval_order_id": str(approval.id),
        "title": approval.title,
        "approval_status": approval.status,
        "auto_review": False,
    }
    response_message = "同步成功"

    if body.auto_review:
        doc_repo = ContractDocumentRepository(db)
        documents = await doc_repo.list_by_approval_order(approval.id)
        original_documents = [doc for doc in documents if not _is_report_file(doc.file_name)]

        if original_documents:
            review_result = await _start_review_for_approval(approval.id, body.async_mode, db, service)
            approval = await service.refresh_order_status_from_workflow(approval.id) or approval
            response_data.update(
                {
                    "auto_review": True,
                    "approval_status": approval.status,
                    "task_id": review_result.get("task_id"),
                    "review_status": review_result.get("status"),
                    "review_message": review_result.get("message"),
                    "reused_task": review_result.get("reused", False),
                }
            )
            if "risk_count" in review_result:
                response_data["risk_count"] = review_result["risk_count"]
            if "risk_level" in review_result:
                response_data["risk_level"] = review_result["risk_level"]
            if "has_risks" in review_result:
                response_data["has_risks"] = review_result["has_risks"]
            response_message = "同步成功，并已自动衔接合同审查"
        else:
            response_data["review_message"] = "同步成功，但当前审批单下没有可审查的原始合同文档"
            response_message = "同步成功，但没有可自动审查的合同文档"

    return ApiResponse.success(data=response_data, message=response_message)


@router.post("/{approval_order_id}/review", summary="Trigger contract review")
async def trigger_review(
    approval_order_id: str,
    body: ReviewRequest = ReviewRequest(),
    db: AsyncSession = Depends(get_db),
    service: ApprovalService = Depends(get_approval_service),
    _auth: str = Depends(verify_api_key),
):
    result = await _start_review_for_approval(int(approval_order_id), body.async_mode, db, service)
    approval = await service.refresh_order_status_from_workflow(int(approval_order_id))
    return ApiResponse.success(
        data={
            "task_id": result.get("task_id"),
            "status": result.get("status"),
            "risk_count": result.get("risk_count", 0),
            "risk_level": result.get("risk_level", "NONE"),
            "has_risks": result.get("has_risks", False),
            "reused_task": result.get("reused", False),
            "approval_status": approval.status if approval else None,
        },
        message=str(result.get("message", "审查任务已处理")),
    )


@router.get("/{approval_order_id}", summary="Get approval order detail")
async def get_approval_detail(
    approval_order_id: str,
    service: ApprovalService = Depends(get_approval_service),
    _auth: str = Depends(verify_api_key),
):
    approval_id = int(approval_order_id)
    approval = await service.get_approval(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval order not found")

    approval = await service.refresh_order_status_from_workflow(approval_id) or approval
    documents = await service.get_documents(approval_id)
    comments = await service.get_comments(approval_id)

    return ApiResponse.success(
        data={
            "approval": {
                "approval_order_id": str(approval.id),
                "title": approval.title,
                "status": approval.status,
                "applicant": approval.applicant,
                "created_at": str(approval.created_at) if approval.created_at else None,
                "updated_at": str(approval.updated_at) if approval.updated_at else None,
            },
            "documents": [
                {
                    "doc_id": document.doc_id,
                    "file_name": document.file_name,
                    "file_type": document.file_type,
                    "parse_status": document.parse_status,
                    "is_scanned": document.is_scanned,
                }
                for document in documents
            ],
            "comments": [
                {
                    "comment_id": comment.comment_id,
                    "content": comment.content,
                    "created_at": str(comment.created_at) if comment.created_at else None,
                }
                for comment in comments
            ],
        },
        message="Query success",
    )


@router.get("", summary="List approval orders")
async def list_approvals(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    keyword: str | None = Query(None, description="Search by title or applicant"),
    db: AsyncSession = Depends(get_db),
    service: ApprovalService = Depends(get_approval_service),
    _auth: str = Depends(verify_api_key),
):
    where_clauses = []
    params: dict[str, object] = {
        "offset": (page - 1) * page_size,
        "limit": page_size,
    }

    if status_filter:
        where_clauses.append("status = :status")
        params["status"] = status_filter
    if keyword:
        where_clauses.append("(title LIKE :keyword OR applicant LIKE :keyword)")
        params["keyword"] = f"%{keyword}%"

    where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    count_query = text(f"SELECT COUNT(id) AS total FROM t_approval_order{where_sql}")
    total_result = await db.execute(count_query, params)
    total = int(total_result.scalar() or 0)

    query_candidates = [
        text(
            "SELECT id, title, status, applicant, created_at, updated_at "
            f"FROM t_approval_order{where_sql} "
            "ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        ),
        text(
            "SELECT id, title, status, applicant, created_at, updated_at "
            f"FROM t_approval_order{where_sql} "
            "ORDER BY id DESC LIMIT :limit OFFSET :offset"
        ),
    ]

    approvals = []
    last_error = None
    for query in query_candidates:
        try:
            result = await db.execute(query, params)
            approvals = result.mappings().all()
            last_error = None
            break
        except Exception as exc:
            last_error = exc

    if last_error is not None:
        raise last_error

    for approval in approvals:
        await service.refresh_order_status_from_workflow(int(approval["id"]))

    refreshed_result = await db.execute(query_candidates[0], params)
    refreshed_approvals = refreshed_result.mappings().all()

    # 批量查询合同风险等级
    risk_map: dict[int, dict[str, object]] = {}
    approval_ids = [int(a["id"]) for a in refreshed_approvals]
    if approval_ids:
        risk_query = text("""
            SELECT approval_order_id,
                   MAX(CASE risk_level
                       WHEN 'HIGH' THEN 3 WHEN 'MEDIUM' THEN 2 WHEN 'LOW' THEN 1 ELSE 0
                   END) AS severity,
                   COUNT(*) AS risk_count
            FROM t_risk_review_result
            WHERE approval_order_id IN :ids
            GROUP BY approval_order_id
        """)
        try:
            risk_result = await db.execute(risk_query, {"ids": tuple(approval_ids)})
            for row in risk_result.mappings().all():
                severity = row["severity"]
                risk_map[int(row["approval_order_id"])] = {
                    "risk_level": {3: "HIGH", 2: "MEDIUM", 1: "LOW"}.get(severity),
                    "risk_count": row["risk_count"],
                }
        except Exception:
            pass

    return ApiResponse.success(
        data={
            "items": [
                {
                    "approval_order_id": str(approval["id"]),
                    "title": approval["title"],
                    "status": approval["status"],
                    "applicant": approval["applicant"],
                    "created_at": str(approval.get("created_at")) if approval.get("created_at") else None,
                    "updated_at": str(approval.get("updated_at")) if approval.get("updated_at") else None,
                    "risk_level": risk_map.get(int(approval["id"]), {}).get("risk_level"),
                    "risk_count": risk_map.get(int(approval["id"]), {}).get("risk_count", 0),
                }
                for approval in refreshed_approvals
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
        message="Query success",
    )
