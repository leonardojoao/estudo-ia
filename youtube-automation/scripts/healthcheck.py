#!/usr/bin/env python3
"""
Script de verificação de saúde do ambiente — YouTube Automation.

Verifica:
  1. Backend FastAPI respondendo no endpoint /health
  2. Diretório do banco de dados acessível
  3. Ollama acessível e com modelos instalados
  4. FFmpeg instalado e funcional
  5. Pasta de vídeos configurada e com arquivos suportados

Uso:
  python scripts/healthcheck.py

Códigos de saída:
  0 — todos os checks passaram
  1 — um ou mais checks falharam

Variáveis de ambiente (com fallbacks):
  BACKEND_URL    — URL do backend  (padrão: http://localhost:8000)
  OLLAMA_URL     — URL do Ollama   (padrão: http://localhost:11434)
  DATABASE_PATH  — Path do banco   (padrão: ./data/youtube_automation.db)
  VIDEOS_FOLDER_HOST — Pasta de vídeos no host (padrão: ./videos)
"""

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Extensões de vídeo suportadas pelo pipeline
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}

# Códigos ANSI para output colorido no terminal
RED   = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RESET = "\033[0m"


def _ok(msg: str) -> bool:
    print(f"  {GREEN}✓{RESET} {msg}")
    return True


def _fail(msg: str) -> bool:
    print(f"  {RED}✗{RESET} {msg}")
    return False


def _warn(msg: str) -> bool:
    print(f"  {YELLOW}⚠{RESET} {msg}")
    return False


def check_backend() -> bool:
    """Verifica se o backend FastAPI está respondendo no endpoint /health."""
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
    url = f"{backend_url}/health"

    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                try:
                    data = json.loads(response.read().decode())
                    status = data.get("status", "unknown")
                    return _ok(f"Backend: HTTP 200 — status={status} ({url})")
                except (json.JSONDecodeError, AttributeError):
                    return _ok(f"Backend: HTTP 200 ({url})")
            else:
                return _fail(f"Backend: HTTP {response.status} ({url})")

    except urllib.error.URLError as e:
        reason = getattr(e, "reason", str(e))
        return _fail(
            f"Backend: não acessível em {url}\n"
            f"         Causa: {reason}\n"
            f"         → Verifique se o container está rodando: docker compose ps"
        )
    except TimeoutError:
        return _fail(f"Backend: timeout ao conectar em {url} (>5s)")


def check_database() -> bool:
    """Verifica se o diretório do banco de dados existe e tem permissão de escrita."""
    db_path_str = os.getenv("DATABASE_PATH", "./data/youtube_automation.db")
    db_path = Path(db_path_str)
    db_dir = db_path.parent

    if not db_dir.exists():
        return _fail(
            f"Banco de dados: diretório '{db_dir}' não existe\n"
            f"         → Execute: mkdir -p {db_dir}"
        )

    if not os.access(db_dir, os.W_OK):
        return _fail(
            f"Banco de dados: sem permissão de escrita em '{db_dir}'\n"
            f"         → Verifique as permissões do diretório"
        )

    if db_path.exists():
        size_kb = db_path.stat().st_size / 1024
        return _ok(f"Banco de dados: '{db_path}' ({size_kb:.1f} KB)")
    else:
        return _ok(
            f"Banco de dados: diretório '{db_dir}' OK — "
            f"banco será criado na primeira execução"
        )


def check_ollama() -> bool:
    """Verifica se o Ollama está acessível e lista os modelos instalados."""
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    url = f"{ollama_url}/api/tags"

    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                models = data.get("models", [])
                model_names = [m.get("name", "?") for m in models]

                if not models:
                    return _warn(
                        f"Ollama: acessível em {ollama_url} mas sem modelos instalados\n"
                        f"         → Instale um modelo: ollama pull llama3"
                    )

                return _ok(
                    f"Ollama: {len(models)} modelo(s) em {ollama_url}\n"
                    f"         Modelos: {', '.join(model_names[:5])}"
                    + (" ..." if len(model_names) > 5 else "")
                )
            else:
                return _fail(f"Ollama: HTTP {response.status} ({url})")

    except urllib.error.URLError as e:
        reason = getattr(e, "reason", str(e))
        return _fail(
            f"Ollama: não acessível em {ollama_url}\n"
            f"         Causa: {reason}\n"
            f"         → Inicie o Ollama: ollama serve"
        )
    except TimeoutError:
        return _fail(f"Ollama: timeout ao conectar em {ollama_url} (>5s)")


