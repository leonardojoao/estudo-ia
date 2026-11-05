"""Cria o schema inicial da aplicação."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Cria tabelas e configurações padrão."""
    op.create_table(
        "youtube_accounts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("channel_id", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("avatar_url", sa.String(length=2048), nullable=True),
        sa.Column("credentials", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("channel_id"),
    )
    op.create_index(
        "ix_youtube_accounts_channel_id",
        "youtube_accounts",
        ["channel_id"],
        unique=True,
    )

    op.create_table(
        "processing_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("current_step", sa.String(length=100), nullable=True),
        sa.Column("progress", sa.Integer(), server_default="0", nullable=False),
        sa.Column("config", sa.Text(), nullable=False),
        sa.Column("output_video", sa.String(length=2048), nullable=True),
        sa.Column("youtube_urls", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'error', 'cancelled')",
            name="ck_processing_jobs_status",
        ),
        sa.CheckConstraint(
            "progress >= 0 AND progress <= 100",
            name="ck_processing_jobs_progress",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("key"),
    )

    op.create_table(
        "job_accounts",
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["youtube_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["processing_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("job_id", "account_id"),
    )

    op.create_table(
        "job_steps",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("step_name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("input", sa.Text(), nullable=True),
        sa.Column("output", sa.Text(), nullable=True),
        sa.Column("log", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["processing_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_steps_job_id", "job_steps", ["job_id"], unique=False)

    op.bulk_insert(
        sa.table(
            "system_settings",
            sa.column("key", sa.String()),
            sa.column("value", sa.String()),
        ),
        [
            {"key": "ollama_url", "value": "http://localhost:11434"},
            {"key": "ollama_model", "value": "llama3"},
            {"key": "videos_folder", "value": ""},
            {"key": "tts_voice", "value": "en-US-JennyNeural"},
            {"key": "default_dimension", "value": "16:9"},
            {"key": "clip_min_duration", "value": "3"},
            {"key": "clip_max_duration", "value": "6"},
        ],
    )


def downgrade() -> None:
    """Remove o schema inicial na ordem exigida pelas chaves estrangeiras."""
    op.drop_index("ix_job_steps_job_id", table_name="job_steps")
    op.drop_table("job_steps")
    op.drop_table("job_accounts")
    op.drop_table("system_settings")
    op.drop_table("processing_jobs")
    op.drop_index("ix_youtube_accounts_channel_id", table_name="youtube_accounts")
    op.drop_table("youtube_accounts")
