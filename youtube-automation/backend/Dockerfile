# syntax=docker/dockerfile:1.6
# =============================================================================
# Backend Dockerfile — YouTube Automation
# Estágios: builder → development → runtime
# =============================================================================

# =============================================================================
# Stage 1: builder — instala e compila dependências Python
# =============================================================================
FROM python:3.11-slim AS builder

WORKDIR /app

# Dependências de sistema para compilar pacotes Python nativos
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
    && rm -rf /var/lib/apt/lists/*

# Cria ambiente virtual isolado para produção
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Instala dependências em camada separada para cache eficiente
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Stage 2: development — builder + FFmpeg + ferramentas de dev
# Usado pelo docker-compose.dev.yml (build.target: development)
# =============================================================================
FROM builder AS development

# FFmpeg + utilitários para desenvolvimento local
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        wget \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Ferramentas de desenvolvimento, teste e qualidade de código
RUN pip install --no-cache-dir \
    pytest==8.2.0 \
    pytest-cov==5.0.0 \
    pytest-asyncio==0.23.6 \
    httpx==0.27.0 \
    ruff==0.4.4 \
    black==24.4.2

# Diretórios de dados — sobrescritos por volumes em dev
RUN mkdir -p /app/data /app/videos /app/credentials /app/output

EXPOSE 8000

# Hot reload habilitado por padrão no estágio de dev
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "debug"]

# =============================================================================
# Stage 3: runtime — imagem mínima de produção (sem build tools, sem dev deps)
# =============================================================================
FROM python:3.11-slim AS runtime

WORKDIR /app

LABEL maintainer="youtube-automation" \
      description="Backend FastAPI — YouTube Automation" \
      version="1.0"

# FFmpeg (processamento de vídeo) + wget (healthcheck)
# Sem gcc, sem build-essential — imagem mínima
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        wget \
    && rm -rf /var/lib/apt/lists/* \
    && ffmpeg -version 2>&1 | head -1

# Cria usuário não-root (princípio de menor privilégio)
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid 1001 --shell /bin/sh --create-home appuser

# Copia ambiente virtual do builder — sem ferramentas de compilação
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Diretórios para dados persistentes (montados como volumes pelo compose)
RUN mkdir -p /app/data /app/videos /app/credentials /app/output && \
    chown -R appuser:appgroup /app

# Copia código da aplicação com permissões corretas
COPY --chown=appuser:appgroup . .

# Executa como usuário não-root
USER appuser

EXPOSE 8000

# Verifica o endpoint /health do FastAPI a cada 30s
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD wget -qO- http://localhost:8000/health || exit 1

# Single worker — SQLite não suporta múltiplos writers concorrentes
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
