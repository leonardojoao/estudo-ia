"""Dependências reutilizáveis das rotas FastAPI."""

from collections.abc import Generator

from app.core.config import Settings, get_settings as load_settings
from app.db.database import get_db as open_db
from sqlalchemy.orm import Session


def get_db() -> Generator[Session, None, None]:
    """Fornece uma sessão SQLAlchemy por requisição."""
    yield from open_db()


def get_settings() -> Settings:
    """Fornece a configuração singleton da aplicação."""
    return load_settings()
