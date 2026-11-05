"""Ponto de entrada da API FastAPI."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.db.database import create_tables


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Inicializa a persistência antes de atender requisições."""
    create_tables()
    yield


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


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Retorna o estado básico da API."""
    return {"status": "ok"}
