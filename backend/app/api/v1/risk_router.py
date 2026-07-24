"""Risk review API routes."""

from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_risk_review_service, get_rule_service, verify_api_key
from app.common.response import ApiResponse
from app.models.contract_document import ContractDocument
from app.models.risk_review_result import RiskReviewResult
from app.repositories.workflow_task_repo import WorkflowTaskRepository
from app.services.risk.risk_service import RiskReviewService
from app.services.risk.rule_service import RuleService

router = APIRouter(prefix="/risks")


def _is_generated_report_name(file_name: str | None) -> bool:
    if not file_name:
        return False
    upper_name = file_name.upper()
    return upper_name.startswith("HIGH_") or upper_name.startswith("MEDIUM_") or upper_name.startswith("LOW_")


async def _load_original_contract_names(db: AsyncSession, approval_order_ids: list[int]) -> dict[int, str | None]:
    if not approval_order_ids:
        return {}

    result = await db.execute(
        select(ContractDocument)
        .where(ContractDocument.approval_order_id.in_(approval_order_ids))
        .order_by(ContractDocument.approval_order_id.asc(), ContractDocument.created_at.asc(), ContractDocument.id.asc())
    )
    docs = result.scalars().all()

    names: dict[int, str | None] = {}
    for doc in docs:
        current_name = names.get(doc.approval_order_id)
        if current_name is None:
            names[doc.approval_order_id] = doc.file_name
            continue
        if _is_generated_report_name(current_name) and not _is_generated_report_name(doc.file_name):
            names[doc.approval_order_id] = doc.file_name
    return names


async def _serialize_risk_rows(db: AsyncSession, rows: list[dict], fallback_approval_order_id: int | None = None) -> list[dict]:
    approval_order_ids = sorted(
        {
            int(row.get("approval_order_id") or fallback_approval_order_id)
            for row in rows
            if row.get("approval_order_id") or fallback_approval_order_id
        }
    )
    contract_names = await _load_original_contract_names(db, approval_order_ids)

    items = []
    for row in rows:
        approval_order_id = row.get("approval_order_id") or fallback_approval_order_id
        items.append(
            {
                "risk_id": row["risk_id"],
                "approval_order_id": str(approval_order_id) if approval_order_id is not None else None,
                "contract_file_name": contract_names.get(int(approval_order_id)) if approval_order_id is not None else None,
                "rule_id": row.get("rule_id"),
                "risk_level": row["risk_level"],
                "risk_description": row["risk_description"],
                "suggestion": row.get("suggestion"),
                "source_text": row.get("source_text"),
                "field_name": row.get("field_name"),
                "is_valid": bool(row.get("is_valid", True)),
            }
        )
    return items


async def _query_risk_rows(
    db: AsyncSession,
    where_sql: str = "",
    params: dict | None = None,
    limit_sql: str = "",
):
    base_params = params or {}
    query_candidates = [
        text(
            "SELECT risk_id, approval_order_id, rule_id, risk_level, risk_description, suggestion, source_text, field_name, is_valid "
            f"FROM t_risk_review_result{where_sql} ORDER BY created_at DESC, id DESC{limit_sql}"
        ),
        text(
            "SELECT risk_id, approval_order_id, rule_id, risk_level, risk_description, suggestion, source_text, is_valid "
            f"FROM t_risk_review_result{where_sql} ORDER BY created_at DESC, id DESC{limit_sql}"
        ),
        text(
            "SELECT risk_id, approval_order_id, rule_id, risk_level, risk_description, suggestion, is_valid "
            f"FROM t_risk_review_result{where_sql} ORDER BY id DESC{limit_sql}"
        ),
    ]

    last_error = None
    for query in query_candidates:
        try:
            result = await db.execute(query, base_params)
            return result.mappings().all()
        except Exception as exc:
            last_error = exc

    if last_error is not None:
        raise last_error
    return []


class CreateRuleRequest(BaseModel):
    rule_code: str = Field(..., min_length=1, max_length=64)
    rule_name: str = Field(..., min_length=1, max_length=200)
    rule_category: str
    rule_type: str = Field("field")
    rule_config_json: str | None = None
    priority: int = 0
    risk_level: str = "MEDIUM"
    description: str | None = None


class UpdateRuleRequest(BaseModel):
    rule_name: str | None = None
    rule_category: str | None = None
    rule_type: str | None = None
    rule_config_json: str | None = None
    priority: int | None = None
    risk_level: str | None = None
    is_enabled: bool | None = None
    description: str | None = None


