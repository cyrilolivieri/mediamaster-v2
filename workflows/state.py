"""TypedDict state definitions for LangGraph workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Any, TypedDict

from api.models.schemas import (
    AnalyticsDataPoint,
    PlatformHealth,
    PostResultItem,
    ScheduleResultItem,
)


# ─── Publish Workflow State ──────────────────────────────────────────────────


class PublishState(TypedDict, total=False):
    """State carried through the publish workflow graph."""

    # Input fields
    content: str
    platforms: list[str]
    media_urls: list[str]
    link_url: str | None
    metadata: dict[str, Any]

    # Intermediate state
    validation_errors: list[str]
    selected_platforms: list[str]
    post_results: list[PostResultItem]
    errors: list[str]

    # Output
    success: bool
    total_posted: int
    total_failed: int


# ─── Schedule Workflow State ─────────────────────────────────────────────────


class ScheduleState(TypedDict, total=False):
    """State carried through the schedule workflow graph."""

    # Input fields
    content: str
    platforms: list[str]
    scheduled_at: datetime
    media_urls: list[str]
    link_url: str | None
    metadata: dict[str, Any]

    # Intermediate state
    validation_errors: list[str]
    timing_adjustments: dict[str, datetime]
    schedule_results: list[ScheduleResultItem]
    errors: list[str]

    # Output
    success: bool
    total_scheduled: int
    total_failed: int


# ─── Analytics Workflow State ───────────────────────────────────────────────


class AnalyticsState(TypedDict, total=False):
    """State carried through the analytics workflow graph."""

    # Input fields
    platform: str
    period: str | None
    since: datetime | None
    until: datetime | None

    # Intermediate state
    raw_data: dict[str, Any] | None
    aggregated: list[AnalyticsDataPoint]
    insights: list[str]
    error: str | None

    # Output
    report: dict[str, Any] | None
    success: bool
