"""FastAPI application entry point."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from mediamasterv2.api import routes, lifespan


app = FastAPI(
    title="MediaMaster v2 API",
    description="Multi-platform social media agent — FastAPI layer",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("mediamasterv2.api.main:app", host="0.0.0.0", port=8000, reload=True)
