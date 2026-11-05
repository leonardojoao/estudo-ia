"""Configuração do Alembic para o banco SQLite da aplicação."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.db.database import Base
from app.models.account import YouTubeAccount  # noqa: F401
from app.models.job import ProcessingJob  # noqa: F401
from app.models.job_step import JobStep  # noqa: F401
from app.models.settings import SystemSetting  # noqa: F401

config = context.config
settings = get_settings()
database_url = (
    settings.database_path
    if settings.database_path.startswith("sqlite:")
    else f"sqlite:///{settings.database_path}"
)
config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Executa migrations sem abrir uma conexão."""
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Executa migrations usando uma conexão ativa."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
