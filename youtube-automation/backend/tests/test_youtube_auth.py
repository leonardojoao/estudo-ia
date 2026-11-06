"""Testes do fluxo OAuth2 do YouTube."""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from google.oauth2.credentials import Credentials

from app.core.config import Settings
from app.core.crypto import encrypt
from app.core.exceptions import OAuthError, TokenDecryptionError
from app.models.account import YouTubeAccount
from app.services.youtube.auth import (
    YOUTUBE_SCOPES,
    exchange_code_for_tokens,
    extract_state,
    get_channel_info,
    get_oauth_authorization_url,
    refresh_token_if_expired,
    test_token as check_token,
)


def _settings(tmp_path) -> Settings:
    client_secret = tmp_path / "client_secret.json"
    client_secret.write_text("{}", encoding="utf-8")
    return Settings(
        secret_key="test-secret",
        environment="test",
        oauth_credentials_path=str(tmp_path),
    )


def _credentials(expired: bool = False) -> Credentials:
    expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    if expired:
        expiry = datetime.now(timezone.utc) - timedelta(hours=1)
    return Credentials(
        token="access-token",
        refresh_token="refresh-token",
        token_uri="https://oauth2.googleapis.com/token",
        client_id="client-id",
        client_secret="client-secret",
        scopes=YOUTUBE_SCOPES,
        expiry=expiry,
    )


def test_authorization_url_contains_oauth_parameters(monkeypatch, tmp_path):
    """A URL deve carregar state, escopos e parâmetros offline."""
    settings = _settings(tmp_path)
    flow = Mock()
    flow.authorization_url.return_value = (
        "https://accounts.google.test/auth?state=state-token",
        "state-token",
    )
    monkeypatch.setattr(
        "app.services.youtube.auth._create_flow",
        Mock(return_value=flow),
    )
    monkeypatch.setattr(
        "app.services.youtube.auth.secrets.token_urlsafe",
        Mock(return_value="state-token"),
    )

    url = get_oauth_authorization_url(settings)

    flow.authorization_url.assert_called_once()
    kwargs = flow.authorization_url.call_args.kwargs
    assert kwargs["access_type"] == "offline"
    assert kwargs["prompt"] == "consent"
    assert kwargs["state"] == "state-token"
    assert flow.redirect_uri == settings.oauth_redirect_uri
    assert extract_state(url) == "state-token"


def test_authorization_rejects_missing_client_secret(tmp_path):
    """Arquivo de credenciais ausente deve gerar erro explícito."""
    settings = Settings(
        secret_key="test-secret",
        environment="test",
        oauth_credentials_path=str(tmp_path / "missing"),
    )

    with pytest.raises(OAuthError, match="client_secret"):
        get_oauth_authorization_url(settings)


@pytest.mark.asyncio
async def test_exchange_code_returns_serializable_payload(monkeypatch, tmp_path):
    """A troca deve retornar os campos serializáveis das credenciais."""
    credentials = _credentials()
    flow = Mock(credentials=credentials)
    flow.fetch_token.return_value = None
    monkeypatch.setattr(
        "app.services.youtube.auth._create_flow",
        Mock(return_value=flow),
    )

    result = await exchange_code_for_tokens("code", _settings(tmp_path))

    flow.fetch_token.assert_called_once_with(code="code")
    assert result["token"] == "access-token"
    assert result["refresh_token"] == "refresh-token"


@pytest.mark.asyncio
async def test_channel_info_normalizes_youtube_response(monkeypatch):
    """A resposta do canal deve ser convertida para o contrato público."""
    service = Mock()
    service.channels.return_value.list.return_value.execute.return_value = {
        "items": [
            {
                "id": "channel-id",
                "snippet": {
                    "title": "Channel",
                    "thumbnails": {"default": {"url": "https://avatar.test"}},
                },
            }
        ]
    }
    monkeypatch.setattr(
        "app.services.youtube.auth._credentials_from_dict",
        Mock(return_value=_credentials()),
    )
    monkeypatch.setattr("app.services.youtube.auth.build", Mock(return_value=service))

    result = await get_channel_info({"token": "token"})

    assert result == {
        "channel_id": "channel-id",
        "name": "Channel",
        "avatar_url": "https://avatar.test",
    }


@pytest.mark.asyncio
async def test_refresh_updates_encrypted_credentials(monkeypatch, tmp_path):
    """Token expirado deve ser renovado e persistido."""
    settings = _settings(tmp_path)
    account = YouTubeAccount(
        name="Channel",
        channel_id="channel-id",
        credentials=encrypt(json.dumps({"token": "old"}), settings),
    )
    credentials = Mock(
        expired=True,
        refresh_token="refresh-token",
        to_json=Mock(return_value=json.dumps({"token": "new"})),
    )
    credentials.refresh.return_value = None
    monkeypatch.setattr(
        "app.services.youtube.auth._credentials_from_dict",
        Mock(return_value=credentials),
    )
    db = Mock()

    result = await refresh_token_if_expired(account, db, settings)

    assert result is credentials
    credentials.refresh.assert_called_once()
    db.commit.assert_called_once()
    assert account.credentials != encrypt(json.dumps({"token": "old"}), settings)


@pytest.mark.asyncio
async def test_invalid_token_returns_false(monkeypatch, tmp_path):
    """Falha na chamada do YouTube deve retornar False."""
    settings = _settings(tmp_path)
    account = YouTubeAccount(
        name="Channel",
        channel_id="channel-id",
        credentials=encrypt(json.dumps({"token": "invalid"}), settings),
    )
    monkeypatch.setattr(
        "app.services.youtube.auth._test_token",
        Mock(return_value=False),
    )

    assert await check_token(account, settings) is False


@pytest.mark.asyncio
async def test_corrupted_credentials_are_not_treated_as_invalid_token(
    tmp_path,
):
    """Credenciais corrompidas devem permanecer distinguíveis."""
    settings = _settings(tmp_path)
    account = YouTubeAccount(
        name="Channel",
        channel_id="channel-id",
        credentials="corrupted",
    )

    with pytest.raises(TokenDecryptionError):
        await refresh_token_if_expired(account, Mock(), settings)
