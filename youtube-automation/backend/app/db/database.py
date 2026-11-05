"""Configuração do banco SQLite e sessões SQLAlchemy."""

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Classe base dos modelos SQLAlchemy."""


settings = get_settings()
database_url = (
    settings.database_path
    if settings.database_path.startswith("sqlite:")
    else f"sqlite:///{settings.database_path}"
)

if not settings.database_path.startswith(":memory:"):
    database_path = Path(settings.database_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    database_url,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    class_=Session,
)


def create_tables() -> None:
    """Habilita o modo WAL e cria as tabelas registradas nos modelos."""
    import app.models  # noqa: F401

    with engine.connect() as connection:
        if not settings.database_path.startswith(":memory:"):
            connection.execute(text("PRAGMA journal_mode=WAL"))
        connection.commit()
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Fornece uma sessão por requisição e garante seu fechamento."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
