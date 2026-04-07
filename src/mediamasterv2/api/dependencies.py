"""Dependency injection helpers for API routes."""

from mediamasterv2.core.config import PlatformConfig
from mediamasterv2.core.factory import PlatformFactory
from mediamasterv2.api.lifespan import get_factory, get_config

__all__ = ["get_factory", "get_config"]
