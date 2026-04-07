"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class PlatformName(str, Enum):
    """Supported platform names."""

    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    X = "x"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    DISCORD = "discord"
    TELEGRAM = "telegram"
    PINTEREST = "pinterest"
    TWITCH = "twitch"
    TIKTOK = "tiktok"


# ─── Post Schemas ───────────────────────────────────────────────────────────────


class PostRequest(BaseModel):
    """Request payload for posting content."""

    content: str = Field(..., min_length=1, max_length=5000, description="Post text content")
    platforms: list[PlatformName] = Field(
        ..., min_length=1, description="Target platforms"
    )
    media_urls: list[str] = Field(
        default_factory=list, max_length=10, description="Media URLs to attach"
    )
    title: str | None = Field(None, max_length=300, description="Optional title (YouTube)")
    tags: list[str] = Field(default_factory=list, max_length=30, description="Tags/keywords")
    privacy_status: str = Field(
        default="public",
        pattern="^(public|unlisted|private)$",
        description="Privacy for YouTube",
    )

    @field_validator("media_urls")
    @classmethod
    def validate_media_urls(cls, v: list[str]) -> list[str]:
        for url in v:
            if not url.startswith(("http://", "https://")):
                raise ValueError(f"Invalid URL: {url}")
        return v

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        return [tag.strip()[:50] for tag in v if tag.strip()]


class PostResponse(BaseModel):
    """Response after posting to platforms."""

    results: list[PostResultItem] = Field(default_factory=list)
    overall_success: bool
    total_platforms: int
    successful_platforms: int


class PostResultItem(BaseModel):
    """Result for a single platform."""

    platform: str
    post_id: str | None = None
    url: str | None = None
    success: bool
    error: str | None = None


# ─── Schedule Schemas ─────────────────────────────────────────────────────────


class ScheduleRequest(BaseModel):
    """Request payload for scheduling content."""

    content: str = Field(..., min_length=1, max_length=5000)
    platforms: list[PlatformName] = Field(..., min_length=1)
    scheduled_at: datetime = Field(..., description="UTC datetime to post")
    media_urls: list[str] = Field(default_factory=list)
    title: str | None = Field(None, max_length=300)
    tags: list[str] = Field(default_factory=list)

    @field_validator("scheduled_at")
    @classmethod
    def validate_future(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            # Assume UTC if naive
            from datetime import timezone
            v = v.replace(tzinfo=timezone.utc)
        return v

    @field_validator("media_urls")
    @classmethod
    def validate_media_urls(cls, v: list[str]) -> list[str]:
        for url in v:
            if not url.startswith(("http://", "https://")):
                raise ValueError(f"Invalid URL: {url}")
        return v


class ScheduleResponse(BaseModel):
    """Response after scheduling content."""

    results: list[ScheduleResultItem] = Field(default_factory=list)
    overall_success: bool
    total_platforms: int
    successful_platforms: int


class ScheduleResultItem(BaseModel):
    """Result for a single scheduled platform."""

    platform: str
    schedule_id: str | None = None
    scheduled_at: datetime | None = None
    success: bool
    error: str | None = None


# ─── Analytics Schemas ────────────────────────────────────────────────────────


class AnalyticsRequest(BaseModel):
    """Request for analytics data."""

    platform: PlatformName
    post_id: str | None = None
    days: int = Field(default=7, ge=1, le=90)


class AnalyticsResponse(BaseModel):
    """Analytics data response."""

    platform: str
    metrics: dict[str, Any]
    fetched_at: datetime


# ─── Health / Platforms Schemas ───────────────────────────────────────────────


class PlatformStatus(BaseModel):
    """Health status of a single platform."""

    name: str
    registered: bool
    healthy: bool | None = None
    capabilities: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    """Overall API health response."""

    status: str  # "healthy" | "degraded" | "unhealthy"
    total_platforms: int
    healthy_platforms: int
    platforms: list[PlatformStatus]


class PlatformsResponse(BaseModel):
    """List of available platforms."""

    platforms: list[PlatformStatus]


# ─── Error Schema ─────────────────────────────────────────────────────────────


class ErrorResponse(BaseModel):
    """Standardized error response."""

    detail: str
    error_code: str | None = None
