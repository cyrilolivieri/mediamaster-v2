"""Tests for core module: base, config, factory."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from mediamasterv2.core.base import (
    BasePlatform,
    PlatformCapability,
    PostResult,
    ScheduleResult,
    AnalyticsResult,
    EngagementResult,
)
from mediamasterv2.core.config import (
    PlatformConfig,
    LinkedInConfig,
    YouTubeConfig,
    load_config,
)
from mediamasterv2.core.factory import PlatformFactory


# --- Test BasePlatform abstract behavior ---

class DummyPlatform(BasePlatform):
    """Concrete implementation of BasePlatform for testing."""

    name = "dummy"
    capabilities = {PlatformCapability.POST_TEXT, PlatformCapability.SCHEDULE}

    async def post(self, content: str, **kwargs):
        return PostResult(
            platform=self.name,
            post_id="123",
            url="https://example.com/123",
            success=True,
        )

    async def schedule(self, content: str, scheduled_at: datetime, **kwargs):
        return ScheduleResult(
            platform=self.name,
            schedule_id="456",
            scheduled_at=scheduled_at,
            success=True,
        )

    async def _health_check_impl(self) -> bool:
        return True


class FailingPlatform(BasePlatform):
    """Platform that always fails health check."""

    name = "failing"
    capabilities = set()

    async def post(self, content: str, **kwargs):
        return PostResult(platform=self.name, post_id=None, url=None, success=False, error="failed")

    async def schedule(self, content: str, scheduled_at: datetime, **kwargs):
        return ScheduleResult(platform=self.name, schedule_id=None, scheduled_at=scheduled_at, success=False)

    async def _health_check_impl(self) -> bool:
        return False


def test_base_platform_capabilities():
    p = DummyPlatform({})
    assert p.has_capability(PlatformCapability.POST_TEXT)
    assert p.has_capability(PlatformCapability.SCHEDULE)
    assert not p.has_capability(PlatformCapability.POST_VIDEO)


@pytest.mark.asyncio
async def test_post_result_success():
    p = DummyPlatform({})
    result = await p.post("Hello world")
    assert result.success is True
    assert result.post_id == "123"
    assert result.platform == "dummy"


@pytest.mark.asyncio
async def test_schedule_result():
    p = DummyPlatform({})
    future = datetime(2025, 12, 31, 12, 0)
    result = await p.schedule("Hello", future)
    assert result.success is True
    assert result.schedule_id == "456"
    assert result.scheduled_at == future


@pytest.mark.asyncio
async def test_health_check_success():
    p = DummyPlatform({})
    assert await p.health_check() is True


@pytest.mark.asyncio
async def test_health_check_failure():
    p = FailingPlatform({})
    assert await p.health_check() is False


@pytest.mark.asyncio
async def test_analytics_not_implemented():
    p = DummyPlatform({})
    result = await p.analytics()
    assert result.error == "Not implemented"


@pytest.mark.asyncio
async def test_engage_not_implemented():
    p = DummyPlatform({})
    result = await p.engage("like", "post123")
    assert result.success is False
    assert result.error == "Not implemented"


# --- Test Config ---

def test_linkedin_config_defaults():
    cfg = LinkedInConfig()
    assert cfg.api_key == ""
    assert cfg.postiz_url == "http://localhost:4000"


def test_youtube_config_defaults():
    cfg = YouTubeConfig()
    assert cfg.channel_id == ""
    assert "~" in cfg.client_secrets_path


def test_platform_config_from_dict():
    data = {
        "linkedin": {"api_key": "test_key", "workspace_id": "ws1"},
        "youtube": {"channel_id": "UC123"},
        "global": {"max_retries": 5},
    }
    cfg = PlatformConfig.from_dict(data)
    assert cfg.linkedin.api_key == "test_key"
    assert cfg.linkedin.workspace_id == "ws1"
    assert cfg.youtube.channel_id == "UC123"
    assert cfg.global_settings.max_retries == 5


def test_load_config_nonexistent():
    import os
    os.environ.pop("MEDIAMASTER_CONFIG", None)
    cfg = load_config("/nonexistent/path/config.yaml")
    assert isinstance(cfg, PlatformConfig)


# --- Test Factory ---

def test_factory_register_and_create():
    PlatformFactory._registry.clear()
    PlatformFactory.register("test", DummyPlatform)
    assert "test" in PlatformFactory.available_platforms()


def test_factory_create_unknown():
    PlatformFactory._registry.clear()
    with pytest.raises(ValueError, match="Unknown platform"):
        PlatformFactory.create("unknown", PlatformConfig())


def test_factory_available_platforms():
    platforms = PlatformFactory.available_platforms()
    assert isinstance(platforms, list)
