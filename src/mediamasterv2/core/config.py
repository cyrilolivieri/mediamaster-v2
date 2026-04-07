"""Configuration management for platform connectors."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class LinkedInConfig(BaseModel):
    """LinkedIn-specific configuration."""

    api_key: str = Field(alias="api_key", default="")
    postiz_url: str = Field(default="http://localhost:4000")
    workspace_id: str = Field(default="")


class TwitterConfig(BaseModel):
    """Twitter/X-specific configuration."""

    api_key: str = Field(alias="api_key", default="")
    api_secret: str = Field(alias="api_secret", default="")
    access_token: str = Field(default="")
    access_secret: str = Field(default="")
    postiz_url: str = Field(default="http://localhost:4000")


class InstagramConfig(BaseModel):
    """Instagram-specific configuration."""

    api_key: str = Field(alias="api_key", default="")
    postiz_url: str = Field(default="http://localhost:4000")
    username: str = Field(default="")


class YouTubeConfig(BaseModel):
    """YouTube-specific configuration."""

    client_secrets_path: str = Field(default="~/.config/mediamaster/client_secrets.json")
    credentials_path: str = Field(default="~/.config/mediamaster/youtube_credentials.json")
    channel_id: str = Field(default="")
    upload_bucket: str = Field(default="mediamaster-uploads")


class TikTokConfig(BaseModel):
    """TikTok-specific configuration."""

    api_key: str = Field(alias="api_key", default="")
    username: str = Field(default="")


class DiscordConfig(BaseModel):
    """Discord-specific configuration."""

    bot_token: str = Field(default="")
    default_channel_id: str = Field(default="")


class TelegramConfig(BaseModel):
    """Telegram-specific configuration."""

    bot_token: str = Field(default="")
    allowed_chat_ids: list[int] = Field(default_factory=list)


class PinterestConfig(BaseModel):
    """Pinterest-specific configuration."""

    access_token: str = Field(default="")
    board_id: str = Field(default="")


class TwitchConfig(BaseModel):
    """Twitch-specific configuration."""

    client_id: str = Field(default="")
    client_secret: str = Field(default="")
    channel_name: str = Field(default="")


class GlobalConfig(BaseModel):
    """Global MediaMaster configuration."""

    postiz_api_key: str = Field(default="")
    default_timeout: int = Field(default=30)
    max_retries: int = Field(default=3)
    log_level: str = Field(default="INFO")


@dataclass
class PlatformConfig:
    """Complete platform configuration container."""

    global_settings: GlobalConfig = field(default_factory=GlobalConfig)
    linkedin: LinkedInConfig = field(default_factory=LinkedInConfig)
    twitter: TwitterConfig = field(default_factory=TwitterConfig)
    instagram: InstagramConfig = field(default_factory=InstagramConfig)
    youtube: YouTubeConfig = field(default_factory=YouTubeConfig)
    tiktok: TikTokConfig = field(default_factory=TikTokConfig)
    discord: DiscordConfig = field(default_factory=DiscordConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    pinterest: PinterestConfig = field(default_factory=PinterestConfig)
    twitch: TwitchConfig = field(default_factory=TwitchConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlatformConfig:
        """Create from a flat or nested dictionary."""
        gc = GlobalConfig(**data.get("global", {}))
        return cls(
            global_settings=gc,
            linkedin=LinkedInConfig(**data.get("linkedin", {})),
            twitter=TwitterConfig(**data.get("twitter", {})),
            instagram=InstagramConfig(**data.get("instagram", {})),
            youtube=YouTubeConfig(**data.get("youtube", {})),
            tiktok=TikTokConfig(**data.get("tiktok", {})),
            discord=DiscordConfig(**data.get("discord", {})),
            telegram=TelegramConfig(**data.get("telegram", {})),
            pinterest=PinterestConfig(**data.get("pinterest", {})),
            twitch=TwitchConfig(**data.get("twitch", {})),
        )


def load_config(path: str | Path | None = None) -> PlatformConfig:
    """
    Load configuration from YAML file or environment variables.

    Priority: env vars > config file > defaults
    """
    if path is None:
        path = Path(os.environ.get("MEDIAMASTER_CONFIG", "~/.mediamaster/config.yaml"))

    path = Path(path).expanduser()
    data: dict[str, Any] = {}

    if path.exists():
        with open(path) as f:
            data = yaml.safe_load(f) or {}

    # Env var overrides
    if api_key := os.environ.get("POSTIZ_API_KEY"):
        data.setdefault("global", {})["postiz_api_key"] = api_key
    if yt_secrets := os.environ.get("YT_CLIENT_SECRETS"):
        data.setdefault("youtube", {})["client_secrets_path"] = yt_secrets
    if discord_token := os.environ.get("DISCORD_BOT_TOKEN"):
        data.setdefault("discord", {})["bot_token"] = discord_token
    if tg_token := os.environ.get("TELEGRAM_BOT_TOKEN"):
        data.setdefault("telegram", {})["bot_token"] = tg_token

    return PlatformConfig.from_dict(data)
