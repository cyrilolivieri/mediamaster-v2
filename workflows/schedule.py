"""Schedule workflow — LangGraph graph for time-aware cross-platform scheduling."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

from langgraph.graph import END, StateGraph

from api.models.schemas import ScheduleResultItem
from mediamasterv2.core.config import PlatformConfig
from mediamasterv2.core.factory import PlatformFactory
from workflows.state import ScheduleState


def _validate(state: ScheduleState) -> ScheduleState:
    """Validate schedule content and timestamp."""
    errors: list[str] = []
    if not state.get("content", "").strip():
        errors.append("content cannot be empty")
    if not state.get("platforms"):
        errors.append("at least one platform is required")
    sched = state.get("scheduled_at")
    if sched and sched <= datetime.utcnow():
        errors.append("scheduled_at must be in the future")

    state["validation_errors"] = errors
    return state


def _calculate_timing(state: ScheduleState) -> ScheduleState:
    """
    Apply platform-specific timing adjustments (e.g., off-peak windows,
    buffer between posts). Currently applies a 5-minute stagger.
    """
    scheduled_at = state.get("scheduled_at") or datetime.utcnow()
    platforms = state.get("platforms", [])
    adjustments: dict[str, datetime] = {}

    for i, name in enumerate(platforms):
        # Stagger posts by 5 minutes per platform
        offset = timedelta(minutes=i * 5)
        adjustments[name] = scheduled_at + offset

    state["timing_adjustments"] = adjustments
    return state


async def _schedule_node(state: ScheduleState) -> ScheduleState:
    """Schedule posts on all selected platforms concurrently."""
    content = state.get("content", "")
    media_urls = state.get("media_urls", [])
    link_url = state.get("link_url")
    metadata = state.get("metadata", {})
    adjustments = state.get("timing_adjustments", {})
    results: list[ScheduleResultItem] = []
    config = PlatformConfig()

    async def _sched_one(name: str) -> ScheduleResultItem:
        scheduled_at = adjustments.get(name)
        try:
            connector = PlatformFactory.create(name, config)
            result = await connector.schedule(content, scheduled_at, media_urls=media_urls, link_url=link_url, **metadata)
            return ScheduleResultItem(
                platform=name,
                schedule_id=result.schedule_id,
                scheduled_at=result.scheduled_at,
                success=result.success,
                error=result.error,
            )
        except Exception as exc:  # noqa: BLE-001
            return ScheduleResultItem(
                platform=name,
                schedule_id=None,
                scheduled_at=scheduled_at,
                success=False,
                error=str(exc),
            )

    results = await asyncio.gather(*[_sched_one(p) for p in adjustments])
    successful = sum(1 for r in results if r.success)

    state["schedule_results"] = results
    state["success"] = successful > 0
    state["total_scheduled"] = successful
    state["total_failed"] = len(results) - successful
    return state


def _confirm(state: ScheduleState) -> ScheduleState:
    """Final confirmation — mark success if any schedule succeeded."""
    if state.get("schedule_results"):
        state["success"] = any(r.success for r in state["schedule_results"])
    return state


def build_schedule_graph() -> StateGraph:
    """
    Construct the validate → calculate_timing → schedule → confirm schedule workflow.
    """
    g = StateGraph(ScheduleState)

    g.add_node("validate", _validate)
    g.add_node("calculate_timing", _calculate_timing)
    g.add_node("schedule", _schedule_node)
    g.add_node("confirm", _confirm)

    g.set_entry_point("validate")

    g.add_edge("validate", "calculate_timing")
    g.add_edge("calculate_timing", "schedule")
    g.add_edge("schedule", "confirm")

    g.add_conditional_edges(
        "confirm",
        lambda s: END if not s.get("success") else END,
    )

    return g.compile()


async def run_schedule_workflow(
    content: str,
    platforms: list[str],
    scheduled_at: datetime,
    media_urls: list[str] | None = None,
    link_url: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ScheduleState:
    """Run the full schedule workflow and return the final state."""
    initial: ScheduleState = {
        "content": content,
        "platforms": platforms,
        "scheduled_at": scheduled_at,
        "media_urls": media_urls or [],
        "link_url": link_url,
        "metadata": metadata or {},
        "validation_errors": [],
        "timing_adjustments": {},
        "schedule_results": [],
        "errors": [],
        "success": False,
        "total_scheduled": 0,
        "total_failed": 0,
    }

    graph = build_schedule_graph()
    result = await graph.ainvoke(initial)
    return result  # type: ignore[return-value]
