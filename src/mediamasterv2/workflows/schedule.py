"""Schedule workflow — validate → calculate_timing → schedule → confirm."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from langgraph.graph import StateGraph, END


@dataclass
class ScheduleState:
    """State for the schedule workflow."""

    content: str = ""
    platforms: list[str] = field(default_factory=list)
    scheduled_at: datetime | None = None
    media_urls: list[str] = field(default_factory=list)
    title: str | None = None
    tags: list[str] = field(default_factory=list)

    # Validation
    validation_error: str | None = None
    is_valid: bool = False

    # Timing analysis
    time_until_post: timedelta | None = None
    timing_warning: str | None = None

    # Results
    results: dict[str, dict[str, Any]] = field(default_factory=dict)
    successful_platforms: list[str] = field(default_factory=list)
    failed_platforms: list[str] = field(default_factory=list)

    # Final
    overall_success: bool = False
    final_message: str = ""


def validate_schedule(state: ScheduleState) -> ScheduleState:
    """Validate content and schedule parameters."""
    errors: list[str] = []

    if not state.content or not state.content.strip():
        errors.append("Content cannot be empty")

    if not state.platforms:
        errors.append("At least one platform must be selected")

    if state.scheduled_at is None:
        errors.append("scheduled_at is required")
    else:
        now = datetime.now(timezone.utc)
        sched = state.scheduled_at
        if sched.tzinfo is None:
            sched = sched.replace(tzinfo=timezone.utc)
        if sched <= now:
            errors.append("scheduled_at must be in the future")

    for url in state.media_urls:
        if not url.startswith(("http://", "https://")):
            errors.append(f"Invalid media URL: {url}")

    if errors:
        return ScheduleState(
            **{
                **state.__dict__,
                "validation_error": "; ".join(errors),
                "is_valid": False,
            }
        )

    return ScheduleState(**{**state.__dict__, "is_valid": True})


def calculate_timing(state: ScheduleState) -> ScheduleState:
    """
    Analyze timing and produce warnings for suboptimal posting times.

    Warnings:
    - Less than 15 min away: "very short notice"
    - More than 30 days: "very long horizon"
    - Weekend vs weekday considerations (placeholder)
    """
    if not state.is_valid or state.scheduled_at is None:
        return state

    now = datetime.now(timezone.utc)
    sched = state.scheduled_at
    if sched.tzinfo is None:
        sched = sched.replace(tzinfo=timezone.utc)

    delta = sched - now
    warning: str | None = None

    if delta < timedelta(minutes=15):
        warning = "Very short notice — platform rate limits may cause failure"
    elif delta > timedelta(days=30):
        warning = "Long horizon — platform limits may change before posting"

    return ScheduleState(
        **{
            **state.__dict__,
            "time_until_post": delta,
            "timing_warning": warning,
        }
    )


async def schedule_on_platforms(state: ScheduleState) -> ScheduleState:
    """
    Schedule content on each platform concurrently.
    """
    from mediamasterv2.core.factory import PlatformFactory
    from mediamasterv2.core.config import load_config
    import asyncio

    factory = PlatformFactory()
    config = load_config()

    async def sched_one(name: str) -> tuple[str, dict[str, Any]]:
        try:
            platform = factory.create(name, config)
            kwargs: dict[str, Any] = {}
            if state.media_urls:
                kwargs["media_urls"] = state.media_urls
            if state.title:
                kwargs["title"] = state.title
            if state.tags:
                kwargs["tags"] = state.tags

            result = await platform.schedule(state.content, state.scheduled_at, **kwargs)
            return name, {
                "success": result.success,
                "schedule_id": result.schedule_id,
                "scheduled_at": str(result.scheduled_at),
                "error": result.error,
            }
        except Exception as e:
            return name, {
                "success": False,
                "schedule_id": None,
                "scheduled_at": None,
                "error": str(e),
            }

    tasks = [sched_one(name) for name in state.platforms]
    outcomes = await asyncio.gather(*tasks, return_exceptions=True)

    results: dict[str, Any] = {}
    successful: list[str] = []
    failed: list[str] = []

    for outcome in outcomes:
        if isinstance(outcome, Exception):
            continue
        name, result = outcome
        results[name] = result
        if result["success"]:
            successful.append(name)
        else:
            failed.append(name)

    return ScheduleState(
        **{
            **state.__dict__,
            "results": results,
            "successful_platforms": successful,
            "failed_platforms": failed,
        }
    )


def confirm(state: ScheduleState) -> ScheduleState:
    """Finalize and produce confirmation message."""
    total = len(state.platforms)
    ok = len(state.successful_platforms)

    if ok == total:
        msg = f"All {total} scheduled successfully for {state.scheduled_at}"
        overall = True
    elif ok > 0:
        msg = f"Scheduled {ok}/{total} for {state.scheduled_at}. Failed: {', '.join(state.failed_platforms)}"
        overall = False
    else:
        msg = f"Failed to schedule on all {total} platforms"
        overall = False

    return ScheduleState(
        **{
            **state.__dict__,
            "overall_success": overall,
            "final_message": msg,
        }
    )


def build_schedule_graph() -> StateGraph:
    """Build the schedule workflow StateGraph."""
    workflow = StateGraph(ScheduleState)

    workflow.add_node("validate", validate_schedule)
    workflow.add_node("calculate_timing", calculate_timing)
    workflow.add_node("schedule_on_platforms", schedule_on_platforms)
    workflow.add_node("confirm", confirm)

    workflow.set_entry_point("validate")

    workflow.add_conditional_edges(
        "validate",
        lambda s: "calculate_timing" if s.is_valid else "confirm",
        {
            "calculate_timing": "calculate_timing",
            "confirm": "confirm",
        },
    )

    workflow.add_edge("calculate_timing", "schedule_on_platforms")
    workflow.add_edge("schedule_on_platforms", "confirm")
    workflow.add_edge("confirm", END)

    return workflow


async def run_schedule(
    content: str,
    platforms: list[str],
    scheduled_at: datetime,
    media_urls: list[str] | None = None,
    title: str | None = None,
    tags: list[str] | None = None,
) -> ScheduleState:
    """Run the schedule workflow."""
    graph = build_schedule_graph()
    compiled = graph.compile()

    initial_state = ScheduleState(
        content=content,
        platforms=platforms,
        scheduled_at=scheduled_at,
        media_urls=media_urls or [],
        title=title,
        tags=tags or [],
    )

    result = await compiled.advance(initial_state)
    return result
