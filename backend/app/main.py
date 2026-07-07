from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.routes import edit, export, health, map as map_routes, poi, trip
from backend.app.errors import http_exception_handler, unhandled_exception_handler, validation_exception_handler

ROOT_DIR = Path(__file__).resolve().parents[2]
APP_DIR = ROOT_DIR / "app"


def create_app() -> FastAPI:
    app = FastAPI(
        title="旅游规划 Agent API",
        description="FastAPI + 多 Agent 旅游规划后端，提供行程生成、POI搜索、路线摘要与静态前端页面。",
        version="0.4.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    app.include_router(health.router, prefix="/api")
    app.include_router(trip.router, prefix="/api")
    app.include_router(poi.router, prefix="/api")
    app.include_router(map_routes.router, prefix="/api")
    app.include_router(edit.router, prefix="/api")
    app.include_router(export.router, prefix="/api")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(APP_DIR / "index.html")

    app.mount("/app", StaticFiles(directory=APP_DIR), name="app")
    return app


app = create_app()