class RuleResponse(BaseModel):
    id: int
    rule_code: str
    rule_name: str
    rule_category: str
    rule_type: str
    risk_level: str
    priority: int
    is_enabled: bool
    description: str | None


class RiskResultResponse(BaseModel):
    risk_id: str
    approval_order_id: str | None = None
    contract_file_name: str | None = None
    rule_id: int | None
    risk_level: str
    risk_description: str
    suggestion: str | None
    source_text: str | None
    field_name: str | None
    is_valid: bool


class RiskReportResponse(BaseModel):
    approval_order_id: str
    overall_level: str
    risk_score: int
    summary: str
    statistics: dict
    high_risks: list[dict]
    medium_risks: list[dict]
    low_risks: list[dict]


@router.post("/rules", response_model=RuleResponse, summary="Create risk rule")
async def create_rule(
    body: CreateRuleRequest,
    service: RuleService = Depends(get_rule_service),
    _auth: str = Depends(verify_api_key),
):
    existing = await service.get_by_rule_code(body.rule_code)
    if existing:
        raise HTTPException(status_code=409, detail="Rule code already exists")

    rule = await service.create_rule(**body.model_dump())
    return RuleResponse(
        id=rule.id,
        rule_code=rule.rule_code,
        rule_name=rule.rule_name,
        rule_category=rule.rule_category,
        rule_type=rule.rule_type,
        risk_level=rule.risk_level,
        priority=rule.priority,
        is_enabled=rule.is_enabled,
        description=rule.description,
    )


@router.put("/rules/{rule_id}", response_model=RuleResponse, summary="Update risk rule")
async def update_rule(
    rule_id: int,
    body: UpdateRuleRequest,
    service: RuleService = Depends(get_rule_service),
    _auth: str = Depends(verify_api_key),
):
    rule = await service.update_rule(rule_id, **body.model_dump(exclude_none=True))
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    return RuleResponse(
        id=rule.id,
        rule_code=rule.rule_code,
        rule_name=rule.rule_name,
        rule_category=rule.rule_category,
        rule_type=rule.rule_type,
        risk_level=rule.risk_level,
        priority=rule.priority,
        is_enabled=rule.is_enabled,
        description=rule.description,
    )


@router.delete("/rules/{rule_id}", summary="Delete risk rule")
async def delete_rule(
    rule_id: int,
    service: RuleService = Depends(get_rule_service),
    _auth: str = Depends(verify_api_key),
):
    success = await service.delete_rule(rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Rule not found")
    return ApiResponse.success(data={"status": "deleted", "rule_id": rule_id})


@router.post("/rules/{rule_id}/toggle", response_model=RuleResponse, summary="Toggle risk rule")
async def toggle_rule(
    rule_id: int,
    enabled: bool = Query(...),
    service: RuleService = Depends(get_rule_service),
    _auth: str = Depends(verify_api_key),
):
    rule = await service.toggle_rule(rule_id, enabled)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    return RuleResponse(
        id=rule.id,
        rule_code=rule.rule_code,
        rule_name=rule.rule_name,
        rule_category=rule.rule_category,
        rule_type=rule.rule_type,
        risk_level=rule.risk_level,
        priority=rule.priority,
        is_enabled=rule.is_enabled,
        description=rule.description,
    )


@router.get("/rules", response_model=list[RuleResponse], summary="List risk rules")
async def list_rules(
    category: str | None = Query(None),
    enabled_only: bool = Query(True),
    service: RuleService = Depends(get_rule_service),
    _auth: str = Depends(verify_api_key),
):
    rules = await service.list_by_category(category) if category else await service.list_all(enabled_only=enabled_only)
    return [
        RuleResponse(
            id=rule.id,
            rule_code=rule.rule_code,
            rule_name=rule.rule_name,
            rule_category=rule.rule_category,
            rule_type=rule.rule_type,
            risk_level=rule.risk_level,
            priority=rule.priority,
            is_enabled=rule.is_enabled,
            description=rule.description,
        )
        for rule in rules
    ]


def _serialize_risk_result(item: RiskReviewResult) -> dict:
    return {
        "risk_id": item.risk_id,
        "approval_order_id": str(item.approval_order_id) if item.approval_order_id is not None else None,
        "contract_file_name": None,
        "rule_id": item.rule_id,
        "risk_level": item.risk_level,
        "risk_description": item.risk_description,
        "suggestion": item.suggestion,
        "source_text": item.source_text,
        "field_name": item.field_name,
        "is_valid": item.is_valid,
    }


@router.get("/results/{approval_order_id}", summary="Get risk results by approval")
async def get_risk_results(
    approval_order_id: int,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_api_key),
):
    rows = await _query_risk_rows(
        db,
        where_sql=" WHERE approval_order_id = :approval_order_id",
        params={"approval_order_id": approval_order_id},
    )
    items = await _serialize_risk_rows(db, rows, fallback_approval_order_id=approval_order_id)
    return ApiResponse.success(
        data=items,
        message="Query success",
    )