def check_ffmpeg() -> bool:
    """Verifica se o FFmpeg está instalado e funcionando."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            # Extrai apenas a versão da primeira linha
            first_line = result.stdout.split("\n")[0]
            # Formato típico: "ffmpeg version N.N.N ..."
            version_info = first_line.replace("ffmpeg version ", "").split(" ")[0]
            return _ok(f"FFmpeg: versão {version_info}")
        else:
            return _fail(
                f"FFmpeg: erro ao executar\n"
                f"         Stderr: {result.stderr[:100]}"
            )

    except FileNotFoundError:
        return _fail(
            "FFmpeg: não encontrado no PATH\n"
            "         → Linux/Mac: sudo apt install ffmpeg | brew install ffmpeg\n"
            "         → Windows:   https://ffmpeg.org/download.html\n"
            "         → Docker:    já instalado automaticamente no container"
        )
    except subprocess.TimeoutExpired:
        return _fail("FFmpeg: timeout ao executar (>5s)")


def check_videos_folder() -> bool:
    """Verifica se a pasta de vídeos está configurada, existe e contém arquivos suportados."""
    # Tenta VIDEOS_FOLDER_HOST (host) ou VIDEOS_FOLDER (container)
    folder_path = os.getenv("VIDEOS_FOLDER_HOST") or os.getenv("VIDEOS_FOLDER", "")

    if not folder_path:
        return _warn(
            "Pasta de vídeos: não configurada\n"
            "         → Defina VIDEOS_FOLDER_HOST no seu .env\n"
            "         → Exemplo: VIDEOS_FOLDER_HOST=/home/usuario/Videos/fonte"
        )

    folder = Path(folder_path)

    if not folder.exists():
        return _fail(
            f"Pasta de vídeos: '{folder}' não existe\n"
            f"         → Crie a pasta ou corrija VIDEOS_FOLDER_HOST no .env"
        )

    if not folder.is_dir():
        return _fail(f"Pasta de vídeos: '{folder}' não é um diretório")

    # Conta arquivos de vídeo suportados (incluindo subpastas)
    video_files = [
        f for f in folder.rglob("*")
        if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS
    ]

    if not video_files:
        return _warn(
            f"Pasta de vídeos: '{folder}' existe mas está vazia\n"
            f"         → Adicione vídeos .mp4, .mov ou .avi para usar o pipeline"
        )

    # Agrupa por extensão para informação útil
    by_ext: dict[str, int] = {}
    for f in video_files:
        ext = f.suffix.lower()
        by_ext[ext] = by_ext.get(ext, 0) + 1

    ext_summary = ", ".join(f"{v} {k}" for k, v in sorted(by_ext.items()))
    return _ok(
        f"Pasta de vídeos: '{folder}' — {len(video_files)} vídeo(s)\n"
        f"         Tipos: {ext_summary}"
    )


def main() -> int:
    """Executa todos os health checks e retorna o código de saída."""
    print()
    print("=" * 60)
    print("  YouTube Automation — Verificação de Saúde do Ambiente")
    print("=" * 60)
    print()

    # Cada check retorna True (passou) ou False (falhou/aviso)
    checks = [
        ("Backend FastAPI",       check_backend),
        ("Banco de Dados",        check_database),
        ("Ollama (IA Local)",     check_ollama),
        ("FFmpeg (Processamento)", check_ffmpeg),
        ("Pasta de Vídeos",       check_videos_folder),
    ]

    results = []
    for name, check_fn in checks:
        print(f"{name}:")
        passed = check_fn()
        results.append(passed)
        print()

    # Sumário final
    passed_count = sum(results)
    total = len(results)

    print("-" * 60)
    if all(results):
        print(f"  {GREEN}✓ Todos os {total} checks passaram — ambiente pronto!{RESET}")
        print()
        print("  Para iniciar: make dev  (desenvolvimento)")
        print("                make prod (produção)")
        return 0
    else:
        failed_count = total - passed_count
        print(
            f"  {YELLOW}⚠ {passed_count}/{total} checks passaram "
            f"— {failed_count} item(s) requerem atenção{RESET}"
        )
        print()
        print("  Corrija os itens marcados com ✗ ou ⚠ antes de iniciar.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
