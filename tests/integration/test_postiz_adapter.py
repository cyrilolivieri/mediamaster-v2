"""Integration tests for Postiz adapter."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from mediamasterv2.core.base import PostResult, ScheduleResult
from mediamasterv2.platforms.postiz_adapter import PostizAdapter


@pytest.fixture
def adapter():
    """Create a PostizAdapter with test config."""
    config = {
        "api_key": "test_api_key",
        "postiz_url": "http://localhost:4000",
        "workspace_id": "test_workspace",
    }
    return PostizAdapter(config)


def test_adapter_initialization(adapter):
    assert adapter.name == "postiz"
    assert adapter.api_key == "test_api_key"
    assert adapter.workspace_id == "test_workspace"
    from mediamasterv2.core.base import PlatformCapability
    assert adapter.has_capability(PlatformCapability.POST_TEXT)


def test_adapter_has_required_capabilities(adapter):
    from mediamasterv2.core.base import PlatformCapability
    assert adapter.has_capability(PlatformCapability.POST_TEXT)
    assert adapter.has_capability(PlatformCapability.POST_IMAGE)
    assert adapter.has_capability(PlatformCapability.SCHEDULE)
    assert adapter.has_capability(PlatformCapability.ANALYTICS)


@pytest.mark.asyncio
async def test_post_success(adapter):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "post_123",
        "url": "https://postiz.app/post/123",
    }
    mock_response.raise_for_status = MagicMock()

    with patch.object(adapter, "_get_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = await adapter.post(
            "Hello from Postiz!",
            networks=["linkedin", "twitter"],
        )

        assert result.success is True
        assert result.post_id == "post_123"
        assert result.url == "https://postiz.app/post/123"
        assert "linkedin" in result.metadata["networks"]
        mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_post_http_error(adapter):
    import httpx

    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    mock_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "401", request=MagicMock(), response=mock_response
        )
    )

    with patch.object(adapter, "_get_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = await adapter.post("Test", networks=["linkedin"])

        assert result.success is False
        assert "401" in result.error


@pytest.mark.asyncio
async def test_schedule_success(adapter):
    future = datetime.utcnow() + timedelta(hours=2)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "sched_456",
    }
    mock_response.raise_for_status = MagicMock()

    with patch.object(adapter, "_get_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = await adapter.schedule(
            "Scheduled post",
            scheduled_at=future,
            networks=["twitter"],
        )

        assert result.success is True
        assert result.schedule_id == "sched_456"
        assert result.scheduled_at == future


@pytest.mark.asyncio
async def test_engage_success(adapter):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"action": "like", "targetId": "post123"}
    mock_response.raise_for_status = MagicMock()

    with patch.object(adapter, "_get_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = await adapter.engage("like", "post123")

        assert result.success is True
        assert result.action == "like"
        assert result.target_id == "post123"


@pytest.mark.asyncio
async def test_analytics(adapter):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"views": 1000, "likes": 50}
    mock_response.raise_for_status = MagicMock()

    with patch.object(adapter, "_get_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = await adapter.analytics()

        assert result["views"] == 1000


@pytest.mark.asyncio
async def test_close(adapter):
    mock_client = AsyncMock()
    adapter._client = mock_client
    await adapter.close()
    assert adapter._client is None
