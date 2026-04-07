"""Tests for YouTube connector."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from mediamasterv2.platforms.youtube_connector import YouTubeConnector
from mediamasterv2.core.base import PostResult, ScheduleResult


@pytest.fixture
def yt_connector():
    config = {
        "client_secrets_path": "/tmp/fake_secrets.json",
        "credentials_path": "/tmp/fake_creds.json",
        "channel_id": "UC123456",
    }
    return YouTubeConnector(config)


def test_youtube_connector_initialization(yt_connector):
    assert yt_connector.name == "youtube"
    assert yt_connector.channel_id == "UC123456"


def test_youtube_has_video_capability(yt_connector):
    from mediamasterv2.core.base import PlatformCapability
    assert yt_connector.has_capability(PlatformCapability.POST_VIDEO)


def test_youtube_no_text_capability(yt_connector):
    from mediamasterv2.core.base import PlatformCapability
    assert not yt_connector.has_capability(PlatformCapability.POST_TEXT)


@pytest.mark.asyncio
async def test_post_video_file_not_found(yt_connector):
    result = await yt_connector.post(
        "/nonexistent/video.mp4",
        title="Test",
    )
    assert result.success is False
    assert "not found" in result.error.lower() or "no such file" in result.error.lower()


@pytest.mark.asyncio
async def test_schedule_without_video(yt_connector):
    future = datetime(2025, 12, 31)
    result = await yt_connector.schedule(
        "/nonexistent/video.mp4",
        scheduled_at=future,
    )
    assert result.success is False


@pytest.mark.asyncio
async def test_close(yt_connector):
    mock_service = MagicMock()
    mock_service.close = MagicMock()
    yt_connector._service = mock_service
    await yt_connector.close()
    assert yt_connector._service is None
    mock_service.close.assert_called_once()
