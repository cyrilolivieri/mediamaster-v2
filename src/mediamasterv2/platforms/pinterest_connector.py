"""Pinterest connector using pinterest-python-sdk."""

from __future__ import annotations

from typing import Any

from mediamasterv2.core.base import (
    BasePlatform,
    PlatformCapability,
    PostResult,
    ScheduleResult,
)
from mediamasterv2.core.factory import PlatformFactory


class PinterestConnector(BasePlatform):
    """
    Pinterest connector using pinterest-python-sdk.

    Features:
    - Create pins on boards
    - Upload images with descriptions
    - Board management

    Requires: PINTEREST_ACCESS_TOKEN
    """

    name = "pinterest"
    capabilities: set[PlatformCapability] = {
        PlatformCapability.POST_IMAGE,
        PlatformCapability.POST_LINK,
        PlatformCapability.SCHEDULE,
    }

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.access_token = config.get("access_token", "")
        self.board_id = config.get("board_id", "")

    async def _health_check_impl(self) -> bool:
        try:
            import pinterest
            return bool(self.access_token)
        except Exception:
            return False

    async def post(self, content: str, **kwargs: Any) -> PostResult:
        """Create a Pin on Pinterest."""
        board_id = kwargs.get("board_id", self.board_id)
        image_url = kwargs.get("image_url", "")
        link = kwargs.get("link", "")

        try:
            import pinterest

            api = pinterest.PinterestApi(token=self.access_token)

            pin = api.create_pin(
                board_id=board_id,
                note=content,
                image_url=image_url,
                link=link,
            )

            return PostResult(
                platform=self.name,
                post_id=pin.get("id"),
                url=pin.get("url"),
                success=True,
            )

        except Exception as e:
            return PostResult(
                platform=self.name,
                post_id=None,
                url=None,
                success=False,
                error=str(e),
            )

    async def schedule(
        self, content: str, scheduled_at: Any, **kwargs: Any
    ) -> ScheduleResult:
        """Schedule a pin for later publishing."""
        return ScheduleResult(
            platform=self.name,
            schedule_id=None,
            scheduled_at=scheduled_at,
            success=False,
            error="Pinterest scheduling via API not yet implemented",
        )


PlatformFactory.register("pinterest", PinterestConnector)
