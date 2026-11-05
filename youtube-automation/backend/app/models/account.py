"""Modelo de contas conectadas do YouTube."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class YouTubeAccount(Base):
    """Conta YouTube autorizada para uploads."""

    __tablename__ = "youtube_accounts"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    channel_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    email: Mapped[str | None] = mapped_column(String(320))
    avatar_url: Mapped[str | None] = mapped_column(String(2048))
    credentials: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    jobs: Mapped[list["ProcessingJob"]] = relationship(
        secondary="job_accounts",
        back_populates="accounts",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """Retorna uma representação sem expor credenciais."""
        return (
            f"YouTubeAccount(id={self.id!r}, name={self.name!r}, "
            f"channel_id={self.channel_id!r}, is_active={self.is_active!r})"
        )
