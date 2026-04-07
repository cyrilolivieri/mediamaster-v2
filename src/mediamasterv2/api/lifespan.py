"""FastAPI lifespan manager — initializes platform connectors on startup."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from mediamasterv2.core.config import load_config, PlatformConfig
from mediamasterv2.core.factory import PlatformFactory
from mediamasterv2.platforms.postiz_adapter import PostizAdapter
from mediamasterv2.platforms.youtube_connector import YouTubeConnector
from mediamasterv2.platforms.discord_bot import DiscordConnector
from mediamasterv2.platforms.telegram_bot import TelegramConnector
from mediamasterv2.platforms.pinterest_connector import PinterestConnector
from mediamasterv2.platforms.twitch_connector import TwitchConnector
from mediamasterv2.platforms.tiktok_connector import TikTokConnector


# Module-level state for dependency injection
_state: dict = {}


def get_factory() -> PlatformFactory:
    return _state["factory"]


def get_config() -> PlatformConfig:
    return _state["config"]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize platform registry and config on startup."""
    # Register all connectors
    # (Import side-effects register them with PlatformFactory)
    # Ensure they're all imported
    _ = (
        PostizAdapter,
        YouTubeConnector,
        DiscordConnector,
        TelegramConnector,
        PinterestConnector,
        TwitchConnector,
        TikTokConnector,
    )

    # Load configuration
    config = load_config()

    factory = PlatformFactory()

    _state["factory"] = factory
    _state["config"] = config

    yield

    # Cleanup: close all platform connections
    for name in factory.available_platforms():
        try:
            platform = factory.create(name, config)
            await platform.close()
        except Exception:
            pass

    _state.clear()
