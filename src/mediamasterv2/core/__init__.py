"""Core module — BasePlatform interface, Factory, Config."""

from mediamasterv2.core.base import BasePlatform, PlatformCapability, PostResult, ScheduleResult
from mediamasterv2.core.factory import PlatformFactory
from mediamasterv2.core.config import PlatformConfig, load_config

__all__ = [
    "BasePlatform",
    "PlatformCapability",
    "PostResult",
    "ScheduleResult",
    "PlatformFactory",
    "PlatformConfig",
    "load_config",
]
