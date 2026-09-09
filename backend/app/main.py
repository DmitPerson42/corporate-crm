"""Точка входа FastAPI: сборка приложения, CORS, обработка ошибок, проверка доступности БД."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app import __version__
from app.config import settings
from app.db import dispose_engine, engine
from app.routers import auth, clients

logger = logging.getLogger("crm")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Заполняется при проверке доступности PostgreSQL на старте.
db_ready: dict[str, str | bool] = {"ok": False, "error": ""}


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.jwt_secret == "change-me-to-a-long-random-string" or len(settings.jwt_secret) < 32:
        logger.warning(
            "JWT_SECRET задан значением по умолчанию или короче 32 символов: "
            "подпись токенов ненадёжна. Замените секрет в файле .env."
        )
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ready.update(ok=True, error="")
        logger.info("PostgreSQL доступен: %s", engine.url.render_as_string(hide_password=True))
    except Exception as exc:  # причину пишем в /api/health, ронять приложение не будем
        db_ready.update(ok=False, error=str(exc))
        logger.error("PostgreSQL недоступен (%s). Проверьте службу и DATABASE_URL в .env", exc)
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    app = FastAPI(
        title="КИС «Учёт клиентов»",
        version=__version__,
        description=(
            "Корпоративная информационно-аналитическая система: менеджер заводит карточки "
            "клиентов, редактирует их и дополняет комментариями. Хранилище — PostgreSQL."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(clients.router)

    @app.get("/api/health", tags=["Сервис"], summary="Проверка живости API и подключения к БД")
    async def health() -> dict:
        return {
            "status": "ok" if db_ready["ok"] else "degraded",
            "database": "up" if db_ready["ok"] else f"down: {db_ready['error']}",
            "version": __version__,
        }

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
        logger.warning("Нарушение целостности данных: %s", exc.orig)
        return JSONResponse(
            status_code=409,
            content={"detail": "Такая запись уже существует или на неё есть ссылки"},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Необработанная ошибка при обработке %s", request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Внутренняя ошибка сервера"})

    return app


app = create_app()


def run() -> None:  # pragma: no cover - удобная точка входа для `python -m app.main`
    """Старт сервера с хостом/портом из .env. Флаг --no-reload отключает автоперезагрузку."""
    import sys

    import uvicorn

    reload = '--no-reload' not in sys.argv
    uvicorn.run('app.main:app', host=settings.host, port=settings.port, reload=reload)


if __name__ == '__main__':
    run()
