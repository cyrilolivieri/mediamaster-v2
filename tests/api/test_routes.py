"""Tests for FastAPI routes."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient


# We need to mock the lifespan state before importing the app
@pytest.fixture(autouse=True)
def mock_lifespan_state():
    """Set up mock state for lifespan before importing routes."""
    from mediamasterv2.api import lifespan
    from mediamasterv2.core.factory import PlatformFactory
    from mediamasterv2.core.config import PlatformConfig

    factory = PlatformFactory()

    mock_config = MagicMock(spec=PlatformConfig)

    lifespan._state["factory"] = factory
    lifespan._state["config"] = mock_config

    yield

    lifespan._state.clear()


@pytest.fixture
def mock_factory_with_dummy():
    """Register a dummy platform for testing."""
    from mediamasterv2.core.factory import PlatformFactory
    from mediamasterv2.core.base import BasePlatform, PlatformCapability, PostResult, ScheduleResult

    class DummyTestPlatform(BasePlatform):
        name = "dummytest"
        capabilities = {PlatformCapability.POST_TEXT, PlatformCapability.SCHEDULE}

        async def post(self, content, **kwargs):
            return PostResult(platform=self.name, post_id="test123", url="https://test.com/123", success=True)

        async def schedule(self, content, scheduled_at, **kwargs):
            return ScheduleResult(
                platform=self.name,
                schedule_id="sched123",
                scheduled_at=scheduled_at,
                success=True,
            )

        async def _health_check_impl(self) -> bool:
            return True

    PlatformFactory._registry.clear()
    PlatformFactory.register("dummytest", DummyTestPlatform)
    yield


def test_post_request_validation():
    """Test that invalid payloads are rejected."""
    from mediamasterv2.api.schemas import PostRequest

    # Empty content should fail
    with pytest.raises(ValueError):
        PostRequest(content="", platforms=["linkedin"])

    # No platforms should fail
    with pytest.raises(ValueError):
        PostRequest(content="Hello", platforms=[])

    # Invalid URL should fail
    with pytest.raises(ValueError):
        PostRequest(content="Hello", platforms=["linkedin"], media_urls=["not-a-url"])

    # Valid request
    req = PostRequest(
        content="Hello world",
        platforms=["linkedin", "twitter"],
        media_urls=["https://example.com/img.jpg"],
    )
    assert req.content == "Hello world"
    assert len(req.platforms) == 2


def test_schedule_request_validation():
    """Test schedule request validation."""
    from mediamasterv2.api.schemas import ScheduleRequest

    future = datetime.now(timezone.utc) + timedelta(hours=2)

    req = ScheduleRequest(
        content="Scheduled post",
        platforms=["linkedin"],
        scheduled_at=future,
    )
    assert req.content == "Scheduled post"
    assert req.scheduled_at == future


def test_platform_status_schema():
    """Test PlatformStatus schema."""
    from mediamasterv2.api.schemas import PlatformStatus

    status = PlatformStatus(
        name="linkedin",
        registered=True,
        healthy=True,
        capabilities=["POST_TEXT", "POST_IMAGE"],
    )
    assert status.name == "linkedin"
    assert status.healthy is True


def test_error_response_schema():
    """Test ErrorResponse schema."""
    from mediamasterv2.api.schemas import ErrorResponse

    err = ErrorResponse(detail="Something went wrong", error_code="POST_001")
    assert err.detail == "Something went wrong"
    assert err.error_code == "POST_001"
