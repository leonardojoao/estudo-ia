"""Criptografia autenticada para tokens armazenados."""

import base64

from cryptography.exceptions import InvalidTag
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import Settings
from app.core.exceptions import TokenDecryptionError

CRYPTO_SALT = b"youtube-automation-fernet-v1"
PBKDF2_ITERATIONS = 390_000


def _derive_key(secret_key: str) -> bytes:
    """Deriva uma chave Fernet estável para segredos arbitrários."""
    derivation = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=CRYPTO_SALT,
        iterations=PBKDF2_ITERATIONS,
    )
    return base64.urlsafe_b64encode(derivation.derive(secret_key.encode("utf-8")))


def get_fernet(settings: Settings) -> Fernet:
    """Cria Fernet usando uma chave válida ou derivando a configuração."""
    try:
        return Fernet(settings.secret_key.encode("ascii"))
    except (UnicodeEncodeError, ValueError):
        return Fernet(_derive_key(settings.secret_key))


def encrypt(data: str, settings: Settings) -> str:
    """Criptografa uma string e retorna o token em texto ASCII."""
    return get_fernet(settings).encrypt(data.encode("utf-8")).decode("ascii")


def decrypt(data: str, settings: Settings) -> str:
    """Descriptografa um token ou lança erro de domínio seguro."""
    try:
        plaintext = get_fernet(settings).decrypt(data.encode("ascii"))
    except (UnicodeEncodeError, ValueError, InvalidToken, InvalidTag) as exc:
        raise TokenDecryptionError(
            "Não foi possível descriptografar o token armazenado"
        ) from exc
    return plaintext.decode("utf-8")
