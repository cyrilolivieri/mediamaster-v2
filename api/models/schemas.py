"""Pydantic request/response schemas for MediaMaster API."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class PlatformName(str, Enum):
    """Supported platform identifiers."""

    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    X = "x"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    DISCORD = "discord"
    TELEGRAM = "telegram"
    PINTEREST = "pinterest"
    TWITCH = "twitch"


# ─── Request Schemas ────────────────────────────────────────────────────────


class PostRequest(BaseModel):
    """Request to publish content to one or more platforms."""

    platforms: list[PlatformName] = Field(
        ..., min_length=1, description="Target platforms"
    )
    content: str = Field(..., min_length=1, max_length=10000)
    media_urls: list[str] = Field(default_factory=list)
    link_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("content cannot be empty or whitespace only")
        return v


class ScheduleRequest(BaseModel):
    """Request to schedule content for future publishing."""

    platforms: list[PlatformName] = Field(
        ..., min_length=1, description="Target platforms"
    )
    content: str = Field(..., min_length=1, max_length=10000)
    scheduled_at: datetime = Field(..., description="UTC timestamp to post")
    media_urls: list[str] = Field(default_factory=list)
    link_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("scheduled_at")
    @classmethod
    def must_be_future(cls, v: datetime) -> datetime:
        if v <= datetime.utcnow():
            raise ValueError("scheduled_at must be in the future")
        return v


# ─── Response Schemas ──────────────────────────────────────────────────────


class PostResultItem(BaseModel):
    """Result for a single platform post."""

    platform: str
    post_id: str | None
    url: str | None
    success: bool
    error: str | None = None
    posted_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PostResponse(BaseModel):
    """Response from a publish operation."""

    results: list[PostResultItem]
    total: int
    successful: int
    failed: int


class ScheduleResultItem(BaseModel):
    """Result for a single platform schedule."""

    platform: str
    schedule_id: str | None
    scheduled_at: datetime | None
    success: bool
    error: str | None = None


class ScheduleResponse(BaseModel):
    """Response from a schedule operation."""

    results: list[ScheduleResultItem]
    total: int
    successful: int
    failed: int


class AnalyticsDataPoint(BaseModel):
    """Single analytics metric."""

    metric: str
    value: float | int | str
    period: str | None = None


class PlatformHealth(BaseModel):
    """Health status for a single platform."""

    platform: str
    healthy: bool
    latency_ms: float | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    """Health check response for all platforms."""

    overall: str = Field(description="'healthy' | 'degraded' | 'unhealthy'")
    platforms: list[PlatformHealth]
    checked_at: datetime = Field(default_factory=datetime.utcnow)


class PlatformInfo(BaseModel):
    """Information about a registered platform."""

    name: str
    capabilities: list[str]
    enabled: bool = True


class PlatformsResponse(BaseModel):
    """List of available platforms."""

    platforms: list[PlatformInfo]
    total: int


class AnalyticsResponse(BaseModel):
    """Analytics data for a platform."""

    platform: str
    metrics: dict[str, Any]
    fetched_at: datetime
    error: str | None = None


class ErrorResponse(BaseModel):
    """Standardized error response."""

    detail: str
    error_code: str | None = None
    request_id: str | None = None
