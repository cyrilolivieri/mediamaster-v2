"""MediaMaster v2 — FastAPI Application Entry Point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.models.schemas import ErrorResponse
from api.routes import analytics, health, platforms, post, schedule
from mediamasterv2.core.config import PlatformConfig
from mediamasterv2.core.factory import PlatformFactory
from mediamasterv2.platforms.discord_bot import DiscordBot
from mediamasterv2.platforms.pinterest_connector import PinterestConnector
from mediamasterv2.platforms.postiz_adapter import PostizAdapter
from mediamasterv2.platforms.telegram_bot import TelegramBot
from mediamasterv2.platforms.tiktok_connector import TikTokConnector
from mediamasterv2.platforms.twitch_connector import TwitchConnector
from mediamasterv2.platforms.youtube_connector import YouTubeConnector

# ─── Logging Configuration ────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("mediamasterv2.api")


# ─── Lifespan ────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    On startup: register all platform connectors with the factory.
    On shutdown: close all connector resources.
    """
    # Register platforms
    PlatformFactory.register("linkedin", PostizAdapter)
    PlatformFactory.register("twitter", PostizAdapter)
    PlatformFactory.register("instagram", PostizAdapter)
    PlatformFactory.register("youtube", YouTubeConnector)
    PlatformFactory.register("discord", DiscordBot)
    PlatformFactory.register("telegram", TelegramBot)
    PlatformFactory.register("pinterest", PinterestConnector)
    PlatformFactory.register("twitch", TwitchConnector)
    PlatformFactory.register("tiktok", TikTokConnector)

    logger.info("Platforms registered: %s", PlatformFactory.available_platforms())

    yield  # ─── shutdown ─────────────────────────────────────────────────────

    config = PlatformConfig.load()
    for name in PlatformFactory.available_platforms():
        try:
            connector = PlatformFactory.create(name, config)
            await connector.close()
        except Exception:  # noqa: BLE-001
            pass

    logger.info("All connectors closed.")


# ─── App Factory ──────────────────────────────────────────────────────────────


def create_app() -> FastAPI:
    app = FastAPI(
        title="MediaMaster v2 API",
        description=(
            "Multi-platform social media publishing agent. "
            "Post, schedule, and analyze content across LinkedIn, "
            "Twitter, Instagram, YouTube, Discord, Telegram, and more."
        ),
        version="0.2.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS ─────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routes ────────────────────────────────────────────────────────────────
    app.include_router(health.router)
    app.include_router(platforms.router)
    app.include_router(post.router)
    app.include_router(schedule.router)
    app.include_router(analytics.router)

    # ── Global Exception Handler ──────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("Unhandled exception")
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                detail="Internal server error",
                error_code="INTERNAL_ERROR",
            ).model_dump(),
        )

    return app


# ─── App Instance ─────────────────────────────────────────────────────────────

app = create_app()


# ─── CLI Entrypoint (uvicorn) ─────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
