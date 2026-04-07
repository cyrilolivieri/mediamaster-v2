"""Analytics workflow — LangGraph graph for cross-platform analytics."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from langgraph.graph import END, StateGraph

from api.models.schemas import AnalyticsDataPoint
from mediamasterv2.core.config import PlatformConfig
from mediamasterv2.core.factory import PlatformFactory
from workflows.state import AnalyticsState


def _fetch(state: AnalyticsState) -> AnalyticsState:
    """Fetch raw analytics data from the target platform."""
    platform = state.get("platform")
    if not platform:
        state["error"] = "No platform specified"
        state["success"] = False
        return state

    try:
        config = PlatformConfig()
        connector = PlatformFactory.create(platform, config)
        # Build kwargs from state
        kwargs: dict[str, Any] = {}
        if state.get("period"):
            kwargs["period"] = state["period"]
        if state.get("since"):
            kwargs["since"] = state["since"]
        if state.get("until"):
            kwargs["until"] = state["until"]

        result = connector.analytics(**kwargs)
        state["raw_data"] = result.metrics
        state["error"] = result.error
        state["success"] = result.error is None
    except Exception as exc:  # noqa: BLE-001
        state["error"] = str(exc)
        state["success"] = False

    return state


def _aggregate(state: AnalyticsState) -> AnalyticsState:
    """
    Transform raw metrics into structured data points.
    If raw_data is missing (platform not implemented), synthesize a stub response.
    """
    raw = state.get("raw_data")
    if raw is None:
        # Stub for platforms without analytics implementation
        state["aggregated"] = [
            AnalyticsDataPoint(metric="impressions", value=0, period="day"),
            AnalyticsDataPoint(metric="engagements", value=0, period="day"),
        ]
        return state

    aggregated: list[AnalyticsDataPoint] = []
    period = state.get("period") or "day"
    for key, value in raw.items():
        aggregated.append(
            AnalyticsDataPoint(metric=key, value=value, period=period)
        )

    state["aggregated"] = aggregated
    return state


def _analyze(state: AnalyticsState) -> AnalyticsState:
    """Derive simple insights from aggregated metrics."""
    insights: list[str] = []
    aggregated = state.get("aggregated", [])

    for pt in aggregated:
        if pt.metric in ("impressions", "views") and isinstance(pt.value, (int, float)):
            if pt.value > 10000:
                insights.append(f"High {pt.metric} detected ({pt.value})")
            elif pt.value == 0:
                insights.append(f"No {pt.metric} recorded — consider boosting")
        elif pt.metric in ("engagements", "likes") and isinstance(pt.value, (int, float)):
            ratio = pt.value / max(pt.value, 1)
            if ratio > 0.05:
                insights.append(f"Strong engagement rate ({ratio:.1%})")

    state["insights"] = insights
    return state


def _report(state: AnalyticsState) -> AnalyticsState:
    """Build the final analytics report."""
    platform = state.get("platform") or "unknown"
    report: dict[str, Any] = {
        "platform": platform,
        "generated_at": datetime.utcnow().isoformat(),
        "period": state.get("period") or "day",
        "metrics": [pt.model_dump() for pt in state.get("aggregated", [])],
        "insights": state.get("insights", []),
        "error": state.get("error"),
    }
    state["report"] = report
    return state


def build_analytics_graph() -> StateGraph:
    """
    Construct the fetch → aggregate → analyze → report analytics workflow.
    """
    g = StateGraph(AnalyticsState)

    g.add_node("fetch", _fetch)
    g.add_node("aggregate", _aggregate)
    g.add_node("analyze", _analyze)
    g.add_node("report", _report)

    g.set_entry_point("fetch")
    g.add_edge("fetch", "aggregate")
    g.add_edge("aggregate", "analyze")
    g.add_edge("analyze", "report")
    g.add_edge("report", END)

    return g.compile()


async def run_analytics_workflow(
    platform: str,
    period: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> AnalyticsState:
    """Run the full analytics workflow and return the final state."""
    initial: AnalyticsState = {
        "platform": platform,
        "period": period,
        "since": since,
        "until": until,
        "raw_data": None,
        "aggregated": [],
        "insights": [],
        "error": None,
        "report": None,
        "success": False,
    }

    graph = build_analytics_graph()
    result = await graph.ainvoke(initial)
    return result  # type: ignore[return-value]
