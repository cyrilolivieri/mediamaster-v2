"""Postiz adapter — wraps Postiz API for LinkedIn, Twitter/X, Instagram."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import httpx

from mediamasterv2.core.base import (
    BasePlatform,
    EngagementResult,
    PlatformCapability,
    PostResult,
    ScheduleResult,
)
from mediamasterv2.core.factory import PlatformFactory


class PostizAdapter(BasePlatform):
    """
    Adapter for Postiz API (https://github.com/gitroomhq/postiz-app).

    Postiz is an open-source social media scheduling tool that supports
    LinkedIn, Twitter/X, Instagram, and YouTube via a unified API.
    """

    name = "postiz"
    capabilities: set[PlatformCapability] = {
        PlatformCapability.POST_TEXT,
        PlatformCapability.POST_IMAGE,
        PlatformCapability.POST_LINK,
        PlatformCapability.SCHEDULE,
        PlatformCapability.ANALYTICS,
        PlatformCapability.ENGAGE,
        PlatformCapability.REELS,
    }

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.base_url = config.get("postiz_url", "http://localhost:4000")
        self.api_key = config.get("api_key", "")
        self.workspace_id = config.get("workspace_id", "")
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def _health_check_impl(self) -> bool:
        try:
            client = self._get_client()
            resp = await client.get("/api/health")
            return resp.status_code == 200
        except Exception:
            return False

    async def post(self, content: str, **kwargs: Any) -> PostResult:
        """
        Post content to the configured social networks via Postiz.

        Args:
            content: The post text/content
            networks: List of networks to post to (e.g. ["linkedin", "twitter"])
            media_urls: Optional list of media URLs to attach
            scheduled_at: If provided, schedules instead of posting immediately
        """
        networks = kwargs.get("networks", self._infer_networks())
        media_urls = kwargs.get("media_urls", [])
        scheduled_at = kwargs.get("scheduled_at")

        try:
            client = self._get_client()

            payload: dict[str, Any] = {
                "content": content,
                "networks": networks,
                "workspaceId": self.workspace_id,
            }

            if media_urls:
                payload["media"] = [{"url": url} for url in media_urls]

            if scheduled_at:
                payload["scheduledAt"] = scheduled_at.isoformat()

            endpoint = "/api/v1/posts/schedule" if scheduled_at else "/api/v1/posts"
            resp = await client.post(endpoint, json=payload)
            resp.raise_for_status()

            data = resp.json()

            return PostResult(
                platform=self.name,
                post_id=data.get("id"),
                url=data.get("url"),
                success=True,
                posted_at=datetime.now(tz=datetime.now().astimezone().tzinfo),
                metadata={"networks": networks, "response": data},
            )

        except httpx.HTTPStatusError as e:
            return PostResult(
                platform=self.name,
                post_id=None,
                url=None,
                success=False,
                error=f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            )
        except Exception as e:
            return PostResult(
                platform=self.name,
                post_id=None,
                url=None,
                success=False,
                error=str(e),
            )

    async def schedule(
        self, content: str, scheduled_at: datetime, **kwargs: Any
    ) -> ScheduleResult:
        """Schedule content for later posting."""
        networks = kwargs.get("networks", self._infer_networks())
        media_urls = kwargs.get("media_urls", [])

        try:
            client = self._get_client()

            payload: dict[str, Any] = {
                "content": content,
                "networks": networks,
                "scheduledAt": scheduled_at.isoformat(),
                "workspaceId": self.workspace_id,
            }

            if media_urls:
                payload["media"] = [{"url": url} for url in media_urls]

            resp = await client.post("/api/v1/posts/schedule", json=payload)
            resp.raise_for_status()
            data = resp.json()

            return ScheduleResult(
                platform=self.name,
                schedule_id=data.get("id"),
                scheduled_at=scheduled_at,
                success=True,
                metadata={"networks": networks},
            )

        except Exception as e:
            return ScheduleResult(
                platform=self.name,
                schedule_id=None,
                scheduled_at=scheduled_at,
                success=False,
                error=str(e),
            )

    async def analytics(self, **kwargs: Any) -> Any:
        """Fetch analytics from Postiz for posted content."""
        try:
            client = self._get_client()
            post_id = kwargs.get("post_id")
            endpoint = (
                f"/api/v1/analytics/posts/{post_id}"
                if post_id
                else "/api/v1/analytics/overview"
            )
            resp = await client.get(endpoint, params={"workspaceId": self.workspace_id})
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    async def engage(
        self, action: str, target_id: str, **kwargs: Any
    ) -> EngagementResult:
        """Perform engagement actions via Postiz."""
        try:
            client = self._get_client()
            payload = {
                "action": action,
                "targetId": target_id,
                "workspaceId": self.workspace_id,
            }
            resp = await client.post("/api/v1/engagement", json=payload)
            resp.raise_for_status()
            return EngagementResult(
                platform=self.name,
                action=action,
                target_id=target_id,
                success=True,
                metadata=resp.json(),
            )
        except Exception as e:
            return EngagementResult(
                platform=self.name,
                action=action,
                target_id=target_id,
                success=False,
                error=str(e),
            )

    def _infer_networks(self) -> list[str]:
        """Infer which networks to post to based on populated config fields."""
        # This is a heuristic — callers should explicitly pass networks
        return ["linkedin", "twitter"]

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


# Register with factory
PlatformFactory.register("linkedin", PostizAdapter)
PlatformFactory.register("twitter", PostizAdapter)
PlatformFactory.register("x", PostizAdapter)
PlatformFactory.register("instagram", PostizAdapter)
PlatformFactory.register("postiz", PostizAdapter)
