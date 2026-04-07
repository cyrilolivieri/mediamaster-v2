"""Schedule content route — POST /api/schedule."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from api.models.schemas import (
    ErrorResponse,
    ScheduleRequest,
    ScheduleResponse,
)
from workflows.schedule import run_schedule_workflow

router = APIRouter(prefix="/api", tags=["schedule"])


@router.post(
    "/schedule",
    response_model=ScheduleResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Workflow error"},
    },
    summary="Schedule content for future publishing",
)
async def schedule_content(request: ScheduleRequest) -> JSONResponse | ScheduleResponse:
    """
    Schedule content for future publishing on one or more platforms.

    The workflow validates the content and timestamp, calculates platform-specific
    timing (with a 5-minute stagger between platforms), schedules, and confirms.
    """
    try:
        state = await run_schedule_workflow(
            content=request.content,
            platforms=[p.value for p in request.platforms],
            scheduled_at=request.scheduled_at,
            media_urls=request.media_urls,
            link_url=request.link_url,
            metadata=request.metadata,
        )
    except Exception as exc:  # noqa: BLE-001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow error: {exc}",
        ) from exc

    if state.get("validation_errors") and not state.get("schedule_results"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(state["validation_errors"]),
        )

    results = state.get("schedule_results", [])
    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful

    return ScheduleResponse(
        results=results,
        total=len(results),
        successful=successful,
        failed=failed,
    )
