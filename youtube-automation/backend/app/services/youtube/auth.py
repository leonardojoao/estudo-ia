"""Fluxo OAuth2 e credenciais da API do YouTube."""

import asyncio
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from google.auth.transport.requests import Request
from google.auth.exceptions import GoogleAuthError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from oauthlib.oauth2.rfc6749.errors import OAuth2Error
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.crypto import decrypt, encrypt
from app.core.exceptions import OAuthError, TokenDecryptionError, YouTubeAPIError
from app.models.account import YouTubeAccount

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def _client_secret_file(settings: Settings) -> str:
    """Resolve o client secret a partir de arquivo ou diretório."""
    configured = Path(settings.oauth_credentials_path)
    if configured.is_file():
        return str(configured)
    if configured.is_dir():
        client_secret = configured / "client_secret.json"
        if client_secret.is_file():
            return str(client_secret)
    raise OAuthError(
        "Arquivo client_secret.json não encontrado em oauth_credentials_path"
    )


def _create_flow(settings: Settings) -> InstalledAppFlow:
    """Cria um flow Google com as configurações do projeto."""
    return InstalledAppFlow.from_client_secrets_file(
        _client_secret_file(settings),
        scopes=YOUTUBE_SCOPES,
    )


def get_oauth_authorization_url(settings: Settings) -> str:
    """Gera a URL de autorização OAuth do YouTube."""
    flow = _create_flow(settings)
    flow.redirect_uri = settings.oauth_redirect_uri
    state = secrets.token_urlsafe(32)
    authorization_url, returned_state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )
    if returned_state != state:
        raise OAuthError("O provedor OAuth retornou um state inconsistente")
    return authorization_url


def _credentials_to_dict(credentials: Credentials) -> dict[str, Any]:
    """Converte credenciais Google em estrutura JSON serializável."""
    return json.loads(credentials.to_json())


def _exchange_code(code: str, settings: Settings) -> dict[str, Any]:
    """Troca o authorization code de forma síncrona."""
    flow = _create_flow(settings)
    flow.redirect_uri = settings.oauth_redirect_uri
    try:
        flow.fetch_token(code=code)
    except (GoogleAuthError, OAuth2Error, OSError, ValueError) as exc:
        raise OAuthError("Não foi possível trocar o código OAuth") from exc
    return _credentials_to_dict(flow.credentials)


async def exchange_code_for_tokens(
    code: str,
    settings: Settings,
) -> dict[str, Any]:
    """Troca um código OAuth por credenciais serializáveis."""
    if not code.strip():
        raise OAuthError("Código OAuth não pode ser vazio")
    return await asyncio.to_thread(_exchange_code, code, settings)


def _credentials_from_dict(credentials: dict[str, Any]) -> Credentials:
    """Cria Credentials sem aceitar um payload vazio."""
    if not credentials:
        raise OAuthError("Credenciais OAuth vazias")
    try:
        return Credentials.from_authorized_user_info(credentials, YOUTUBE_SCOPES)
    except (TypeError, ValueError) as exc:
        raise OAuthError("Formato de credenciais OAuth inválido") from exc


def _channel_info(credentials: dict[str, Any]) -> dict[str, str | None]:
    """Consulta os dados públicos do canal autenticado."""
    google_credentials = _credentials_from_dict(credentials)
    try:
        response = (
            build("youtube", "v3", credentials=google_credentials)
            .channels()
            .list(part="snippet", mine=True)
            .execute()
        )
    except HttpError as exc:
        raise YouTubeAPIError("Não foi possível consultar o canal YouTube") from exc
    items = response.get("items", [])
    if not items:
        raise YouTubeAPIError("A conta OAuth não possui um canal YouTube")
    snippet = items[0].get("snippet", {})
    return {
        "channel_id": items[0].get("id"),
        "name": snippet.get("title"),
        "avatar_url": snippet.get("thumbnails", {}).get("default", {}).get("url"),
    }


async def get_channel_info(
    credentials: dict[str, Any],
) -> dict[str, str | None]:
    """Busca nome, ID e avatar do canal autenticado."""
    return await asyncio.to_thread(_channel_info, credentials)


def _refresh_account(
    account: YouTubeAccount,
    db: Session,
    settings: Settings,
) -> Credentials:
    """Renova credenciais e persiste o JSON criptografado."""
    try:
        payload = json.loads(decrypt(account.credentials, settings))
    except (json.JSONDecodeError, TokenDecryptionError) as exc:
        raise TokenDecryptionError(
            "As credenciais armazenadas da conta estão corrompidas"
        ) from exc
    credentials = _credentials_from_dict(payload)
    if credentials.expired:
        if not credentials.refresh_token:
            raise OAuthError("A conta não possui refresh token")
        try:
            credentials.refresh(Request())
        except (GoogleAuthError, OSError, ValueError) as exc:
            raise OAuthError("Não foi possível renovar o token OAuth") from exc
        account.credentials = encrypt(credentials.to_json(), settings)
        account.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.add(account)
        db.commit()
        db.refresh(account)
    return credentials


async def refresh_token_if_expired(
    account: YouTubeAccount,
    db: Session,
    settings: Settings,
) -> Credentials:
    """Verifica, renova e persiste o token expirado."""
    return await asyncio.to_thread(_refresh_account, account, db, settings)


def _test_token(credentials: dict[str, Any]) -> bool:
    """Testa o token com uma chamada mínima à API."""
    try:
        google_credentials = _credentials_from_dict(credentials)
        (
            build("youtube", "v3", credentials=google_credentials)
            .channels()
            .list(part="id", mine=True)
            .execute()
        )
        return True
    except (GoogleAuthError, HttpError, OAuthError, ValueError, TypeError):
        return False


async def test_token(
    account: YouTubeAccount,
    settings: Settings,
) -> bool:
    """Retorna se as credenciais criptografadas ainda são válidas."""
    try:
        payload = json.loads(decrypt(account.credentials, settings))
    except (json.JSONDecodeError, TokenDecryptionError):
        return False
    return await asyncio.to_thread(_test_token, payload)


def extract_state(url: str) -> str | None:
    """Extrai state para integração e persistência da rota OAuth."""
    return parse_qs(urlparse(url).query).get("state", [None])[0]
