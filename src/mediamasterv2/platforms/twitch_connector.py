"""Twitch connector using twitchAPI."""

from __future__ import annotations

from typing import Any

from mediamasterv2.core.base import (
    BasePlatform,
    PlatformCapability,
    PostResult,
    ScheduleResult,
)
from mediamasterv2.core.factory import PlatformFactory


class TwitchConnector(BasePlatform):
    """
    Twitch connector using twitchAPI.

    Features:
    - Start/stop streams
    - Schedule broadcasts
    - Get stream analytics
    - Manage channel settings

    Requires: TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET
    """

    name = "twitch"
    capabilities: set[PlatformCapability] = {
        PlatformCapability.POST_VIDEO,  # streams
        PlatformCapability.ANALYTICS,
        PlatformCapability.LIVE,
    }

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.client_id = config.get("client_id", "")
        self.client_secret = config.get("client_secret", "")
        self.channel_name = config.get("channel_name", "")
        self._twitch: Any = None

    async def _health_check_impl(self) -> bool:
        try:
            twitch = await self._get_twitch()
            return bool(twitch)
        except Exception:
            return False

    async def _get_twitch(self) -> Any:
        if self._twitch is None:
            from twitchAPI.twitch import Twitch
            self._twitch = await Twitch(
                self.client_id,
                self.client_secret,
            )
        return self._twitch

    async def post(self, content: str, **kwargs: Any) -> PostResult:
        """Start a Twitch stream or send a chat message."""
        game_title = kwargs.get("game_title", "")
        stream_title = content

        try:
            twitch = await self._get_twitch()
            from twitchAPI.helper import TWITCH_AUTH_BASE_URL

            # Start a stream (requires streamer token)
            # Note: This is a placeholder — actual implementation needs
            # User OAuth token with channel:manage:broadcast scope
            return PostResult(
                platform=self.name,
                post_id=None,
                url=f"https://twitch.tv/{self.channel_name}",
                success=False,
                error="Stream start requires User OAuth token (not App token). "
                      "Use: twitchAPI.auth.UserAuthHandler",
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
        """Schedule a Twitch broadcast."""
        return ScheduleResult(
            platform=self.name,
            schedule_id=None,
            scheduled_at=scheduled_at,
            success=False,
            error="Twitch scheduling not yet implemented via API",
        )


PlatformFactory.register("twitch", TwitchConnector)
