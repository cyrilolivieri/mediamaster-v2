"""Discord bot connector using discord.py."""

from __future__ import annotations

from typing import Any

from mediamasterv2.core.base import (
    BasePlatform,
    PlatformCapability,
    PostResult,
    ScheduleResult,
)
from mediamasterv2.core.factory import PlatformFactory


class DiscordConnector(BasePlatform):
    """
    Discord bot connector using discord.py.

    Features:
    - Post messages to channels
    - Send embeds with rich formatting
    - Manage webhooks
    - Server/channel management

    Requires: DISCORD_BOT_TOKEN
    """

    name = "discord"
    capabilities: set[PlatformCapability] = {
        PlatformCapability.POST_TEXT,
        PlatformCapability.POST_IMAGE,
        PlatformCapability.POST_LINK,
        PlatformCapability.ENGAGE,
    }

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.bot_token = config.get("bot_token", "")
        self.default_channel_id = config.get("default_channel_id", "")
        self._client: Any = None

    async def _health_check_impl(self) -> bool:
        try:
            import discord
            if self._client and self._client.is_ready():
                return True
            return False
        except Exception:
            return False

    async def post(self, content: str, **kwargs: Any) -> PostResult:
        """Send a message to a Discord channel."""
        import discord

        channel_id = kwargs.get("channel_id", self.default_channel_id)
        embed = kwargs.get("embed")
        file_paths = kwargs.get("files", [])

        try:
            client = await self._get_client()

            channel = await client.fetch_channel(int(channel_id))

            if embed:
                msg = await channel.send(content, embed=embed)
            elif file_paths:
                from discord import File
                files = [File(fp) for fp in file_paths]
                msg = await channel.send(content, files=files)
            else:
                msg = await channel.send(content)

            return PostResult(
                platform=self.name,
                post_id=str(msg.id),
                url=msg.jump_url,
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
        """Discord scheduling is not natively supported; use a job queue."""
        return ScheduleResult(
            platform=self.name,
            schedule_id=None,
            scheduled_at=scheduled_at,
            success=False,
            error="Use an external job queue (e.g. Celery, RQ) for Discord scheduling",
        )

    async def _get_client(self) -> Any:
        import discord

        if self._client is None or not self._client.is_ready():
            self._client = discord.Client(intents=discord.Intents.default())
            await self._client.start(self.bot_token)
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.close()


PlatformFactory.register("discord", DiscordConnector)
