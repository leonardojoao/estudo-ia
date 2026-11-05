"""Modelo de configurações persistidas da aplicação."""

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.db.database import Base


class SystemSetting(Base):
    """Configuração armazenada como chave e valor textual."""

    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    @classmethod
    def get(
        cls,
        db: Session,
        key: str,
        default: str | None = None,
    ) -> str | None:
        """Retorna o valor de uma configuração ou o default informado."""
        setting = db.get(cls, key)
        return setting.value if setting is not None else default

    @classmethod
    def set(cls, db: Session, key: str, value: str) -> "SystemSetting":
        """Cria ou atualiza uma configuração e confirma a transação."""
        setting = db.get(cls, key)
        if setting is None:
            setting = cls(key=key, value=value)
            db.add(setting)
        else:
            setting.value = value
        db.commit()
        db.refresh(setting)
        return setting
