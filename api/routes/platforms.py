"""Platform listing route."""

from __future__ import annotations

from fastapi import APIRouter

from api.models.schemas import PlatformInfo, PlatformsResponse
from mediamasterv2.core.base import PlatformCapability
from mediamasterv2.core.config import PlatformConfig
from mediamasterv2.core.factory import PlatformFactory

router = APIRouter(prefix="/api", tags=["platforms"])


@router.get(
    "/platforms",
    response_model=PlatformsResponse,
    summary="List available platforms",
)
async def list_platforms() -> PlatformsResponse:
    """
    Return all registered platform connectors with their capabilities.
    """
    config = PlatformConfig.load()
    platform_names = PlatformFactory.available_platforms()
    infos: list[PlatformInfo] = []

    for name in platform_names:
        try:
            connector = PlatformFactory.create(name, config)
            infos.append(
                PlatformInfo(
                    name=name,
                    capabilities=[c.name for c in connector.capabilities],
                    enabled=True,
                )
            )
        except Exception:  # noqa: BLE-001
            infos.append(
                PlatformInfo(name=name, capabilities=[], enabled=False)
            )

    return PlatformsResponse(platforms=infos, total=len(infos))
