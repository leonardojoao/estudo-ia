"""Testes das rotas de contas YouTube."""

import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("DATABASE_PATH", ":memory:")

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.models.account import YouTubeAccount  # noqa: E402
from app.services.youtube.auth import create_oauth_state  # noqa: E402

ADMIN_KEY = os.environ["SECRET_KEY"]


def _clear_accounts() -> None:
    with SessionLocal.begin() as db:
        db.query(YouTubeAccount).delete()


def test_list_accounts_does_not_expose_credentials() -> None:
    """A listagem deve omitir o campo sensível."""
    _clear_accounts()
    with SessionLocal.begin() as db:
        db.add(
            YouTubeAccount(
                name="Channel",
                channel_id="channel-list",
                credentials="encrypted-secret",
            )
        )

    with TestClient(app) as client:
        response = client.get("/api/accounts")

    assert response.status_code == 200
    assert response.json()[0]["channel_id"] == "channel-list"
    assert "credentials" not in response.json()[0]


def test_oauth_url_requires_admin_key(monkeypatch) -> None:
    """A criação de state deve exigir a proteção administrativa."""
    monkeypatch.setattr(
        "app.api.routes.accounts.get_oauth_authorization_url",
        lambda settings, state: f"https://oauth.test/?state={state}",
    )
    with TestClient(app) as client:
        unauthorized = client.get("/api/accounts/oauth/url")
        authorized = client.get(
            "/api/accounts/oauth/url",
            headers={"X-Admin-Key": ADMIN_KEY},
        )

    assert unauthorized.status_code == 401
    assert authorized.status_code == 200
    assert "state=" in authorized.json()["url"]


def test_oauth_callback_creates_account_and_redirects(monkeypatch) -> None:
    """Callback deve salvar a conta e redirecionar sem tokens na URL."""
    _clear_accounts()
    with SessionLocal() as db:
        state = create_oauth_state(db)

    async def exchange_code(code, settings):
        return {"token": "access", "refresh_token": "refresh"}

    async def channel_info(credentials):
        return {
            "channel_id": "channel-callback",
            "name": "Callback Channel",
            "avatar_url": "https://avatar.test/image.png",
        }

    monkeypatch.setattr(
        "app.api.routes.accounts.exchange_code_for_tokens",
        exchange_code,
    )
    monkeypatch.setattr(
        "app.api.routes.accounts.get_channel_info",
        channel_info,
    )

    with TestClient(app, follow_redirects=False) as client:
        response = client.get(
            "/api/accounts/oauth/callback",
            params={"code": "code", "state": state},
        )

    assert response.status_code == 303
    assert response.headers["location"] == (
        f"{get_settings().frontend_url}/accounts?connected=true"
    )
    with SessionLocal() as db:
        account = (
            db.query(YouTubeAccount).filter_by(channel_id="channel-callback").one()
        )
        assert account.name == "Callback Channel"
        assert account.credentials != "access"

    with SessionLocal() as db:
        second_state = create_oauth_state(db)
    with TestClient(app, follow_redirects=False) as client:
        second_response = client.get(
            "/api/accounts/oauth/callback",
            params={"code": "second-code", "state": second_state},
        )

    assert second_response.status_code == 303
    with SessionLocal() as db:
        assert (
            db.query(YouTubeAccount).filter_by(channel_id="channel-callback").count()
            == 1
        )


def test_token_test_returns_false_without_500(monkeypatch) -> None:
    """Token inválido deve retornar um erro de domínio no payload."""
    _clear_accounts()
    with SessionLocal.begin() as db:
        account = YouTubeAccount(
            name="Invalid",
            channel_id="channel-invalid",
            credentials="encrypted-secret",
        )
        db.add(account)
        db.flush()
        account_id = account.id

    async def invalid_token(account, settings):
        return False

    monkeypatch.setattr("app.api.routes.accounts.test_token", invalid_token)
    with TestClient(app) as client:
        response = client.post(
            f"/api/accounts/{account_id}/test",
            headers={"X-Admin-Key": ADMIN_KEY},
        )

    assert response.status_code == 200
    assert response.json() == {"valid": False, "error": "token_invalid"}


def test_delete_account_requires_admin_key() -> None:
    """Remoção sem chave não deve apagar a conta."""
    _clear_accounts()
    with SessionLocal.begin() as db:
        account = YouTubeAccount(
            name="Delete",
            channel_id="channel-delete",
            credentials="encrypted-secret",
        )
        db.add(account)

    with TestClient(app) as client:
        response = client.delete("/api/accounts/1")

    assert response.status_code == 401
    with SessionLocal() as db:
        account_id = (
            db.query(YouTubeAccount).filter_by(channel_id="channel-delete").one().id
        )
    with TestClient(app) as client:
        response = client.delete(
            f"/api/accounts/{account_id}",
            headers={"X-Admin-Key": ADMIN_KEY},
        )
    assert response.status_code == 204
    with SessionLocal() as db:
        assert db.get(YouTubeAccount, account_id) is None
