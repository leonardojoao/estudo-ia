"""Configuração central da aplicação."""

from functools import lru_cache
from typing import Any

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações carregadas do ambiente e do arquivo `.env`."""

    database_path: str = "/app/data/youtube_automation.db"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    videos_folder: str = ""
    clip_min_duration: int = 3
    clip_max_duration: int = 6
    default_dimension: str = "16:9"
    tts_voice: str = "en-US-JennyNeural"
    oauth_credentials_path: str = "/app/credentials"
    secret_key: str
    cors_origins: str | list[str] = [
        "http://localhost:5173",
        "http://localhost",
    ]
    log_level: str = "INFO"
    environment: str = "production"
    max_workers: int = 2
    max_concurrent_jobs: int = 2
    debug_mode: bool = False
    output_retention_days: int = 7
    audio_preview_ttl_hours: int = 1

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("cors_origins", mode="after")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        """Aceita tanto lista JSON quanto origens separadas por vírgula."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def validate_values(self) -> "Settings":
        """Valida valores que não podem ser verificados por campo isolado."""
        if self.clip_min_duration <= 0:
            raise ValueError("clip_min_duration deve ser maior que zero")
        if self.clip_max_duration < self.clip_min_duration:
            raise ValueError(
                "clip_max_duration deve ser maior ou igual a clip_min_duration"
            )
        if (
            self.environment.lower() == "production"
            and self.secret_key == "TROQUE-ESTA-CHAVE-ANTES-DE-USAR-EM-PRODUCAO"
        ):
            raise ValueError("SECRET_KEY padrão não pode ser usada em produção")
        return self


@lru_cache
def get_settings() -> Settings:
    """Retorna a instância singleton das configurações da aplicação."""
    return Settings()
