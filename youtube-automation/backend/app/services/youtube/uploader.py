"""Upload resumable de vídeos para a API do YouTube."""

import asyncio
import json
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from sqlalchemy.orm import Session, object_session

from app.core.config import Settings, get_settings
from app.core.exceptions import OAuthError, TokenDecryptionError, YouTubeAPIError
from app.db.database import SessionLocal
from app.models.account import YouTubeAccount
from app.services.youtube.auth import refresh_token_if_expired
from app.services.youtube.schemas import UploadInput

UPLOAD_CHUNK_SIZE = 1024 * 1024


def _publish_at_value(publish_at: datetime) -> str:
    """Converte a data de publicação para RFC 3339 em UTC."""
    if publish_at.tzinfo is None:
        publish_at = publish_at.replace(tzinfo=timezone.utc)
    return publish_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _error_details(error: HttpError) -> tuple[str | None, str]:
    """Extrai reason e mensagem do payload retornado pela API."""
    reason = None
    message = str(error)
    try:
        payload = json.loads(error.content.decode("utf-8"))
        api_error = payload.get("error", {})
        message = api_error.get("message", message)
        errors = api_error.get("errors", [])
        if errors:
            reason = errors[0].get("reason")
    except (AttributeError, TypeError, UnicodeDecodeError, json.JSONDecodeError):
        pass
    return reason, message


def _youtube_api_error(error: HttpError) -> YouTubeAPIError:
    """Converte erro Google para erro de domínio acionável."""
    reason, message = _error_details(error)
    status = getattr(error.resp, "status", None)
    details: dict[str, Any] = {"code": status, "reason": reason}
    if reason == "quotaExceeded":
        message = (
            "Quota do YouTube excedida. A quota renova à meia-noite PT; "
            "reagende o upload automaticamente para 01:00 PT do dia seguinte."
        )
    return YouTubeAPIError(message, details=details)


def _upload_sync(
    credentials: Any,
    payload: UploadInput,
    progress_callback: Callable[[int], None] | None,
) -> str:
    """Executa a parte bloqueante do upload."""
    status: dict[str, Any] = {
        "privacyStatus": "private" if payload.publish_at else payload.privacy,
    }
    if payload.publish_at:
        status["publishAt"] = _publish_at_value(payload.publish_at)
    snippet: dict[str, Any] = {
        "title": payload.title,
        "description": payload.description,
        "categoryId": payload.category_id,
    }
    if payload.tags:
        snippet["tags"] = payload.tags
    try:
        media = MediaFileUpload(
            str(Path(payload.video_path)),
            mimetype="video/*",
            chunksize=UPLOAD_CHUNK_SIZE,
            resumable=True,
        )
        request = (
            build("youtube", "v3", credentials=credentials)
            .videos()
            .insert(
                part="snippet,status",
                body={"snippet": snippet, "status": status},
                media_body=media,
            )
        )
        response = None
        last_progress = -1
        while response is None:
            upload_status, response = request.next_chunk()
            if upload_status is not None and progress_callback is not None:
                last_progress = int(upload_status.progress() * 100)
                progress_callback(last_progress)
        if progress_callback is not None and last_progress != 100:
            progress_callback(100)
    except HttpError as exc:
        raise _youtube_api_error(exc) from exc
    video_id = response.get("id") if response else None
    if not video_id:
        raise YouTubeAPIError(
            "A API do YouTube concluiu o upload sem retornar video_id"
        )
    return video_id


def _mark_account_inactive(account: YouTubeAccount, db: Session | None) -> None:
    """Marca a conta inativa e persiste quando há uma sessão disponível."""
    account.is_active = False
    if db is not None and account.id is not None:
        db.add(account)
        db.commit()


async def upload_video(
    account: YouTubeAccount,
    video_path: str,
    title: str,
    description: str,
    category_id: str = "22",
    privacy: str = "public",
    publish_at: datetime | None = None,
    progress_callback: Callable[[int], None] | None = None,
    *,
    settings: Settings | None = None,
    db: Session | None = None,
    tags: list[str] | None = None,
) -> str:
    """Faz upload resumable e retorna o identificador do vídeo."""
    payload = UploadInput(
        video_path=video_path,
        title=title,
        description=description,
        category_id=category_id,
        privacy=privacy,
        publish_at=publish_at,
        tags=tags or [],
    )
    settings = settings or get_settings()
    session = db or object_session(account)
    owns_session = session is None
    if owns_session:
        session = SessionLocal()
    try:
        try:
            credentials = await refresh_token_if_expired(account, session, settings)
        except TokenDecryptionError:
            _mark_account_inactive(account, session)
            raise
        except OAuthError as exc:
            _mark_account_inactive(account, session)
            raise YouTubeAPIError(
                "Não foi possível renovar as credenciais da conta YouTube",
                details={"reason": "token_refresh_failed"},
            ) from exc
        video_id = await asyncio.to_thread(
            _upload_sync,
            credentials,
            payload,
            progress_callback,
        )
        return video_id
    finally:
        if owns_session:
            session.close()
