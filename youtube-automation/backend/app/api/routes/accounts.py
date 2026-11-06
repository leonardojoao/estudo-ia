"""Endpoints para contas conectadas do YouTube."""

import json
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import Settings, get_settings
from app.core.crypto import encrypt
from app.core.exceptions import NotFoundError, OAuthError, TokenDecryptionError
from app.api.routes.settings import require_admin_key
from app.models.account import YouTubeAccount
from app.schemas.account import AccountResponse
from app.services.youtube.auth import (
    create_oauth_state,
    exchange_code_for_tokens,
    get_channel_info,
    get_oauth_authorization_url,
    test_token,
    validate_oauth_state,
)

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountResponse])
def list_accounts(db: Session = Depends(get_db)) -> list[YouTubeAccount]:
    """Lista contas sem incluir o campo de credenciais."""
    return list(db.scalars(select(YouTubeAccount).order_by(YouTubeAccount.id)).all())


@router.get("/oauth/url")
def oauth_url(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_admin_key),
) -> dict[str, str]:
    """Cria state persistido e retorna a URL de autorização."""
    state = create_oauth_state(db)
    return {"url": get_oauth_authorization_url(settings, state=state)}


@router.get("/oauth/callback")
async def oauth_callback(
    code: str = Query(min_length=1),
    state: str = Query(min_length=1),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    """Conclui o OAuth, salvando ou atualizando a conta autenticada."""
    validate_oauth_state(db, state)
    credentials = await exchange_code_for_tokens(code, settings)
    channel = await get_channel_info(credentials)
    channel_id = channel.get("channel_id")
    name = channel.get("name")
    if not channel_id or not name:
        raise OAuthError("A API do YouTube não retornou dados do canal")
    account = db.scalar(
        select(YouTubeAccount).where(YouTubeAccount.channel_id == channel_id)
    )
    if account is None:
        account = YouTubeAccount(
            name=name,
            channel_id=channel_id,
            avatar_url=channel.get("avatar_url"),
            credentials=encrypt(json.dumps(credentials), settings),
            is_active=True,
        )
        db.add(account)
    else:
        account.name = name
        account.avatar_url = channel.get("avatar_url")
        account.credentials = encrypt(json.dumps(credentials), settings)
        account.is_active = True
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    frontend_url = settings.frontend_url.rstrip("/")
    return RedirectResponse(
        url=f"{frontend_url}/accounts?{urlencode({'connected': 'true'})}",
        status_code=303,
    )


@router.delete("/{account_id}", status_code=204)
def delete_account(
    account_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_key),
) -> None:
    """Remove uma conta e suas credenciais criptografadas."""
    account = db.get(YouTubeAccount, account_id)
    if account is None:
        raise NotFoundError("Conta YouTube não encontrada")
    db.delete(account)
    db.commit()


@router.post("/{account_id}/test")
async def test_account_token(
    account_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_admin_key),
) -> dict[str, bool | str | None]:
    """Testa o token e sincroniza o estado ativo da conta."""
    account = db.get(YouTubeAccount, account_id)
    if account is None:
        raise NotFoundError("Conta YouTube não encontrada")
    try:
        valid = await test_token(account, settings)
    except TokenDecryptionError:
        account.is_active = False
        db.commit()
        return {"valid": False, "error": "credentials_corrupted"}
    account.is_active = valid
    db.commit()
    return {"valid": valid, "error": None if valid else "token_invalid"}
