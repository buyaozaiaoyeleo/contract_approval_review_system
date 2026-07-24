from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, verify_api_key
from app.models.contract_document import ContractDocument
from app.models.workflow_task import WorkflowTask
from app.repositories.workflow_task_repo import WorkflowTaskRepository
from app.workflow.contract_review_workflow import contract_review_workflow

router = APIRouter(prefix="/tasks")


# ==================== 请求/响应模型 ====================

class CreateTaskRequest(BaseModel):
    """创建审查任务请求"""
    approval_order_id: int = Field(..., gt=0, description="审批单 ID")
    async_mode: bool = Field(default=False, description="是否异步执行")


class CreateTaskResponse(BaseModel):
    """创建审查任务响应"""
    task_id: str
    status: str
    message: str


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str
    task_status: str
    current_node: str | None
    retry_count: int
    error_message: str | None
    started_at: str | None
    completed_at: str | None
    duration_ms: int | None
    node_statuses: dict | None
    failed_node: str | None
    file_name: str | None = None  # 原文档名称，从 state_json.doc_id 关联查询


class TaskListResponse(BaseModel):
    """任务列表响应"""
    total: int
    items: list[TaskStatusResponse]


# ==================== 路由 ====================

async def _resolve_file_name(db: AsyncSession, task: WorkflowTask) -> str | None:
    """从 state_json.doc_id 或 approval_order_id 反查原文档文件名"""
    import json as _json

    from sqlalchemy import select

    # 1) 优先从 state_json 的 doc_id 查
    if task.state_json:
        try:
            state_data = _json.loads(task.state_json)
            doc_id = state_data.get("doc_id")
            if doc_id:
                row = await db.execute(
                    select(ContractDocument.file_name).where(ContractDocument.doc_id == doc_id)
                )
                first = row.first()
                if first:
                    return first[0]
        except _json.JSONDecodeError:
            pass

    # 2) 降级：根据审批单 ID 查第一个文档
    row = await db.execute(
        select(ContractDocument.file_name)
        .where(ContractDocument.approval_order_id == task.approval_order_id)
        .order_by(ContractDocument.created_at.asc())
        .limit(1)
    )
    first = row.first()
    return first[0] if first else None


def _effective_duration_ms(task: WorkflowTask) -> int | None:
    """返回任务耗时：已完成用存库值，执行中用实时已用时间"""
    if task.duration_ms is not None:
        return task.duration_ms
    if task.status in ("running", "pending") and task.started_at is not None:
        try:
            started = task.started_at
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            return int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        except Exception:
            return None
    return None

@router.post(
    "/review",
    response_model=CreateTaskResponse,
    summary="创建合同审查任务",
    description="对指定审批单创建审查任务，支持同步/异步两种模式。",
)
async def create_review_task(
    body: CreateTaskRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_api_key),
):
    """创建审查任务并启动工作流"""
    # 检查是否有进行中的任务
    task_repo = WorkflowTaskRepository(db)
    existing = await task_repo.get_running_by_approval(body.approval_order_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"审批单 {body.approval_order_id} 已有进行中的任务: {existing.task_id}",
        )

    task_id = await contract_review_workflow.create_task(db, body.approval_order_id)

    if body.async_mode:
        await contract_review_workflow.run_background(task_id, body.approval_order_id)
        return CreateTaskResponse(
            task_id=task_id,
            status="started",
            message="审查任务已启动，请稍后查询结果",
        )

    result = await contract_review_workflow.run(task_id, body.approval_order_id)
    return CreateTaskResponse(
        task_id=task_id,
        status=result.get("status", "unknown"),
        message=f"审查完成 | 风险数: {result.get('risk_count', 0)} | 等级: {result.get('risk_level', 'NONE')}",
    )


