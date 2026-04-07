"""API routes for MediaMaster v2."""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

from mediamasterv2.api import schemas
from mediamasterv2.api.dependencies import get_factory, get_config


router = APIRouter(prefix="/api", tags=["api"])


# ─── Health & Platforms ───────────────────────────────────────────────────────


@router.get("/health", response_model=schemas.HealthResponse)
async def health_check() -> schemas.HealthResponse:
    """
    Health check across all registered platform connectors.

    Returns overall status: healthy (all up), degraded (some up), unhealthy (all down).
    """
    from mediamasterv2.core.factory import PlatformFactory

    factory = get_factory()
    config = get_config()
    available = factory.available_platforms()

    platform_statuses = []
    healthy_count = 0

    for name in sorted(available):
        try:
            platform = factory.create(name, config)
            healthy = await platform.health_check()
            if healthy:
                healthy_count += 1
            capabilities = [c.name for c in platform.capabilities]
            platform_statuses.append(
                schemas.PlatformStatus(
                    name=name,
                    registered=True,
                    healthy=healthy,
                    capabilities=capabilities,
                )
            )
        except Exception as e:
            platform_statuses.append(
                schemas.PlatformStatus(
                    name=name,
                    registered=True,
                    healthy=False,
                    capabilities=[],
                )
            )

    total = len(platform_statuses)
    if total == 0 or healthy_count == 0:
        status = "unhealthy"
    elif healthy_count < total:
        status = "degraded"
    else:
        status = "healthy"

    return schemas.HealthResponse(
        status=status,
        total_platforms=total,
        healthy_platforms=healthy_count,
        platforms=platform_statuses,
    )


@router.get("/platforms", response_model=schemas.PlatformsResponse)
async def list_platforms() -> schemas.PlatformsResponse:
    """List all registered platform connectors and their capabilities."""
    factory = get_factory()
    config = get_config()
    available = factory.available_platforms()

    platforms = []
    for name in sorted(available):
        try:
            platform = factory.create(name, config)
            platforms.append(
                schemas.PlatformStatus(
                    name=name,
                    registered=True,
                    healthy=None,
                    capabilities=[c.name for c in platform.capabilities],
                )
            )
        except Exception:
            platforms.append(
                schemas.PlatformStatus(name=name, registered=True, healthy=False, capabilities=[])
            )

    return schemas.PlatformsResponse(platforms=platforms)


# ─── Post ─────────────────────────────────────────────────────────────────────


@router.post("/post", response_model=schemas.PostResponse)
async def post_content(req: schemas.PostRequest) -> schemas.PostResponse:
    """
    Post content to one or more platforms.

    Each platform is called independently. Partial success is possible.
    """
    factory = get_factory()
    config = get_config()

    results: list[schemas.PostResultItem] = []
    success_count = 0

    for platform_name in req.platforms:
        try:
            platform = factory.create(platform_name.value, config)

            kwargs: dict[str, Any] = {}
            if req.media_urls:
                kwargs["media_urls"] = req.media_urls
            if req.title and platform_name == schemas.PlatformName.YOUTUBE:
                kwargs["title"] = req.title
                kwargs["privacy_status"] = req.privacy_status
            if req.tags and platform_name == schemas.PlatformName.YOUTUBE:
                kwargs["tags"] = req.tags

            result = await platform.post(req.content, **kwargs)

            results.append(
                schemas.PostResultItem(
                    platform=platform.name,
                    post_id=result.post_id,
                    url=result.url,
                    success=result.success,
                    error=result.error,
                )
            )
            if result.success:
                success_count += 1

        except Exception as e:
            results.append(
                schemas.PostResultItem(
                    platform=platform_name.value,
                    success=False,
                    error=str(e),
                )
            )

    return schemas.PostResponse(
        results=results,
        overall_success=success_count == len(req.platforms),
        total_platforms=len(req.platforms),
        successful_platforms=success_count,
    )


# ─── Schedule ──────────────────────────────────────────────────────────────────


@router.post("/schedule", response_model=schemas.ScheduleResponse)
async def schedule_content(req: schemas.ScheduleRequest) -> schemas.ScheduleResponse:
    """
    Schedule content for future posting on one or more platforms.

    Each platform is scheduled independently. Partial success is possible.
    """
    factory = get_factory()
    config = get_config()

    results: list[schemas.ScheduleResultItem] = []
    success_count = 0

    for platform_name in req.platforms:
        try:
            platform = factory.create(platform_name.value, config)

            kwargs: dict[str, Any] = {}
            if req.media_urls:
                kwargs["media_urls"] = req.media_urls
            if req.title and platform_name == schemas.PlatformName.YOUTUBE:
                kwargs["title"] = req.title
            if req.tags and platform_name == schemas.PlatformName.YOUTUBE:
                kwargs["tags"] = req.tags

            result = await platform.schedule(req.content, req.scheduled_at, **kwargs)

            results.append(
                schemas.ScheduleResultItem(
                    platform=platform.name,
                    schedule_id=result.schedule_id,
                    scheduled_at=result.scheduled_at,
                    success=result.success,
                    error=result.error,
                )
            )
            if result.success:
                success_count += 1

        except Exception as e:
            results.append(
                schemas.ScheduleResultItem(
                    platform=platform_name.value,
                    scheduled_at=req.scheduled_at,
                    success=False,
                    error=str(e),
                )
            )

    return schemas.ScheduleResponse(
        results=results,
        overall_success=success_count == len(req.platforms),
        total_platforms=len(req.platforms),
        successful_platforms=success_count,
    )


# ─── Analytics ─────────────────────────────────────────────────────────────────


@router.get("/analytics/{platform}", response_model=schemas.AnalyticsResponse)
async def get_analytics(
    platform: schemas.PlatformName,
    post_id: str | None = None,
    days: int = 7,
) -> schemas.AnalyticsResponse:
    """
    Fetch analytics for a specific platform.

    Args:
        platform: Platform name
        post_id: Optional specific post ID
        days: Number of days to look back (1-90)
    """
    if days < 1 or days > 90:
        raise HTTPException(status_code=400, detail="days must be between 1 and 90")

    factory = get_factory()
    config = get_config()

    try:
        conn = factory.create(platform.value, config)
        result = await conn.analytics(post_id=post_id, days=days)

        if isinstance(result, dict) and "error" in result:
            raise HTTPException(status_code=502, detail=result["error"])

        return schemas.AnalyticsResponse(
            platform=platform.value,
            metrics=result if isinstance(result, dict) else {},
            fetched_at=datetime.now(timezone.utc),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
