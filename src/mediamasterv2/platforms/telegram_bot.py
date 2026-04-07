"""Telegram bot connector using python-telegram-bot."""

from __future__ import annotations

from typing import Any

from mediamasterv2.core.base import (
    BasePlatform,
    PlatformCapability,
    PostResult,
    ScheduleResult,
)
from mediamasterv2.core.factory import PlatformFactory


class TelegramConnector(BasePlatform):
    """
    Telegram bot connector using python-telegram-bot.

    Features:
    - Send messages to chats
    - Media (photos, videos, documents)
    - Inline keyboards and callbacks
    - Groups and channels support

    Requires: TELEGRAM_BOT_TOKEN
    """

    name = "telegram"
    capabilities: set[PlatformCapability] = {
        PlatformCapability.POST_TEXT,
        PlatformCapability.POST_IMAGE,
        PlatformCapability.POST_VIDEO,
        PlatformCapability.POST_LINK,
    }

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.bot_token = config.get("bot_token", "")
        self.allowed_chat_ids = set(config.get("allowed_chat_ids", []))
        self._app: Any = None

    async def _health_check_impl(self) -> bool:
        try:
            from telegram import Bot
            bot = Bot(token=self.bot_token)
            await bot.get_me()
            return True
        except Exception:
            return False

    async def post(self, content: str, **kwargs: Any) -> PostResult:
        """Send a message via Telegram bot."""
        from telegram import Bot

        chat_id = kwargs.get("chat_id")
        photo = kwargs.get("photo")
        video = kwargs.get("video")
        document = kwargs.get("document")
        reply_markup = kwargs.get("reply_markup")

        try:
            bot = Bot(token=self.bot_token)

            if photo:
                msg = await bot.send_photo(
                    chat_id=chat_id or self.allowed_chat_ids.pop(),
                    photo=photo,
                    caption=content,
                    reply_markup=reply_markup,
                )
            elif video:
                msg = await bot.send_video(
                    chat_id=chat_id or self.allowed_chat_ids.pop(),
                    video=video,
                    caption=content,
                    reply_markup=reply_markup,
                )
            elif document:
                msg = await bot.send_document(
                    chat_id=chat_id or self.allowed_chat_ids.pop(),
                    document=document,
                    caption=content,
                    reply_markup=reply_markup,
                )
            else:
                msg = await bot.send_message(
                    chat_id=chat_id or self.allowed_chat_ids.pop(),
                    text=content,
                    reply_markup=reply_markup,
                )

            return PostResult(
                platform=self.name,
                post_id=str(msg.message_id),
                url=f"https://t.me/c/{msg.chat.id}/{msg.message_id}",
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
        """Telegram supports message scheduling via edit_time param."""
        return ScheduleResult(
            platform=self.name,
            schedule_id=None,
            scheduled_at=scheduled_at,
            success=False,
            error="Telegram scheduling requires python-telegram-bot >= 20 with JobQueue",
        )


PlatformFactory.register("telegram", TelegramConnector)
