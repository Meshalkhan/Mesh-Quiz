from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import create_api_router
from app.core.config import get_settings
from app.core.cors import add_cors_middleware
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger = get_logger(__name__)
    settings = get_settings()
    paths = sorted(
        {
            getattr(route, "path", "")
            for route in app.routes
            if getattr(route, "path", None)
        }
    )
    logger.info(
        "startup service=%s version=%s env=%s routes=%s",
        settings.app_name,
        settings.app_version,
        settings.app_env,
        paths,
    )
    yield
    logger.info("shutdown service=%s", settings.app_name)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )
    add_cors_middleware(app, settings)
    register_exception_handlers(app)
    app.include_router(create_api_router(settings))
    return app


app = create_app()
