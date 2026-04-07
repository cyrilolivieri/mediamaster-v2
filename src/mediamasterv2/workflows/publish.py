"""Publish workflow — validate → select_platforms → post → verify."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from langgraph.graph import StateGraph, END
from langgraph.types import interrupt

from mediamasterv2.core.base import BasePlatform, PlatformCapability
from mediamasterv2.core.factory import PlatformFactory


# ─── State ────────────────────────────────────────────────────────────────────


@dataclass
class PublishState:
    """State passed between nodes in the publish workflow."""

    content: str = ""
    platforms: list[str] = field(default_factory=list)
    media_urls: list[str] = field(default_factory=list)
    title: str | None = None
    tags: list[str] = field(default_factory=list)
    privacy_status: str = "public"

    # Validation
    validation_error: str | None = None
    is_valid: bool = False

    # Per-platform results
    results: dict[str, dict[str, Any]] = field(default_factory=dict)
    successful_platforms: list[str] = field(default_factory=list)
    failed_platforms: list[str] = field(default_factory=list)

    # Verification
    verified_count: int = 0

    # Final
    overall_success: bool = False
    final_message: str = ""


# ─── Nodes ────────────────────────────────────────────────────────────────────


def validate(state: PublishState) -> PublishState:
    """
    Validate the content and platform selection.

    Checks:
    - Content is not empty and within length limits
    - At least one platform selected
    - Media URLs are valid (if provided)
    """
    errors: list[str] = []

    if not state.content or not state.content.strip():
        errors.append("Content cannot be empty")
    elif len(state.content) > 5000:
        errors.append(f"Content too long: {len(state.content)} chars (max 5000)")

    if not state.platforms:
        errors.append("At least one platform must be selected")

    for url in state.media_urls:
        if not url.startswith(("http://", "https://")):
            errors.append(f"Invalid media URL: {url}")

    if state.validation_error:
        errors.append(state.validation_error)

    if errors:
        return PublishState(
            **{
                **state.__dict__,
                "validation_error": "; ".join(errors),
                "is_valid": False,
            }
        )

    return PublishState(**{**state.__dict__, "is_valid": True})


def select_platforms(state: PublishState) -> PublishState:
    """
    Filter platforms based on capabilities and availability.

    Returns the same state with platforms filtered to only those
    that support the required content type.
    """
    factory = PlatformFactory()
    filtered: list[str] = []

    for name in state.platforms:
        try:
            # Skip if not registered
            if name not in factory.available_platforms():
                continue
            # We don't create instances here to avoid overhead;
            # we just validate registration
            filtered.append(name)
        except Exception:
            continue

    return PublishState(
        **{**state.__dict__, "platforms": filtered}
    )


async def post_to_platforms(state: PublishState) -> PublishState:
    """
    Post content to each selected platform via PlatformFactory.

    Posts are executed concurrently for efficiency.
    """
    factory = PlatformFactory()
    from mediamasterv2.core.config import load_config
    config = load_config()

    import asyncio

    async def post_one(name: str) -> tuple[str, dict[str, Any]]:
        try:
            platform = factory.create(name, config)
            kwargs: dict[str, Any] = {}
            if state.media_urls:
                kwargs["media_urls"] = state.media_urls
            if state.title:
                kwargs["title"] = state.title
            if state.tags:
                kwargs["tags"] = state.tags
            if state.privacy_status:
                kwargs["privacy_status"] = state.privacy_status

            result = await platform.post(state.content, **kwargs)
            return name, {
                "success": result.success,
                "post_id": result.post_id,
                "url": result.url,
                "error": result.error,
            }
        except Exception as e:
            return name, {
                "success": False,
                "post_id": None,
                "url": None,
                "error": str(e),
            }

    # Post concurrently
    tasks = [post_one(name) for name in state.platforms]
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

    return PublishState(
        **{
            **state.__dict__,
            "results": results,
            "successful_platforms": successful,
            "failed_platforms": failed,
        }
    )


def verify_results(state: PublishState) -> PublishState:
    """
    Verify that posts were created successfully.

    In a production system, this could poll the platform APIs
    to confirm the post exists with the expected content.
    """
    verified = len(state.successful_platforms)
    return PublishState(**{**state.__dict__, "verified_count": verified})


def finalize(state: PublishState) -> PublishState:
    """Finalize the workflow and produce the summary message."""
    total = len(state.platforms)
    ok = len(state.successful_platforms)

    if ok == total:
        msg = f"Successfully posted to all {total} platforms"
        overall = True
    elif ok > 0:
        msg = f"Posted to {ok}/{total} platforms. Failed: {', '.join(state.failed_platforms)}"
        overall = False
    else:
        msg = f"Failed to post to all {total} platforms"
        overall = False

    return PublishState(
        **{
            **state.__dict__,
            "overall_success": overall,
            "final_message": msg,
        }
    )


# ─── Graph ────────────────────────────────────────────────────────────────────


def build_publish_graph() -> StateGraph:
    """Build the publish workflow StateGraph."""
    workflow = StateGraph(PublishState)

    workflow.add_node("validate", validate)
    workflow.add_node("select_platforms", select_platforms)
    workflow.add_node("post_to_platforms", post_to_platforms)
    workflow.add_node("verify_results", verify_results)
    workflow.add_node("finalize", finalize)

    workflow.set_entry_point("validate")

    workflow.add_conditional_edges(
        "validate",
        lambda s: "select_platforms" if s.is_valid else "finalize",
        {
            "select_platforms": "select_platforms",
            "finalize": "finalize",
        },
    )

    workflow.add_edge("select_platforms", "post_to_platforms")
    workflow.add_edge("post_to_platforms", "verify_results")
    workflow.add_edge("verify_results", "finalize")
    workflow.add_edge("finalize", END)

    return workflow


# Convenience runner
async def run_publish(
    content: str,
    platforms: list[str],
    media_urls: list[str] | None = None,
    title: str | None = None,
    tags: list[str] | None = None,
    privacy_status: str = "public",
) -> PublishState:
    """Run the publish workflow with the given parameters."""
    graph = build_publish_graph()
    compiled = graph.compile()

    initial_state = PublishState(
        content=content,
        platforms=platforms,
        media_urls=media_urls or [],
        title=title,
        tags=tags or [],
        privacy_status=privacy_status,
    )

    result = await compiled.ainvoke(initial_state)
    return result