@router.post(
    "/{task_id}/retry",
    response_model=CreateTaskResponse,
    summary="重试审查任务",
    description="重试失败或阻塞的审查任务。",
)
async def retry_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_api_key),
):
    """重试审查任务"""
    task_repo = WorkflowTaskRepository(db)
    task = await task_repo.get_by_task_id(task_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

    if task.status not in ("failed", "blocked"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"只能重试失败或阻塞的任务，当前状态: {task.status}",
        )

    # 直接审查任务不使用 LangGraph，重新执行直接审查流程
    if task.workflow_name == "direct_review":
        # 从 state_json 中提取 doc_id
        import json
        try:
            state = json.loads(task.state_json) if task.state_json else {}
        except json.JSONDecodeError:
            state = {}
        doc_id = state.get("doc_id", "")

        if not doc_id:
            raise HTTPException(status_code=400, detail="无法从任务状态中获取 doc_id，请重新发起审查")

        # 重新生成 task_id 避免冲突
        from app.common.snowflake import generate_id
        new_task_id = f"TASK_{generate_id()}"
        result = await contract_review_workflow.run_direct_review(new_task_id, doc_id)
        return CreateTaskResponse(
            task_id=new_task_id,
            status=result.get("status", "unknown"),
            message=f"直接审查已重新执行 | 风险数: {result.get('risk_count', 0)}",
        )

    result = await contract_review_workflow.resume(task_id)
    return CreateTaskResponse(
        task_id=task_id,
        status=result.get("status", "unknown"),
        message=f"任务已恢复执行 | 当前节点: {result.get('current_node', '')}",
    )


@router.get(
    "/{task_id}",
    response_model=TaskStatusResponse,
    summary="查询任务状态",
    description="查询指定任务的执行状态和进度。",
)
async def get_task_status(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_api_key),
):
    """查询任务状态"""
    task_repo = WorkflowTaskRepository(db)
    task = await task_repo.get_by_task_id(task_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

    # 从 state_json 解析 node_statuses 和 failed_node
    import json as _json
    node_statuses = None
    failed_node = None
    if task.state_json:
        try:
            state_data = _json.loads(task.state_json)
            node_statuses = state_data.get("node_statuses")
            failed_node = state_data.get("failed_node")
        except _json.JSONDecodeError:
            pass

    return TaskStatusResponse(
        task_id=task.task_id,
        task_status=task.status,
        current_node=task.current_node,
        retry_count=task.retry_count,
        error_message=task.error_message,
        started_at=str(task.started_at) if task.started_at else None,
        completed_at=str(task.completed_at) if task.completed_at else None,
        duration_ms=_effective_duration_ms(task),
        node_statuses=node_statuses,
        failed_node=failed_node,
        file_name=await _resolve_file_name(db, task),
    )


@router.get(
    "",
    response_model=TaskListResponse,
    summary="查询任务列表",
    description="分页查询任务列表，支持按状态筛选。",
)
async def list_tasks(
    status_filter: str | None = Query(None, alias="status", description="按状态筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_api_key),
):
    """查询任务列表"""
    from sqlalchemy import func, select

    from app.models.workflow_task import WorkflowTask

    query = select(WorkflowTask)
    count_query = select(func.count(WorkflowTask.id))

    if status_filter:
        query = query.where(WorkflowTask.status == status_filter)
        count_query = count_query.where(WorkflowTask.status == status_filter)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(WorkflowTask.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    tasks = list(result.scalars().all())

    import json as _json

    def _parse_node_info(t):
        """从 state_json 解析 node_statuses 和 failed_node"""
        node_statuses = None
        failed_node = None
        if t.state_json:
            try:
                state_data = _json.loads(t.state_json)
                node_statuses = state_data.get("node_statuses")
                failed_node = state_data.get("failed_node")
            except _json.JSONDecodeError:
                pass
        return node_statuses, failed_node

    # 批量解析 doc_id，用于后续批量查询原文档名称
    doc_ids: set[str] = set()
    approval_ids: set[int] = set()
    for t in tasks:
        if t.state_json:
            try:
                sd = _json.loads(t.state_json)
                did = sd.get("doc_id")
                if did:
                    doc_ids.add(did)
            except _json.JSONDecodeError:
                pass
        approval_ids.add(t.approval_order_id)

    # 批量查询合同文档文件名，构建 doc_id → file_name 映射
    file_name_map: dict[str, str] = {}
    if doc_ids:
        docs_result = await db.execute(
            select(ContractDocument.doc_id, ContractDocument.file_name).where(
                ContractDocument.doc_id.in_(doc_ids)
            )
        )
        for row in docs_result.fetchall():
            file_name_map[row[0]] = row[1]

    # 降级映射：approval_order_id → file_name（无 doc_id 的任务用）
    fallback_map: dict[int, str] = {}
    if approval_ids:
        fb_result = await db.execute(
            select(ContractDocument.approval_order_id, ContractDocument.file_name)
            .where(ContractDocument.approval_order_id.in_(approval_ids))
            .order_by(ContractDocument.approval_order_id.asc(), ContractDocument.created_at.asc())
        )
        for row in fb_result.fetchall():
            if row[0] not in fallback_map:
                fallback_map[row[0]] = row[1]

    def _get_file_name(t) -> str | None:
        """从 state_json.doc_id 或 approval_order_id 获取原文档名称"""
        if t.state_json:
            try:
                sd = _json.loads(t.state_json)
                doc_id = sd.get("doc_id")
                if doc_id and doc_id in file_name_map:
                    return file_name_map[doc_id]
            except _json.JSONDecodeError:
                pass
        return fallback_map.get(t.approval_order_id)

    return TaskListResponse(
        total=total,
        items=[
            TaskStatusResponse(
                task_id=t.task_id,
                task_status=t.status,
                current_node=t.current_node,
                retry_count=t.retry_count,
                error_message=t.error_message,
                started_at=str(t.started_at) if t.started_at else None,
                completed_at=str(t.completed_at) if t.completed_at else None,
                duration_ms=_effective_duration_ms(t),
                node_statuses=_parse_node_info(t)[0],
                failed_node=_parse_node_info(t)[1],
                file_name=_get_file_name(t),
            )
            for t in tasks
        ],
    )
