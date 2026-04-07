"""Analytics route — GET /api/analytics/{platform}."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from api.models.schemas import AnalyticsResponse, ErrorResponse, PlatformName
from workflows.analytics import run_analytics_workflow

router = APIRouter(prefix="/api", tags=["analytics"])


@router.get(
    "/analytics/{platform}",
    response_model=AnalyticsResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid platform"},
        500: {"model": ErrorResponse, "description": "Workflow error"},
    },
    summary="Fetch analytics for a platform",
)
async def get_analytics(
    platform: PlatformName,
    period: str | None = Query(None, description="Reporting period (day/week/month)"),
    since: datetime | None = Query(None, description="Start of date range (ISO 8601)"),
    until: datetime | None = Query(None, description="End of date range (ISO 8601)"),
) -> AnalyticsResponse:
    """
    Fetch analytics for a specific platform using the analytics workflow.

    The workflow: fetch raw data → aggregate metrics → analyze → report.
    Platforms without native analytics return stub data.
    """
    try:
        state = await run_analytics_workflow(
            platform=platform.value,
            period=period,
            since=since,
            until=until,
        )
    except Exception as exc:  # noqa: BLE-001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow error: {exc}",
        ) from exc

    report = state.get("report") or {}
    metrics: dict[str, Any] = report.get("metrics", [])

    # If report is empty, try raw_data as fallback
    if not metrics and state.get("raw_data"):
        metrics = state["raw_data"]

    return AnalyticsResponse(
        platform=platform.value,
        metrics=metrics,
        fetched_at=datetime.utcnow(),
        error=state.get("error"),
    )
