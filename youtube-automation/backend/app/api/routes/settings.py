"""Endpoints de configuração do sistema."""

import hmac
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import Settings, get_settings
from app.core.exceptions import UnauthorizedError, ValidationError
from app.models.settings import SystemSetting
from app.schemas.settings import SettingsResponse, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])

DEFAULT_SETTINGS = {
    "ollama_url": "http://localhost:11434",
    "ollama_model": "llama3",
    "videos_folder": "",
    "tts_voice": "en-US-JennyNeural",
    "default_dimension": "16:9",
    "clip_min_duration": "3",
    "clip_max_duration": "6",
}
VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv"}


def _validate_ollama_url(value: str) -> None:
    """Garante que a URL use HTTP(S) e tenha um host."""
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValidationError("URL do Ollama inválida")


def _validate_video_folder(value: str, allowed_root: str) -> Path:
    """Valida uma pasta local sem aceitar traversal explícito."""
    path = Path(value).resolve()
    root = Path(allowed_root or "/app/videos").resolve()
    try:
        path.relative_to(root)
    except ValueError:
        raise ValidationError(f"Pasta fora do diretório permitido: {value}") from None
    if not value or not path.is_dir():
        raise ValidationError(f"Pasta não encontrada: {value}")
    return path


def require_admin_key(
    x_admin_key: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    """Protege operações administrativas com a chave secreta da aplicação."""
    if not x_admin_key or not hmac.compare_digest(x_admin_key, settings.secret_key):
        raise UnauthorizedError("Chave administrativa inválida")


@router.get("", response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db)) -> SettingsResponse:
    """Retorna configurações persistidas, preenchendo defaults ausentes."""
    rows = db.scalars(select(SystemSetting)).all()
    values = DEFAULT_SETTINGS.copy()
    values.update({row.key: row.value for row in rows})
    return SettingsResponse(data=values)


@router.put("", response_model=SettingsResponse)
def update_settings(
    payload: SettingsUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_key),
) -> SettingsResponse:
    """Atualiza somente as configurações enviadas pelo cliente."""
    values = payload.as_dict()
    if "ollama_url" in values:
        _validate_ollama_url(values["ollama_url"])
    current = {row.key: row.value for row in db.scalars(select(SystemSetting)).all()}
    merged = {**DEFAULT_SETTINGS, **current, **values}
    if "videos_folder" in values and values["videos_folder"]:
        _validate_video_folder(
            values["videos_folder"],
            current.get("videos_folder", ""),
        )
    if int(merged["clip_max_duration"]) < int(merged["clip_min_duration"]):
        raise ValidationError(
            "clip_max_duration deve ser maior ou igual a clip_min_duration"
        )
    try:
        for key, value in values.items():
            setting = db.get(SystemSetting, key)
            if setting is None:
                db.add(SystemSetting(key=key, value=value))
            else:
                setting.value = value
        db.commit()
    except Exception:
        db.rollback()
        raise
    return get_settings(db)


@router.post("/validate-videos-folder")
def validate_videos_folder(
    payload: dict[str, str],
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_admin_key),
) -> dict[str, object]:
    """Lista vídeos suportados encontrados em uma pasta."""
    folder = payload.get("videos_folder", "")
    path = _validate_video_folder(folder, settings.videos_folder)
    files = [
        item.name
        for item in path.iterdir()
        if item.is_file() and item.suffix.lower() in VIDEO_SUFFIXES
    ]
    return {"path": str(path), "count": len(files), "files": sorted(files)}
