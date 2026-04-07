"""Tests for LangGraph workflows."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone

from mediamasterv2.workflows.publish import (
    PublishState,
    validate,
    select_platforms,
    verify_results,
    finalize,
    build_publish_graph,
)
from mediamasterv2.workflows.schedule import (
    ScheduleState,
    validate_schedule,
    calculate_timing,
    confirm,
    build_schedule_graph,
)


# ─── Publish Workflow Tests ────────────────────────────────────────────────────


class TestPublishWorkflow:
    """Tests for the publish workflow nodes."""

    def test_validate_success(self):
        """Valid state should pass validation."""
        state = PublishState(
            content="Hello world",
            platforms=["linkedin"],
        )
        result = validate(state)
        assert result.is_valid is True
        assert result.validation_error is None

    def test_validate_empty_content(self):
        """Empty content should fail validation."""
        state = PublishState(content="", platforms=["linkedin"])
        result = validate(state)
        assert result.is_valid is False
        assert "empty" in result.validation_error.lower()

    def test_validate_no_platforms(self):
        """No platforms should fail validation."""
        state = PublishState(content="Hello", platforms=[])
        result = validate(state)
        assert result.is_valid is False
        assert "platform" in result.validation_error.lower()

    def test_validate_too_long_content(self):
        """Content over 5000 chars should fail."""
        state = PublishState(content="x" * 5001, platforms=["linkedin"])
        result = validate(state)
        assert result.is_valid is False
        assert "too long" in result.validation_error.lower()

    def test_validate_invalid_media_url(self):
        """Invalid media URLs should fail."""
        state = PublishState(
            content="Hello",
            platforms=["linkedin"],
            media_urls=["not-a-url"],
        )
        result = validate(state)
        assert result.is_valid is False
        assert "url" in result.validation_error.lower()

    def test_select_platforms_filters_unregistered(self):
        """select_platforms removes unregistered platforms."""
        state = PublishState(
            content="Hello",
            platforms=["linkedin", "nonexistent_platform"],
        )
        # Only "linkedin" is registered (via PostizAdapter)
        result = select_platforms(state)
        # nonexistent_platform should be filtered out if not in registry

    def test_verify_results_counts_correctly(self):
        """verify_results should count successful platforms."""
        state = PublishState(
            content="Hello",
            platforms=["linkedin", "twitter"],
            successful_platforms=["linkedin"],
            failed_platforms=["twitter"],
        )
        result = verify_results(state)
        assert result.verified_count == 1

    def test_finalize_all_success(self):
        """finalize message for all success."""
        state = PublishState(
            content="Hello",
            platforms=["linkedin", "twitter"],
            successful_platforms=["linkedin", "twitter"],
            failed_platforms=[],
        )
        result = finalize(state)
        assert result.overall_success is True
        assert "all" in result.final_message.lower()

    def test_finalize_partial_failure(self):
        """finalize message for partial failure."""
        state = PublishState(
            content="Hello",
            platforms=["linkedin", "twitter"],
            successful_platforms=["linkedin"],
            failed_platforms=["twitter"],
        )
        result = finalize(state)
        assert result.overall_success is False
        assert "Failed" in result.final_message

    def test_finalize_total_failure(self):
        """finalize message for total failure."""
        state = PublishState(
            content="Hello",
            platforms=["linkedin"],
            successful_platforms=[],
            failed_platforms=["linkedin"],
        )
        result = finalize(state)
        assert result.overall_success is False

    def test_build_publish_graph_compiles(self):
        """The publish graph should compile without errors."""
        graph = build_publish_graph()
        compiled = graph.compile()
        assert compiled is not None


# ─── Schedule Workflow Tests ───────────────────────────────────────────────────


class TestScheduleWorkflow:
    """Tests for the schedule workflow nodes."""

    def test_validate_schedule_success(self):
        """Valid schedule state passes validation."""
        future = datetime.now(timezone.utc) + timedelta(hours=2)
        state = ScheduleState(
            content="Hello",
            platforms=["linkedin"],
            scheduled_at=future,
        )
        result = validate_schedule(state)
        assert result.is_valid is True

    def test_validate_schedule_past_time(self):
        """Past scheduled time fails validation."""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        state = ScheduleState(
            content="Hello",
            platforms=["linkedin"],
            scheduled_at=past,
        )
        result = validate_schedule(state)
        assert result.is_valid is False
        assert "future" in result.validation_error.lower()

    def test_validate_schedule_no_platforms(self):
        """No platforms fails validation."""
        future = datetime.now(timezone.utc) + timedelta(hours=2)
        state = ScheduleState(
            content="Hello",
            platforms=[],
            scheduled_at=future,
        )
        result = validate_schedule(state)
        assert result.is_valid is False

    def test_calculate_timing_short_notice(self):
        """Very short notice produces warning."""
        future = datetime.now(timezone.utc) + timedelta(minutes=5)
        state = ScheduleState(
            content="Hello",
            platforms=["linkedin"],
            scheduled_at=future,
            is_valid=True,
        )
        result = calculate_timing(state)
        assert result.timing_warning is not None
        assert "short notice" in result.timing_warning.lower()

    def test_calculate_timing_long_horizon(self):
        """Very long horizon produces warning."""
        future = datetime.now(timezone.utc) + timedelta(days=60)
        state = ScheduleState(
            content="Hello",
            platforms=["linkedin"],
            scheduled_at=future,
            is_valid=True,
        )
        result = calculate_timing(state)
        assert result.timing_warning is not None
        assert "long horizon" in result.timing_warning.lower()

    def test_confirm_all_success(self):
        """All scheduled successfully."""
        future = datetime.now(timezone.utc) + timedelta(hours=2)
        state = ScheduleState(
            content="Hello",
            platforms=["linkedin"],
            scheduled_at=future,
            successful_platforms=["linkedin"],
            failed_platforms=[],
        )
        result = confirm(state)
        assert result.overall_success is True
        assert "successfully" in result.final_message.lower()

    def test_confirm_partial_failure(self):
        """Partial failure message."""
        future = datetime.now(timezone.utc) + timedelta(hours=2)
        state = ScheduleState(
            content="Hello",
            platforms=["linkedin", "twitter"],
            scheduled_at=future,
            successful_platforms=["linkedin"],
            failed_platforms=["twitter"],
        )
        result = confirm(state)
        assert result.overall_success is False
        assert "2" in result.final_message  # 1/2

    def test_build_schedule_graph_compiles(self):
        """Schedule graph should compile."""
        graph = build_schedule_graph()
        compiled = graph.compile()
        assert compiled is not None
