"""Modelos de processamento e relação com contas YouTube."""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


job_accounts = Table(
    "job_accounts",
    Base.metadata,
    Column(
        "job_id",
        Integer,
        ForeignKey("processing_jobs.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "account_id",
        Integer,
        ForeignKey("youtube_accounts.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class ProcessingJob(Base):
    """Processamento completo de um vídeo."""

    __tablename__ = "processing_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'error', 'cancelled')",
            name="ck_processing_jobs_status",
        ),
        CheckConstraint(
            "progress >= 0 AND progress <= 100",
            name="ck_processing_jobs_progress",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    current_step: Mapped[str | None] = mapped_column(String(100))
    progress: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    config: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    output_video: Mapped[str | None] = mapped_column(String(2048))
    youtube_urls: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    accounts: Mapped[list["YouTubeAccount"]] = relationship(
        secondary=job_accounts,
        back_populates="jobs",
        lazy="selectin",
    )
    steps: Mapped[list["JobStep"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
