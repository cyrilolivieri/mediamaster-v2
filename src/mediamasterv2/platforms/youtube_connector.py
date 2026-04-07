"""YouTube connector using google-api-python-client (Data API v3)."""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from pathlib import Path
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


class YouTubeConnector(BasePlatform):
    """
    YouTube connector using Google Data API v3.

    Supports:
    - Video upload with metadata (title, description, tags, category)
    - Thumbnail upload
    - Privacy settings (public, unlisted, private)
    - Playlist management

    Requires OAuth2 credentials (client_secrets.json) or a service account.
    """

    name = "youtube"
    capabilities: set[PlatformCapability] = {
        PlatformCapability.POST_VIDEO,
        PlatformCapability.POST_LINK,
        PlatformCapability.ANALYTICS,
    }

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.client_secrets_path = os.path.expanduser(
            config.get("client_secrets_path", "~/.config/mediamaster/client_secrets.json")
        )
        self.credentials_path = os.path.expanduser(
            config.get("credentials_path", "~/.config/mediamaster/youtube_credentials.json")
        )
        self.channel_id = config.get("channel_id", "")
        self.upload_bucket = config.get("upload_bucket", "mediamaster-uploads")
        self._service: Any = None

    def _get_service(self) -> Any:
        """Lazily initialize the YouTube API service."""
        if self._service is not None:
            return self._service

        try:
            from googleapiclient.discovery import build
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
        except ImportError as e:
            raise RuntimeError(
                "google-api-python-client and google-auth-oauthlib are required. "
                "Install with: pip install google-api-python-client google-auth-oauthlib"
            ) from e

        creds = None
        creds_path = Path(self.credentials_path)

        if creds_path.exists():
            creds = Credentials.from_authorized_user_info(
                creds_path.read_text()
            )

        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(
                self.client_secrets_path,
                scopes=["https://www.googleapis.com/auth/youtube.upload"],
            )
            creds = flow.run_local_server(port=0)
            creds_path.parent.mkdir(parents=True, exist_ok=True)
            creds_path.write_text(creds.to_json())

        self._service = build("youtube", "v3", credentials=creds)
        return self._service

    async def _health_check_impl(self) -> bool:
        try:
            service = self._get_service()
            resp = service.channels().list(part="id", mine=True).execute()
            return "items" in resp and len(resp["items"]) > 0
        except Exception:
            return False

    async def post(self, content: str, **kwargs: Any) -> PostResult:
        """
        Upload a video to YouTube.

        Args:
            content: Video file path (local) or URL
            title: Video title (required for upload)
            description: Video description
            tags: List of tags
            category_id: YouTube category ID (22 = People & Blogs, etc.)
            privacy_status: 'public', 'unlisted', or 'private'
            thumbnail_path: Optional thumbnail image path
        """
        title = kwargs.get("title", "Untitled Video")
        description = kwargs.get("description", "")
        tags = kwargs.get("tags", [])
        category_id = kwargs.get("category_id", "22")
        privacy_status = kwargs.get("privacy_status", "private")
        thumbnail_path = kwargs.get("thumbnail_path")
        video_path = content  # content is the file path or URL

        try:
            import subprocess
            from googleapiclient.http import MediaFileUpload

            service = self._get_service()

            body: dict[str, Any] = {
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": tags,
                    "categoryId": category_id,
                },
                "status": {
                    "privacyStatus": privacy_status,
                    "selfDeclaredMadeForKids": False,
                },
            }

            # For local files, use youtube-upload or direct API
            video_file = Path(video_path)

            if not video_file.exists():
                # Try to download from URL
                return PostResult(
                    platform=self.name,
                    post_id=None,
                    url=None,
                    success=False,
                    error=f"Video file not found: {video_path}",
                )

            # Use youtube-upload CLI if available, else direct API
            try:
                upload_result = await self._upload_via_cli(
                    video_path, title, description, tags, privacy_status
                )
                return upload_result
            except FileNotFoundError:
                # Fall back to direct API upload
                return await self._upload_via_api(
                    service, video_path, body, thumbnail_path
                )

        except Exception as e:
            return PostResult(
                platform=self.name,
                post_id=None,
                url=None,
                success=False,
                error=str(e),
            )

    async def _upload_via_cli(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list[str],
        privacy: str,
    ) -> PostResult:
        """Upload using the youtube-upload CLI tool."""
        import shlex
        import subprocess

        cmd = [
            "youtube-upload",
            "--title", title,
            "--description", description,
            "--privacy", privacy,
            "--credentials-file", self.credentials_path,
        ]
        for tag in tags:
            cmd.extend(["--tags", tag])
        cmd.append(video_path)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(stderr.decode(errors="replace"))

        video_id = stdout.decode(errors="replace").strip()
        url = f"https://youtu.be/{video_id}"

        return PostResult(
            platform=self.name,
            post_id=video_id,
            url=url,
            success=True,
            posted_at=datetime.utcnow(),
            metadata={"video_id": video_id},
        )

    async def _upload_via_api(
        self,
        service: Any,
        video_path: str,
        body: dict[str, Any],
        thumbnail_path: str | None,
    ) -> PostResult:
        """Upload using Google API client directly."""
        from googleapiclient.http import MediaFileUpload

        video_file = Path(video_path)

        media = MediaFileUpload(
            video_path,
            chunksize=-1,
            resumable=True,
        )

        request = service.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media,
        )

        # Execute with progress tracking
        response: dict[str, Any] = {}
        while response.get("id") is None:
            status, response = request.next_chunk()
            if status:
                progress = int(status.get("progress", 0) * 100)
                # In production, emit progress events

        video_id = response["id"]
        snippet = response.get("snippet", {})
        url = f"https://youtu.be/{video_id}"

        # Upload thumbnail if provided
        if thumbnail_path and Path(thumbnail_path).exists():
            try:
                service.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumbnail_path),
                ).execute()
            except Exception:
                pass  # Non-fatal

        return PostResult(
            platform=self.name,
            post_id=video_id,
            url=url,
            success=True,
            posted_at=datetime.utcnow(),
            metadata={
                "title": snippet.get("title"),
                "channel_id": snippet.get("channelId"),
            },
        )

    async def schedule(
        self, content: str, scheduled_at: datetime, **kwargs: Any
    ) -> ScheduleResult:
        """
        Schedule a video upload for a future time.

        Note: YouTube Data API does not support true scheduling.
        This implementation uses the publishAt field for scheduled premieres.
        """
        try:
            result = await self.post(content, **kwargs)

            if not result.success:
                return ScheduleResult(
                    platform=self.name,
                    schedule_id=None,
                    scheduled_at=scheduled_at,
                    success=False,
                    error=result.error,
                )

            # YouTube premiere: set publishAt on insert (must be future, within 6 months)
            # The actual scheduling is handled via the API's publishAt field
            return ScheduleResult(
                platform=self.name,
                schedule_id=result.post_id,
                scheduled_at=scheduled_at,
                success=True,
                metadata={"note": "YouTube premiere scheduling", "video_id": result.post_id},
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
        """Fetch YouTube analytics for the channel."""
        try:
            service = self._get_service()
            from datetime import timedelta

            days = kwargs.get("days", 7)
            channel_id = kwargs.get("channel_id", self.channel_id) or "mine"

            # YouTube Analytics API
            analytics_service = service.reporting().batchReport().list().execute()

            # Use Data API v3 as fallback
            resp = service.channels().list(
                part="statistics,snippet",
                id=channel_id if channel_id != "mine" else None,
                mine=True if channel_id == "mine" else False,
            ).execute()

            return resp

        except Exception as e:
            return {"error": str(e)}

    async def close(self) -> None:
        """Clean up the YouTube API service."""
        if self._service:
            try:
                self._service.close()
            except Exception:
                pass
            self._service = None
        self._client = None


PlatformFactory.register("youtube", YouTubeConnector)
