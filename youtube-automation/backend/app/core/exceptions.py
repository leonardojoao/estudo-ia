"""Exceções de domínio e handlers HTTP da aplicação."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Erro conhecido da aplicação."""

    status_code = 400
    error_code = "APP_ERROR"

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(AppError):
    """Recurso solicitado não encontrado."""

    status_code = 404
    error_code = "NOT_FOUND"


class ValidationError(AppError):
    """Dados recebidos não atendem às regras de negócio."""

    error_code = "VALIDATION_ERROR"


class OllamaUnavailableError(AppError):
    """O serviço Ollama não está disponível."""

    status_code = 502
    error_code = "OLLAMA_UNAVAILABLE"


class FFmpegError(AppError):
    """Falha ao executar uma operação do FFmpeg."""

    status_code = 500
    error_code = "FFMPEG_ERROR"


class YouTubeAPIError(AppError):
    """Falha na comunicação com a API do YouTube."""

    status_code = 502
    error_code = "YOUTUBE_API_ERROR"


class OAuthError(AppError):
    """Falha no fluxo de autenticação OAuth."""

    status_code = 401
    error_code = "OAUTH_ERROR"


class InsufficientVideosError(AppError):
    """A quantidade de vídeos disponíveis é insuficiente."""

    error_code = "INSUFFICIENT_VIDEOS"


class AntiPlagiarismError(AppError):
    """Falha ao aplicar as regras anti-plágio."""

    status_code = 500
    error_code = "ANTI_PLAGIARISM_ERROR"


def _error_response(
    *,
    error: str,
    message: str,
    details: Any = None,
    status_code: int,
) -> JSONResponse:
    """Cria o formato de erro padronizado da API."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": error,
            "message": message,
            "details": details if details is not None else {},
        },
    )


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    """Converte erros conhecidos em respostas HTTP previsíveis."""
    return _error_response(
        error=exc.error_code,
        message=exc.message,
        details=exc.details,
        status_code=exc.status_code,
    )


async def request_validation_error_handler(
    _: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Formata erros de validação gerados pelo FastAPI/Pydantic."""
    return _error_response(
        error="VALIDATION_ERROR",
        message="Dados de entrada inválidos",
        details=jsonable_encoder(exc.errors()),
        status_code=422,
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Registra falhas inesperadas sem expor detalhes internos em produção."""
    logger.exception(
        "Erro não tratado durante %s %s",
        request.method,
        request.url.path,
        exc_info=exc,
    )
    environment = getattr(request.app.state, "environment", "production").lower()
    details = {"exception": type(exc).__name__} if environment != "production" else {}
    message = str(exc) if environment != "production" else "Erro interno do servidor"
    return _error_response(
        error="INTERNAL_ERROR",
        message=message,
        details=details,
        status_code=500,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Registra os handlers globais de exceções na aplicação FastAPI."""
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(
        RequestValidationError,
        request_validation_error_handler,
    )
    app.add_exception_handler(Exception, unhandled_exception_handler)
