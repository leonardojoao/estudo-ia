"""Testes do scheduler persistente e jobs de manutenção."""

import os
import time
from datetime import datetime, timedelta, timezone

import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("DATABASE_PATH", ":memory:")

from app.core.config import Settings  # noqa: E402
from app.core.scheduler import (  # noqa: E402
    AUDIO_CLEANUP_JOB_ID,
    OAUTH_CLEANUP_JOB_ID,
    OUTPUT_CLEANUP_JOB_ID,
    cancel_scheduled_job,
    cleanup_audio_previews,
    cleanup_oauth_states,
    cleanup_published_outputs,
    schedule_upload_job,
    shutdown_scheduler,
    start_scheduler,
)
from app.db.database import Base  # noqa: E402
from app.models.oauth_state import OAuthState  # noqa: E402


@pytest.fixture
def isolated_scheduler(monkeypatch, tmp_path):
    """Substitui o singleton por scheduler SQLite temporário."""
    import app.core.scheduler as scheduler_module

    scheduler = AsyncIOScheduler(
        timezone="UTC",
        jobstores={
            "default": scheduler_module.SQLAlchemyJobStore(
                url=f"sqlite:///{tmp_path / 'jobs.sqlite'}"
            )
        },
    )
    monkeypatch.setattr(scheduler_module, "_scheduler", scheduler)
    yield scheduler
    if scheduler.running:
        try:
            scheduler.shutdown(wait=False)
        except RuntimeError:
            pass
    monkeypatch.setattr(scheduler_module, "_scheduler", None)


@pytest.mark.asyncio
async def test_schedule_upload_normalizes_utc_and_can_cancel(isolated_scheduler):
    """Upload futuro deve usar UTC e ser cancelável."""
    isolated_scheduler.start()
    naive_future = datetime.now() + timedelta(minutes=10)

    job_id = await schedule_upload_job(42, naive_future)

    job = isolated_scheduler.get_job(job_id)
    assert job is not None
    assert job.next_run_time.tzinfo is not None
    await cancel_scheduled_job(job_id)
    assert isolated_scheduler.get_job(job_id) is None


@pytest.mark.asyncio
async def test_schedule_upload_rejects_past_date(isolated_scheduler):
    """Data passada não deve criar um job silenciosamente."""
    with pytest.raises(ValueError, match="futuro"):
        await schedule_upload_job(
            42,
            datetime.now(timezone.utc) - timedelta(minutes=1),
        )


def test_start_scheduler_registers_stable_maintenance_jobs(
    isolated_scheduler,
):
    """Startup registra exatamente os jobs de manutenção esperados."""
    start_scheduler(Settings(secret_key="test-secret", environment="test"))

    assert isolated_scheduler.get_job(AUDIO_CLEANUP_JOB_ID) is not None
    assert isolated_scheduler.get_job(OAUTH_CLEANUP_JOB_ID) is not None
    assert isolated_scheduler.get_job(OUTPUT_CLEANUP_JOB_ID) is not None
    shutdown_scheduler()


def test_cleanup_audio_previews_removes_only_expired_files(tmp_path, monkeypatch):
    """Preview recente deve ser preservado e preview antigo removido."""
    import app.core.scheduler as scheduler_module

    old_file = tmp_path / "old.mp3"
    recent_file = tmp_path / "recent.mp3"
    old_file.write_bytes(b"old")
    recent_file.write_bytes(b"recent")
    old_time = time.time() - 7200
    os.utime(old_file, (old_time, old_time))
    monkeypatch.setattr(scheduler_module, "Path", lambda _: tmp_path)

    removed = cleanup_audio_previews(
        Settings(
            secret_key="test-secret",
            environment="test",
            audio_preview_ttl_hours=1,
        )
    )

    assert removed == 1
    assert not old_file.exists()
    assert recent_file.exists()


def test_cleanup_oauth_states_deletes_expired_rows(monkeypatch):
    """States expirados devem ser removidos pelo job periódico."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    monkeypatch.setattr(
        "app.core.scheduler.SessionLocal",
        sessionmaker(bind=engine),
    )
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with Session(engine) as db:
        db.add_all(
            [
                OAuthState(
                    state_token="expired",
                    created_at=now - timedelta(hours=1),
                    expires_at=now - timedelta(minutes=1),
                ),
                OAuthState(
                    state_token="valid",
                    created_at=now,
                    expires_at=now + timedelta(minutes=5),
                ),
            ]
        )
        db.commit()
    assert cleanup_oauth_states() == 1
    with Session(engine) as db:
        assert db.get(OAuthState, "expired") is None
        assert db.get(OAuthState, "valid") is not None


def test_cleanup_outputs_preserves_unpublished_files(tmp_path, monkeypatch):
    """Output antigo sem URL publicada não deve ser removido."""
    import app.core.scheduler as scheduler_module

    output = tmp_path / "output.mp4"
    output.write_bytes(b"video")
    old_time = time.time() - 10 * 86400
    os.utime(output, (old_time, old_time))
    monkeypatch.setattr(scheduler_module, "Path", lambda value: tmp_path)

    removed = cleanup_published_outputs(
        Settings(
            secret_key="test-secret",
            environment="test",
            output_retention_days=7,
        )
    )

    assert removed == 0
    assert output.exists()
