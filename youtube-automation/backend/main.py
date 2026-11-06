"""Ponto de entrada da API FastAPI."""

from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text, update

from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.scheduler import shutdown_scheduler, start_scheduler
from app.db.database import SessionLocal, engine
from app.api.routes.settings import router as settings_router
from app.api.routes.ollama import router as ollama_router
from app.api.routes.accounts import router as accounts_router
from app.models.job import ProcessingJob

_migrations_applied = False


def run_migrations() -> None:
    """Aplica migrations pendentes antes de iniciar a API."""
    global _migrations_applied
    if not _migrations_applied:
        config = Config("alembic.ini")
        inspector = inspect(engine)
        has_legacy_schema = inspector.has_table("youtube_accounts")
        has_version = False
        if inspector.has_table("alembic_version"):
            with engine.connect() as connection:
                has_version = (
                    connection.execute(
                        text("SELECT 1 FROM alembic_version LIMIT 1")
                    ).first()
                    is not None
                )
        if has_legacy_schema and not has_version:
            command.stamp(config, "head")
        else:
            command.upgrade(config, "head")
        _migrations_applied = True


def recover_zombie_jobs() -> None:
    """Marca jobs interrompidos por restart como erro."""
    with SessionLocal.begin() as db:
        db.execute(
            update(ProcessingJob)
            .where(ProcessingJob.status == "running")
            .values(
                status="error",
                error_message="Processamento interrompido durante a inicialização",
            )
        )


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Inicializa a persistência antes de atender requisições."""
    run_migrations()
    recover_zombie_jobs()
    start_scheduler(settings)
    try:
        yield
    finally:
        shutdown_scheduler()


settings = get_settings()
app = FastAPI(
    title="YouTube Automation API",
    version="1.0.0",
    lifespan=lifespan,
)
app.state.environment = settings.environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_exception_handlers(app)
app.include_router(settings_router, prefix="/api")
app.include_router(ollama_router, prefix="/api")
app.include_router(accounts_router, prefix="/api")


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Retorna o estado básico da API."""
    return {"status": "ok"}
