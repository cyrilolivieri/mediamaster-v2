"""Base abstract interface for all platform connectors."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Protocol, TypeVar

T = TypeVar("T")


class PlatformCapability(Enum):
    """Capabilities supported by a platform connector."""

    POST_TEXT = auto()
    POST_IMAGE = auto()
    POST_VIDEO = auto()
    POST_LINK = auto()
    SCHEDULE = auto()
    ANALYTICS = auto()
    ENGAGE = auto()
    STORIES = auto()
    REELS = auto()
    LIVE = auto()


@dataclass
class PostResult:
    """Result of a post operation."""

    platform: str
    post_id: str | None
    url: str | None
    success: bool
    error: str | None = None
    posted_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScheduleResult:
    """Result of a scheduling operation."""

    platform: str
    schedule_id: str | None
    scheduled_at: datetime | None
    success: bool
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalyticsResult:
    """Result of an analytics query."""

    platform: str
    metrics: dict[str, Any] = field(default_factory=dict)
    fetched_at: datetime | None = None
    error: str | None = None


@dataclass
class EngagementResult:
    """Result of an engagement action (like, comment, share)."""

    platform: str
    action: str
    target_id: str
    success: bool
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BasePlatform(ABC):
    """
    Abstract base class for all platform connectors.

    Subclasses must implement the core methods. Retry logic is applied
    automatically via the @retry decorators on post() and schedule().
    """

    name: str = "base"
    capabilities: set[PlatformCapability] = set()

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self._client: Any = None

    @abstractmethod
    async def post(self, content: str, **kwargs: Any) -> PostResult:
        """Post content to the platform. Must be implemented by subclasses."""
        ...

    @abstractmethod
    async def schedule(
        self, content: str, scheduled_at: datetime, **kwargs: Any
    ) -> ScheduleResult:
        """Schedule content for later posting."""
        ...

    async def analytics(self, **kwargs: Any) -> AnalyticsResult:
        """Fetch analytics for the account. Override in subclasses."""
        return AnalyticsResult(platform=self.name, error="Not implemented")

    async def engage(
        self, action: str, target_id: str, **kwargs: Any
    ) -> EngagementResult:
        """Perform an engagement action (like, comment, etc.)."""
        return EngagementResult(
            platform=self.name,
            action=action,
            target_id=target_id,
            success=False,
            error="Not implemented",
        )

    def has_capability(self, cap: PlatformCapability) -> bool:
        """Check if the platform supports a given capability."""
        return cap in self.capabilities

    async def health_check(self) -> bool:
        """Verify the platform connection is healthy."""
        try:
            return await self._health_check_impl()
        except Exception:
            return False

    @abstractmethod
    async def _health_check_impl(self) -> bool:
        """Internal health check implementation."""
        ...

    async def close(self) -> None:
        """Clean up resources."""
        self._client = None
