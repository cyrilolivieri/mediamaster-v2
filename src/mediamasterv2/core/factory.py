"""Factory pattern for instantiating platform connectors."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mediamasterv2.core.config import PlatformConfig

if TYPE_CHECKING:
    from mediamasterv2.core.base import BasePlatform


class PlatformFactory:
    """
    Factory for creating platform connector instances.

    Usage:
        factory = PlatformFactory(config)
        linkedin = factory.create("linkedin")
        youtube = factory.create("youtube")
    """

    _registry: dict[str, type["BasePlatform"]] = {}

    @classmethod
    def register(cls, name: str, cls_: type["BasePlatform"]) -> None:
        """Register a platform connector class."""
        cls._registry[name.lower()] = cls_

    @classmethod
    def create(cls, name: str, config: PlatformConfig) -> "BasePlatform":
        """Instantiate a platform connector by name."""
        name_lower = name.lower()

        if name_lower not in cls._registry:
            available = ", ".join(sorted(cls._registry.keys())) or "none"
            raise ValueError(
                f"Unknown platform '{name}'. Available: {available}"
            )

        platform_cls = cls._registry[name_lower]

        # Map platform name to config section
        config_map = {
            "linkedin": config.linkedin,
            "twitter": config.twitter,
            "x": config.twitter,
            "instagram": config.instagram,
            "youtube": config.youtube,
            "tiktok": config.tiktok,
            "discord": config.discord,
            "telegram": config.telegram,
            "pinterest": config.pinterest,
            "twitch": config.twitch,
        }

        cfg = config_map.get(name_lower)
        if cfg is None:
            raise ValueError(f"No config section for platform '{name}'")

        return platform_cls(cfg.model_dump())

    @classmethod
    def available_platforms(cls) -> list[str]:
        """List all registered platform names."""
        return sorted(cls._registry.keys())

    @classmethod
    def create_all(cls, config: PlatformConfig) -> dict[str, "BasePlatform"]:
        """Instantiate all registered platform connectors."""
        return {name: cls.create(name, config) for name in cls._registry}
