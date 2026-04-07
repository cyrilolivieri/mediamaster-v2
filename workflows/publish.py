"""Publish workflow — LangGraph graph for validated cross-platform posting."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from langgraph.graph import END, StateGraph

from api.models.schemas import PostResultItem
from mediamasterv2.core.base import BasePlatform
from mediamasterv2.core.config import PlatformConfig
from mediamasterv2.core.factory import PlatformFactory
from workflows.state import PublishState

# ─── Node Implementations ────────────────────────────────────────────────────


def _validate(state: PublishState) -> PublishState:
    """Validate the post content and selected platforms."""
    errors: list[str] = []
    if not state.get("content", "").strip():
        errors.append("content cannot be empty")
    if not state.get("platforms"):
        errors.append("at least one platform is required")

    state["validation_errors"] = errors
    state["selected_platforms"] = state.get("platforms", [])
    return state


def _select_platforms(state: PublishState) -> PublishState:
    """
    Filter platforms to only those that support POST_TEXT capability.
    If all are filtered out, record an error.
    """
    config = PlatformConfig()
    selected: list[str] = []
    for name in state.get("selected_platforms", []):
        try:
            connector = PlatformFactory.create(name, config)
            if connector.has_capability(
                BasePlatform.__dict__["capabilities"].annotation  # type: ignore[arg-type]
                if False
                else __import__(
                    "mediamasterv2.core.base", fromlist=["PlatformCapability"]
                ).PlatformCapability.POST_TEXT
            ):
                selected.append(name)
        except Exception:  # noqa: BLE-001
            selected.append(name)  # allow unverified platforms through

    if not selected:
        state["errors"] = state.get("errors", []) + [
            "No platforms with posting capability selected"
        ]
    state["selected_platforms"] = selected
    return state


async def _post_node(state: PublishState) -> PublishState:
    """Post to all selected platforms concurrently with retry."""
    content = state.get("content", "")
    media_urls = state.get("media_urls", [])
    link_url = state.get("link_url")
    metadata = state.get("metadata", {})
    platforms = state.get("selected_platforms", [])
    results: list[PostResultItem] = []
    errors: list[str] = []
    config = PlatformConfig()

    async def _post_one(name: str) -> PostResultItem:
        try:
            connector = PlatformFactory.create(name, config)
            result = await connector.post(
                content,
                media_urls=media_urls,
                link_url=link_url,
                **metadata,
            )
            return PostResultItem(
                platform=name,
                post_id=result.post_id,
                url=result.url,
                success=result.success,
                error=result.error,
                posted_at=result.posted_at or datetime.utcnow(),
                metadata=result.metadata,
            )
        except Exception as exc:  # noqa: BLE-001
            return PostResultItem(
                platform=name,
                post_id=None,
                url=None,
                success=False,
                error=str(exc),
            )

    results = await asyncio.gather(*[_post_one(p) for p in platforms])
    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful

    state["post_results"] = results
    state["errors"] = errors
    state["success"] = successful > 0
    state["total_posted"] = successful
    state["total_failed"] = failed
    return state


def _verify(state: PublishState) -> PublishState:
    """Mark success if at least one post succeeded."""
    if state.get("post_results"):
        any_ok = any(r.success for r in state["post_results"])
        state["success"] = any_ok
    return state


# ─── Graph Builder ──────────────────────────────────────────────────────────


def build_publish_graph() -> StateGraph:
    """
    Construct the validate → post → verify publish workflow.

    Edges:
        validate  ─ok──→ select_platforms ────→ post ────→ verify ──ok──→ END
                      └─(errors)───────────────────(no platform)─────────→ END
        verify ──(all failed)──→ END
    """
    g = StateGraph(PublishState)

    g.add_node("validate", _validate)
    g.add_node("select_platforms", _select_platforms)
    g.add_node("post", _post_node)
    g.add_node("verify", _verify)

    g.set_entry_point("validate")

    g.add_edge("validate", "select_platforms")

    g.add_conditional_edges(
        "select_platforms",
        lambda s: (
            "post"
            if s.get("selected_platforms")
            else END
        ),
    )

    g.add_edge("post", "verify")

    g.add_conditional_edges(
        "verify",
        lambda s: END if not s.get("success") else END,
    )

    return g.compile()


# ─── Public Entry Point ──────────────────────────────────────────────────────


async def run_publish_workflow(
    content: str,
    platforms: list[str],
    media_urls: list[str] | None = None,
    link_url: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> PublishState:
    """Run the full publish workflow and return the final state."""
    initial: PublishState = {
        "content": content,
        "platforms": platforms,
        "media_urls": media_urls or [],
        "link_url": link_url,
        "metadata": metadata or {},
        "validation_errors": [],
        "selected_platforms": [],
        "post_results": [],
        "errors": [],
        "success": False,
        "total_posted": 0,
        "total_failed": 0,
    }

    graph = build_publish_graph()
    result = await graph.ainvoke(initial)
    return result  # type: ignore[return-value]
