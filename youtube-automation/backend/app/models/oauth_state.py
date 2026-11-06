"""Modelos para states temporários do fluxo OAuth."""

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class OAuthState(Base):
    """State CSRF de uso único para callbacks OAuth."""

    __tablename__ = "oauth_states"

    state_token: Mapped[str] = mapped_column(String(255), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