@router.get("/report/{approval_order_id}", summary="Get risk report")
async def get_risk_report(
    approval_order_id: int,
    service: RiskReviewService = Depends(get_risk_review_service),
    _auth: str = Depends(verify_api_key),
):
    report = await service.generate_report(approval_order_id)
    return ApiResponse.success(data=RiskReportResponse(**report).model_dump(), message="Query success")


@router.get("/report/{approval_order_id}/download", summary="Download risk report PDF")
async def download_risk_report_pdf(
    approval_order_id: int,
    service: RiskReviewService = Depends(get_risk_review_service),
    _auth: str = Depends(verify_api_key),
):
    file_name, pdf_bytes = await service.export_report_pdf(approval_order_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="risk-report-{approval_order_id}.pdf"; '
                f"filename*=UTF-8''{quote(file_name)}"
            )
        },
    )


@router.get("/results/by-task/{task_id}", summary="Get risk results by task")
async def get_risk_results_by_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_api_key),
):
    task_repo = WorkflowTaskRepository(db)
    task = await task_repo.get_by_task_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    rows = await _query_risk_rows(
        db,
        where_sql=" WHERE approval_order_id = :approval_order_id",
        params={"approval_order_id": task.approval_order_id},
    )
    items = await _serialize_risk_rows(db, rows, fallback_approval_order_id=task.approval_order_id)
    return ApiResponse.success(
        data=items,
        message="Query success",
    )


@router.get("/results", summary="List risk results")
async def list_all_risk_results(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    approval_order_id: int | None = Query(None, description="按审批单 ID 筛选"),
    risk_level: str | None = Query(None, description="按风险等级筛选 HIGH/MEDIUM/LOW"),
    keyword: str | None = Query(None, description="搜索风险描述或原文"),
    contract_file_name: str | None = Query(None, description="按原合同名称筛选"),
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_api_key),
):
    # 兼容历史 camelCase 查询参数，优先使用当前前端的 snake_case。
    risk_level = risk_level or request.query_params.get("riskLevel")
    keyword = keyword or request.query_params.get("keyword")
    contract_file_name = contract_file_name or request.query_params.get("contractFileName")

    where_clauses = []
    params: dict[str, object] = {}

    if approval_order_id is not None:
        where_clauses.append("approval_order_id = :approval_order_id")
        params["approval_order_id"] = approval_order_id
    if risk_level:
        where_clauses.append("risk_level = :risk_level")
        params["risk_level"] = risk_level
    if keyword:
        where_clauses.append("(risk_description LIKE :keyword OR source_text LIKE :keyword)")
        params["keyword"] = f"%{keyword}%"

    where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    rows = await _query_risk_rows(
        db,
        where_sql=where_sql,
        params=params,
    )
    items = await _serialize_risk_rows(db, rows, fallback_approval_order_id=approval_order_id)

    if contract_file_name:
        contract_name_keyword = contract_file_name.strip().lower()
        items = [
            item
            for item in items
            if contract_name_keyword in (item.get("contract_file_name") or "").lower()
        ]

    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size

    return ApiResponse.success(
        data={
            "items": items[start:end],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
        message="Query success",
    )


@router.post("/results/{risk_id}/validate", summary="Validate risk result")
async def validate_risk(
    risk_id: str,
    is_valid: bool = Query(...),
    service: RiskReviewService = Depends(get_risk_review_service),
    _auth: str = Depends(verify_api_key),
):
    success = await service.validate_result(risk_id, is_valid)
    if not success:
        raise HTTPException(status_code=404, detail="Risk result not found")

    return ApiResponse.success(
        data={"status": "validated", "risk_id": risk_id, "is_valid": is_valid},
        message="Operation success",
    )
