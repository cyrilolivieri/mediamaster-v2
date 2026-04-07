"""TikTok connector (placeholder — API access requires special approval)."""

from __future__ import annotations

from typing import Any

from mediamasterv2.core.base import (
    BasePlatform,
    PlatformCapability,
    PostResult,
    ScheduleResult,
)
from mediamasterv2.core.factory import PlatformFactory


class TikTokConnector(BasePlatform):
    """
    TikTok connector (stub — TikTok Creator API requires special approval).

    References:
    - davidteather/TikTok-Api (unofficial, may break)
    - TikTok Ads API (requires business account)

    Status: STUB — Full implementation pending TikTok API approval.
    """

    name = "tiktok"
    capabilities: set[PlatformCapability] = {
        PlatformCapability.POST_VIDEO,
        PlatformCapability.POST_LINK,
    }

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.api_key = config.get("api_key", "")
        self.username = config.get("username", "")

    async def _health_check_impl(self) -> bool:
        return False  # Stub

    async def post(self, content: str, **kwargs: Any) -> PostResult:
        return PostResult(
            platform=self.name,
            post_id=None,
            url=None,
            success=False,
            error="TikTok API access requires special approval. "
                  "Track progress at: https://github.com/cyrilolivieri/mediamaster-v2/issues/3",
        )

    async def schedule(
        self, content: str, scheduled_at: Any, **kwargs: Any
    ) -> ScheduleResult:
        return ScheduleResult(
            platform=self.name,
            schedule_id=None,
            scheduled_at=scheduled_at,
            success=False,
            error="TikTok scheduling not available — API access pending",
        )


PlatformFactory.register("tiktok", TikTokConnector)
