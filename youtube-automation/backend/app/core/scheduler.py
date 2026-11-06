"""Scheduler persistente e tarefas periódicas de manutenção."""

import logging
from datetime import datetime, timezone
from pathlib import Path

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import delete, select

from app.core.config import Settings, get_settings
from app.db.database import SessionLocal
from app.models.job import ProcessingJob
from app.models.oauth_state import OAuthState

logger = logging.getLogger(__name__)

UPLOAD_JOB_PREFIX = "upload:"
AUDIO_CLEANUP_JOB_ID = "maintenance:audio-preview"
OAUTH_CLEANUP_JOB_ID = "maintenance:oauth-states"
OUTPUT_CLEANUP_JOB_ID = "maintenance:outputs"

_scheduler: AsyncIOScheduler | None = None


def _database_url(settings: Settings) -> str:
    """Converte o caminho configurado no formato aceito pelo job store."""
    if settings.database_path.startswith("sqlite:"):
        return settings.database_path
    if settings.database_path == ":memory:":
        return "sqlite://"
    return f"sqlite:///{settings.database_path}"


def get_scheduler(settings: Settings | None = None) -> AsyncIOScheduler:
    """Retorna o scheduler singleton com persistência SQLAlchemy."""
    global _scheduler
    if _scheduler is None:
        settings = settings or get_settings()
        _scheduler = AsyncIOScheduler(
            timezone="UTC",
            jobstores={"default": SQLAlchemyJobStore(url=_database_url(settings))},
        )
    return _scheduler


async def _upload_placeholder(job_id: int) -> None:
    """Falha explicitamente até o pipeline runner assumir a execução."""
    raise RuntimeError(
        f"Upload agendado para o job {job_id} requer o pipeline runner da TASK-036"
    )


def _utc_datetime(value: datetime) -> datetime:
    """Normaliza datas ingênuas ou com offset para UTC."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


async def schedule_upload_job(job_id: int, scheduled_at: datetime) -> str:
    """Agenda um upload futuro em UTC e retorna seu identificador."""
    run_at = _utc_datetime(scheduled_at)
    if run_at <= datetime.now(timezone.utc):
        raise ValueError("scheduled_at deve estar no futuro")
    scheduler_job_id = f"{UPLOAD_JOB_PREFIX}{job_id}"
    get_scheduler().add_job(
        _upload_placeholder,
        trigger="date",
        run_date=run_at,
        args=[job_id],
        id=scheduler_job_id,
        replace_existing=True,
    )
    return scheduler_job_id


async def cancel_scheduled_job(scheduler_job_id: str) -> None:
    """Cancela um job sem falhar quando ele já não existe."""
    scheduler = get_scheduler()
    if scheduler.get_job(scheduler_job_id) is not None:
        scheduler.remove_job(scheduler_job_id)


def cleanup_audio_previews(settings: Settings | None = None) -> int:
    """Remove previews de áudio que excederam o TTL configurado."""
    settings = settings or get_settings()
    root = Path("/tmp/audio_preview")
    cutoff = datetime.now().timestamp() - settings.audio_preview_ttl_hours * 3600
    removed = 0
    if not root.is_dir():
        return removed
    for path in root.iterdir():
        if path.is_file() and path.stat().st_mtime < cutoff:
            path.unlink()
            removed += 1
    return removed


def cleanup_oauth_states() -> int:
    """Remove states OAuth expirados."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with SessionLocal.begin() as db:
        result = db.execute(delete(OAuthState).where(OAuthState.expires_at < now))
        return result.rowcount or 0


def cleanup_published_outputs(settings: Settings | None = None) -> int:
    """Remove outputs antigos apenas quando o job foi publicado."""
    settings = settings or get_settings()
    root = Path("/app/output")
    cutoff = datetime.now().timestamp() - settings.output_retention_days * 86400
    removed = 0
    with SessionLocal() as db:
        published_paths = {
            Path(job.output_video).resolve()
            for job in db.scalars(
                select(ProcessingJob).where(ProcessingJob.youtube_urls.is_not(None))
            )
            if job.output_video
        }
    if not root.is_dir():
        return removed
    for path in root.iterdir():
        if (
            path.is_file()
            and path.resolve() in published_paths
            and path.stat().st_mtime < cutoff
        ):
            path.unlink()
            removed += 1
    return removed


def _run_cleanup(task_name: str, task) -> None:
    """Executa manutenção sem deixar uma falha derrubar o scheduler."""
    try:
        removed = task()
        logger.info("Scheduler cleanup %s removed %d items", task_name, removed)
    except (OSError, RuntimeError, ValueError):
        logger.exception("Scheduler cleanup %s failed", task_name)


def _run_audio_cleanup() -> None:
    """Entry point persistente para a limpeza de previews."""
    _run_cleanup("audio-preview", cleanup_audio_previews)


def _run_oauth_cleanup() -> None:
    """Entry point persistente para a limpeza de states."""
    _run_cleanup("oauth-states", cleanup_oauth_states)


def _run_output_cleanup() -> None:
    """Entry point persistente para a limpeza de outputs."""
    _run_cleanup("outputs", cleanup_published_outputs)


def _register_maintenance_jobs(scheduler: AsyncIOScheduler) -> None:
    """Registra jobs recorrentes com IDs estáveis."""
    scheduler.add_job(
        _run_audio_cleanup,
        trigger="interval",
        hours=1,
        id=AUDIO_CLEANUP_JOB_ID,
        replace_existing=True,
    )
    scheduler.add_job(
        _run_oauth_cleanup,
        trigger="interval",
        minutes=30,
        id=OAUTH_CLEANUP_JOB_ID,
        replace_existing=True,
    )
    scheduler.add_job(
        _run_output_cleanup,
        trigger="interval",
        days=1,
        id=OUTPUT_CLEANUP_JOB_ID,
        replace_existing=True,
    )


def start_scheduler(settings: Settings | None = None) -> AsyncIOScheduler:
    """Inicia o scheduler e garante os jobs periódicos."""
    scheduler = get_scheduler(settings)
    if not scheduler.running:
        _register_maintenance_jobs(scheduler)
        scheduler.start()
    return scheduler


def shutdown_scheduler() -> None:
    """Para o scheduler ativo sem bloquear o encerramento da aplicação."""
    global _scheduler
    scheduler = _scheduler
    if scheduler is not None and scheduler.running:
        scheduler.shutdown(wait=False)
    _scheduler = None
