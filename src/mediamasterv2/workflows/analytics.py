"""Analytics workflow — fetch → aggregate → analyze → report."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from langgraph.graph import StateGraph, END


@dataclass
class AnalyticsState:
    """State for the analytics workflow."""

    platforms: list[str] = field(default_factory=list)
    post_id: str | None = None
    days: int = 7

    # Raw data per platform
    raw_data: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Fetch status
    fetched_platforms: list[str] = field(default_factory=list)
    failed_platforms: list[str] = field(default_factory=list)

    # Aggregated
    aggregated: dict[str, Any] = field(default_factory=dict)

    # Analysis
    analysis: dict[str, Any] = field(default_factory=dict)

    # Report
    report: dict[str, Any] = field(default_factory=dict)

    # Final
    overall_success: bool = False


def validate_analytics_request(state: AnalyticsState) -> AnalyticsState:
    """Validate analytics request parameters."""
    errors: list[str] = []

    if not state.platforms:
        errors.append("At least one platform must be specified")

    if state.days < 1 or state.days > 90:
        errors.append("days must be between 1 and 90")

    if errors:
        return AnalyticsState(
            **{k: v for k, v in state.__dict__.items() if k != "raw_data"},
            **{"raw_data": state.raw_data, "aggregated": {}, "analysis": {}, "report": {}},
        )

    return state


async def fetch_analytics(state: AnalyticsState) -> AnalyticsState:
    """
    Fetch analytics data from each platform concurrently.
    """
    from mediamasterv2.core.factory import PlatformFactory
    from mediamasterv2.core.config import load_config
    import asyncio

    factory = PlatformFactory()
    config = load_config()

    async def fetch_one(name: str) -> tuple[str, dict[str, Any], bool]:
        try:
            platform = factory.create(name, config)
            result = await platform.analytics(post_id=state.post_id, days=state.days)
            success = isinstance(result, dict) and "error" not in result
            return name, result if isinstance(result, dict) else {}, success
        except Exception as e:
            return name, {"error": str(e)}, False

    tasks = [fetch_one(name) for name in state.platforms]
    outcomes = await asyncio.gather(*tasks, return_exceptions=True)

    raw: dict[str, Any] = {}
    fetched: list[str] = []
    failed: list[str] = []

    for outcome in outcomes:
        if isinstance(outcome, Exception):
            continue
        name, data, success = outcome
        raw[name] = data
        if success:
            fetched.append(name)
        else:
            failed.append(name)

    return AnalyticsState(
        **{
            **state.__dict__,
            "raw_data": raw,
            "fetched_platforms": fetched,
            "failed_platforms": failed,
        }
    )


def aggregate_data(state: AnalyticsState) -> AnalyticsState:
    """
    Aggregate raw analytics into cross-platform totals.

    Extracts common metrics: views, likes, shares, comments, engagement_rate.
    """
    if not state.raw_data:
        return AnalyticsState(
            **{
                **state.__dict__,
                "aggregated": {},
            }
        )

    total_views = 0
    total_likes = 0
    total_comments = 0
    total_shares = 0
    platform_breakdown: dict[str, dict[str, Any]] = {}

    for platform, data in state.raw_data.items():
        if "error" in data:
            continue

        views = data.get("views", data.get("view_count", 0))
        likes = data.get("likes", data.get("like_count", 0))
        comments = data.get("comments", data.get("comment_count", 0))
        shares = data.get("shares", data.get("share_count", 0))

        total_views += int(views or 0)
        total_likes += int(likes or 0)
        total_comments += int(comments or 0)
        total_shares += int(shares or 0)

        platform_breakdown[platform] = {
            "views": views,
            "likes": likes,
            "comments": comments,
            "shares": shares,
        }

    total_engagements = total_likes + total_comments + total_shares
    engagement_rate = (
        round(total_engagements / total_views, 4) if total_views > 0 else 0.0
    )

    aggregated = {
        "total_views": total_views,
        "total_likes": total_likes,
        "total_comments": total_comments,
        "total_shares": total_shares,
        "total_engagements": total_engagements,
        "engagement_rate": engagement_rate,
        "platform_breakdown": platform_breakdown,
    }

    return AnalyticsState(**{**state.__dict__, "aggregated": aggregated})


def analyze_data(state: AnalyticsState) -> AnalyticsState:
    """
    Analyze aggregated data and produce insights.
    """
    agg = state.aggregated

    insights: list[str] = []
    top_platform = None
    best_performer = None

    if agg.get("platform_breakdown"):
        breakdown = agg["platform_breakdown"]
        top_platform = max(breakdown, key=lambda p: breakdown[p].get("views", 0))

        # Find best performing platform by engagement rate
        best_engagement = -1
        for platform, metrics in breakdown.items():
            views = max(metrics.get("views", 1), 1)
            engagements = metrics.get("likes", 0) + metrics.get("comments", 0) + metrics.get("shares", 0)
            rate = engagements / views
            if rate > best_engagement:
                best_engagement = rate
                best_performer = platform

        if top_platform:
            insights.append(f"Top platform by views: {top_platform} ({breakdown[top_platform].get('views', 0)} views)")
        if best_performer and best_performer != top_platform:
            insights.append(f"Best engagement rate: {best_performer}")

    if agg.get("engagement_rate", 0) > 0.05:
        insights.append("Above-average engagement rate — content resonates")
    elif agg.get("engagement_rate", 0) > 0:
        insights.append("Below-average engagement — consider improving CTAs")

    if agg.get("total_shares", 0) < agg.get("total_likes", 0) / 10:
        insights.append("Low share-to-like ratio — content may benefit from stronger hooks")

    analysis = {
        "insights": insights,
        "top_platform": top_platform,
        "best_performer": best_performer,
        "total_platforms_analyzed": len(agg.get("platform_breakdown", {})),
    }

    return AnalyticsState(**{**state.__dict__, "analysis": analysis})


def generate_report(state: AnalyticsState) -> AnalyticsState:
    """Generate the final analytics report."""
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period_days": state.days,
        "platforms_analyzed": len(state.fetched_platforms),
        "metrics": state.aggregated,
        "insights": state.analysis.get("insights", []),
        "top_platform": state.analysis.get("top_platform"),
        "failed_platforms": state.failed_platforms,
    }

    return AnalyticsState(
        **{
            **state.__dict__,
            "report": report,
            "overall_success": len(state.fetched_platforms) > 0,
        }
    )


def build_analytics_graph() -> StateGraph:
    """Build the analytics workflow StateGraph."""
    workflow = StateGraph(AnalyticsState)

    workflow.add_node("validate", validate_analytics_request)
    workflow.add_node("fetch_analytics", fetch_analytics)
    workflow.add_node("aggregate_data", aggregate_data)
    workflow.add_node("analyze_data", analyze_data)
    workflow.add_node("generate_report", generate_report)

    workflow.set_entry_point("validate")

    workflow.add_conditional_edges(
        "validate",
        lambda s: "fetch_analytics" if s.platforms else "generate_report",
        {
            "fetch_analytics": "fetch_analytics",
            "generate_report": "generate_report",
        },
    )

    workflow.add_edge("fetch_analytics", "aggregate_data")
    workflow.add_edge("aggregate_data", "analyze_data")
    workflow.add_edge("analyze_data", "generate_report")
    workflow.add_edge("generate_report", END)

    return workflow


async def run_analytics(
    platforms: list[str],
    post_id: str | None = None,
    days: int = 7,
) -> AnalyticsState:
    """Run the analytics workflow."""
    graph = build_analytics_graph()
    compiled = graph.compile()

    initial_state = AnalyticsState(
        platforms=platforms,
        post_id=post_id,
        days=days,
    )

    result = await compiled.ainvoke(initial_state)
    return result
