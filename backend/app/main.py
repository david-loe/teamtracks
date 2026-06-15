from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.conversion_jobs import router as conversion_jobs_router
from app.api.health import router as health_router
from app.api.manifest import router as manifest_router
from app.api.media import router as media_router
from app.api.songs import router as songs_router
from app.api.stems import router as stems_router
from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(songs_router)
    app.include_router(stems_router)
    app.include_router(conversion_jobs_router)
    app.include_router(manifest_router)
    app.include_router(media_router)
    return app


app = create_app()
