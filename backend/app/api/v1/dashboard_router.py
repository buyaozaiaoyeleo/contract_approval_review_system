"""Dashboard API routes."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.approval_order import ApprovalOrder
from app.models.risk_review_result import RiskReviewResult
from app.models.workflow_task import WorkflowTask

router = APIRouter(prefix="/dashboard")


class DashboardStatsResponse(BaseModel):
    total_orders: int = Field(..., description="Total approval orders")
    total_reviews: int = Field(..., description="Total review tasks")
    total_risks: int = Field(..., description="Total risk results")
    risk_distribution: dict = Field(..., description="Risk level distribution")
    avg_duration: float = Field(..., description="Average duration in seconds")
    success_rate: float = Field(..., description="Review success rate")


class DashboardTrendResponse(BaseModel):
    dates: list[str] = Field(..., description="Date labels")
    review_counts: list[int] = Field(..., description="Review counts")
    risk_counts: list[int] = Field(..., description="Risk counts")


@router.get(
    "/stats",
    response_model=DashboardStatsResponse,
    summary="Get dashboard statistics",
)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    total_orders_result = await db.execute(select(func.count(ApprovalOrder.id)))
    total_orders = int(total_orders_result.scalar() or 0)

    total_reviews_result = await db.execute(select(func.count(WorkflowTask.id)))
    total_reviews = int(total_reviews_result.scalar() or 0)

    total_risks_result = await db.execute(select(func.count(RiskReviewResult.id)))
    total_risks = int(total_risks_result.scalar() or 0)

    risk_dist_result = await db.execute(
        select(
            func.sum(case((RiskReviewResult.risk_level == "HIGH", 1), else_=0)).label("high"),
            func.sum(case((RiskReviewResult.risk_level == "MEDIUM", 1), else_=0)).label("medium"),
            func.sum(case((RiskReviewResult.risk_level == "LOW", 1), else_=0)).label("low"),
        )
    )
    dist = risk_dist_result.one_or_none()
    risk_distribution = {
        "high": int(dist.high or 0) if dist else 0,
        "medium": int(dist.medium or 0) if dist else 0,
        "low": int(dist.low or 0) if dist else 0,
    }

    avg_duration_result = await db.execute(
        select(func.avg(WorkflowTask.duration_ms)).where(WorkflowTask.status == "success")
    )
    raw_avg = avg_duration_result.scalar()
    avg_duration = 0.0 if raw_avg is None else float(raw_avg) / 1000.0

    success_count_result = await db.execute(
        select(func.count(WorkflowTask.id)).where(WorkflowTask.status == "success")
    )
    success_count = int(success_count_result.scalar() or 0)
    success_rate = round(success_count / total_reviews * 100, 1) if total_reviews > 0 else 0.0

    return DashboardStatsResponse(
        total_orders=total_orders,
        total_reviews=total_reviews,
        total_risks=total_risks,
        risk_distribution=risk_distribution,
        avg_duration=round(avg_duration, 1),
        success_rate=success_rate,
    )


@router.get(
    "/trend",
    response_model=DashboardTrendResponse,
    summary="Get dashboard trend",
)
async def get_dashboard_trend(
    days: int = Query(30, ge=1, le=365, description="Days to query"),
    db: AsyncSession = Depends(get_db),
):
    start_date = datetime.now() - timedelta(days=days)
    dates: list[str] = []
    review_counts: list[int] = []
    risk_counts: list[int] = []

    for index in range(days):
        day_start = start_date + timedelta(days=index)
        day_end = day_start + timedelta(days=1)
        dates.append(day_start.strftime("%Y-%m-%d"))

        review_count_result = await db.execute(
            select(func.count(WorkflowTask.id)).where(
                WorkflowTask.created_at >= day_start,
                WorkflowTask.created_at < day_end,
            )
        )
        review_counts.append(int(review_count_result.scalar() or 0))

        risk_count_result = await db.execute(
            select(func.count(RiskReviewResult.id)).where(
                RiskReviewResult.created_at >= day_start,
                RiskReviewResult.created_at < day_end,
            )
        )
        risk_counts.append(int(risk_count_result.scalar() or 0))

    return DashboardTrendResponse(
        dates=dates,
        review_counts=review_counts,
        risk_counts=risk_counts,
    )


@router.get(
    "/risk-distribution",
    response_model=dict,
    summary="Get risk distribution",
)
async def get_risk_distribution(db: AsyncSession = Depends(get_db)):
    risk_dist_result = await db.execute(
        select(
            func.sum(case((RiskReviewResult.risk_level == "HIGH", 1), else_=0)).label("high"),
            func.sum(case((RiskReviewResult.risk_level == "MEDIUM", 1), else_=0)).label("medium"),
            func.sum(case((RiskReviewResult.risk_level == "LOW", 1), else_=0)).label("low"),
        )
    )
    dist = risk_dist_result.one_or_none()
    return {
        "high": int(dist.high or 0) if dist else 0,
        "medium": int(dist.medium or 0) if dist else 0,
        "low": int(dist.low or 0) if dist else 0,
    }
