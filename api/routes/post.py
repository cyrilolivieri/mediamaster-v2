"""Publish content route — POST /api/post."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from api.models.schemas import (
    ErrorResponse,
    PostRequest,
    PostResponse,
    PostResultItem,
)
from workflows.publish import run_publish_workflow

router = APIRouter(prefix="/api", tags=["post"])


@router.post(
    "/post",
    response_model=PostResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Workflow error"},
    },
    summary="Publish content to platforms",
)
async def post_content(request: PostRequest) -> JSONResponse | PostResponse:
    """
    Publish content to one or more platforms using the publish workflow.

    The workflow validates content, selects capable platforms, posts concurrently,
    and verifies results.
    """
    try:
        state = await run_publish_workflow(
            content=request.content,
            platforms=[p.value for p in request.platforms],
            media_urls=request.media_urls,
            link_url=request.link_url,
            metadata=request.metadata,
        )
    except Exception as exc:  # noqa: BLE-001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow error: {exc}",
        ) from exc

    if state.get("validation_errors") and not state.get("post_results"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(state["validation_errors"]),
        )

    results = state.get("post_results", [])
    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful

    return PostResponse(
        results=results,
        total=len(results),
        successful=successful,
        failed=failed,
    )
