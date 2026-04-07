"""Health check route — verifies all registered platform connectors."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse

from api.models.schemas import HealthResponse, PlatformHealth
from mediamasterv2.core.base import BasePlatform
from mediamasterv2.core.config import PlatformConfig
from mediamasterv2.core.factory import PlatformFactory

router = APIRouter(prefix="/api", tags=["health"])


def _build_config() -> PlatformConfig:
    """Load config from YAML with env-var overrides."""
    try:
        return PlatformConfig.load()
    except Exception:
        # Return empty config so health check can still report which platforms loaded
        return PlatformConfig()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check all platforms",
    responses={
        200: {"description": "Overall health status"},
    },
)
async def health_check() -> HealthResponse:
    """
    Ping every registered platform connector and return latency / status.

    Returns 'healthy' if all platforms respond, 'degraded' if some fail,
    'unhealthy' if none respond.
    """
    config = _build_config()
    platform_list = PlatformFactory.available_platforms()
    health_results: list[PlatformHealth] = []
    healthy_count = 0

    for name in platform_list:
        try:
            connector = PlatformFactory.create(name, config)
            start = time.perf_counter()
            ok = await connector.health_check()
            elapsed_ms = (time.perf_counter() - start) * 1000

            health_results.append(
                PlatformHealth(
                    platform=name,
                    healthy=ok,
                    latency_ms=round(elapsed_ms, 2),
                    error=None,
                )
            )
            if ok:
                healthy_count += 1
        except Exception as exc:  # noqa: BLE-001
            health_results.append(
                PlatformHealth(
                    platform=name,
                    healthy=False,
                    latency_ms=None,
                    error=str(exc),
                )
            )

    total = len(platform_list)
    if total == 0:
        overall = "unhealthy"
    elif healthy_count == total:
        overall = "healthy"
    elif healthy_count > 0:
        overall = "degraded"
    else:
        overall = "unhealthy"

    return HealthResponse(
        overall=overall,
        platforms=health_results,
        checked_at=datetime.utcnow(),
    )
