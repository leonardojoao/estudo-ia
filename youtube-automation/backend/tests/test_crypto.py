"""Testes da criptografia de tokens."""

import base64

import pytest
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import Settings
from app.core.crypto import decrypt, encrypt, get_fernet
from app.core.exceptions import TokenDecryptionError


def _settings(secret_key: str) -> Settings:
    return Settings(
        secret_key=secret_key,
        environment="test",
    )


def test_short_secret_round_trip() -> None:
    """Segredos comuns devem ser derivados para uma chave Fernet válida."""
    settings = _settings("test-secret")

    token = encrypt("oauth-token", settings)

    assert decrypt(token, settings) == "oauth-token"


def test_valid_fernet_key_is_used_directly() -> None:
    """Uma chave Fernet válida deve permanecer interoperável."""
    key = Fernet.generate_key().decode("ascii")
    settings = _settings(key)

    assert get_fernet(settings).encrypt(b"data")
    assert decrypt(encrypt("data", settings), settings) == "data"


def test_derived_key_is_stable() -> None:
    """Instâncias equivalentes devem derivar a mesma chave."""
    first = get_fernet(_settings("stable-secret")).encrypt(b"data")
    second = get_fernet(_settings("stable-secret"))

    assert second.decrypt(first) == b"data"


def test_different_secret_cannot_decrypt() -> None:
    """Outro segredo não pode autenticar o token."""
    token = encrypt("private", _settings("secret-one"))

    with pytest.raises(TokenDecryptionError):
        decrypt(token, _settings("secret-two"))


def test_corrupted_token_raises_domain_error() -> None:
    """Dados corrompidos não devem vazar InvalidToken."""
    with pytest.raises(TokenDecryptionError, match="descriptografar"):
        decrypt("not-a-token", _settings("test-secret"))


def test_valid_fernet_key_is_not_derived() -> None:
    """O caminho direto deve produzir exatamente a chave configurada."""
    key = Fernet.generate_key()
    settings = _settings(key.decode("ascii"))

    assert (
        base64.urlsafe_b64encode(
            get_fernet(settings)._signing_key + get_fernet(settings)._encryption_key
        )
        == key
    )
    with pytest.raises(InvalidToken):
        Fernet(key).decrypt(encrypt("data", _settings("other-secret")).encode())
