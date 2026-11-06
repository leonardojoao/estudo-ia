"""Schemas de contas YouTube."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl


class AccountCreate(BaseModel):
    """Dados públicos necessários para cadastrar uma conta."""

    name: str = Field(min_length=1, max_length=255)
    channel_id: str = Field(min_length=1, max_length=255)
    email: EmailStr | None = None
    avatar_url: HttpUrl | None = None
    credentials: str = Field(min_length=1)


class AccountResponse(BaseModel):
    """Representação segura de uma conta, sem credenciais."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    channel_id: str
    email: str | None
    avatar_url: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AccountStatus(BaseModel):
    """Estado resumido de uma conta conectada."""

    account_id: int
    status: str
    message: str | None = None
