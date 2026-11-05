# YouTube Automation

Sistema de automação para criação e publicação de vídeos no YouTube usando IA local (Ollama), TTS neural (edge-tts) e processamento de vídeo com FFmpeg.

**Stack:** FastAPI · Vue 3 · SQLite · Docker · Ollama

---

## Sumário

- [Pré-requisitos](#pré-requisitos)
- [Início Rápido](#início-rápido)
- [Configuração OAuth do YouTube](#configuração-oauth-do-youtube)
- [Variáveis de Ambiente](#variáveis-de-ambiente)
- [Modo Desenvolvimento](#modo-desenvolvimento)
- [Comandos Disponíveis](#comandos-disponíveis)
- [Verificação de Saúde](#verificação-de-saúde)
- [Arquitetura dos Containers](#arquitetura-dos-containers)
- [Solução de Problemas](#solução-de-problemas)

---

## Pré-requisitos

| Dependência | Versão mínima | Instalação |
|-------------|---------------|------------|
| Docker + Compose plugin | 24+ | [docs.docker.com](https://docs.docker.com/get-docker/) |
| Ollama | Qualquer | [ollama.com](https://ollama.com) |
| Python 3.11+ | 3.11 | Apenas para `make health` e scripts locais |

> **FFmpeg** não precisa estar instalado no host — ele já está dentro do container Docker.

### Instalar Ollama e um modelo

```bash
# Instala o Ollama (Linux/Mac)
curl -fsSL https://ollama.com/install.sh | sh

# Baixa o modelo llama3 (~4.7GB)
ollama pull llama3

# Verifica se está rodando
curl http://localhost:11434/api/tags
```

---

## Início Rápido

### 1. Clone e configure o ambiente

```bash
git clone <url-do-repositorio>
cd youtube-automation

# Cria o .env a partir do exemplo
cp .env.example .env
```

### 2. Edite o `.env` com suas configurações

As configurações mínimas obrigatórias:

```dotenv
# Chave secreta para criptografar tokens OAuth
# Gere com: openssl rand -hex 32
SECRET_KEY=cole-aqui-sua-chave-gerada

# Pasta com seus vídeos fonte no host
# Linux/Mac: /home/usuario/Videos/fonte
# Windows:   C:\Users\Usuario\Videos\fonte
VIDEOS_FOLDER_HOST=./videos

# URL do Ollama (padrão funciona se estiver rodando localmente)
OLLAMA_URL=http://host.docker.internal:11434
```

### 3. Inicie os containers

```bash
# Modo produção (background)
docker compose up -d

# Acompanhe a inicialização
docker compose logs -f
```

Aguarde o backend passar no health check (alguns segundos). Quando os dois serviços estiverem `healthy`, acesse:

- **Interface:** http://localhost
- **API Docs (Swagger):** http://localhost:8000/docs
- **API Docs (ReDoc):** http://localhost:8000/redoc

---

## Configuração OAuth do YouTube

Para habilitar o upload de vídeos, você precisa de credenciais OAuth2 do Google Cloud Console.

### Passo a passo

**1. Acesse o Google Cloud Console**

Vá para [console.cloud.google.com](https://console.cloud.google.com) e crie um projeto (ou use um existente).

**2. Ative a YouTube Data API v3**

- Menu → APIs e Serviços → Biblioteca
- Pesquise "YouTube Data API v3"
- Clique em **Ativar**

**3. Configure a tela de consentimento OAuth**

- Menu → APIs e Serviços → Tela de consentimento OAuth
- Tipo de usuário: **Externo** (para uso pessoal)
- Preencha nome do app, email de suporte
- Em "Escopos", adicione: `https://www.googleapis.com/auth/youtube.upload`
- Em "Usuários de teste", adicione seu email do Google

**4. Crie as credenciais OAuth2**

- Menu → APIs e Serviços → Credenciais
- Criar credenciais → **ID do cliente OAuth 2.0**
- Tipo de aplicativo: **Aplicativo da Web**
- URIs de redirecionamento autorizados:
  ```
  http://localhost:8000/api/accounts/oauth/callback
  ```
- Baixe o arquivo JSON das credenciais

**5. Configure na interface**

- Acesse a aba **Configurações** na interface
- No campo "Credenciais OAuth", faça upload ou informe o path do JSON baixado
- Clique em **Contas** → **Conectar conta** para autorizar

> As credenciais são armazenadas criptografadas no banco de dados local. Nenhum dado é enviado para servidores externos.

---

## Variáveis de Ambiente

Todas as variáveis ficam no arquivo `.env` (criado a partir de `.env.example`).

### Obrigatórias em produção

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `SECRET_KEY` | Chave para criptografia de tokens OAuth. Gere com `openssl rand -hex 32` | `a1b2c3...` |
| `VIDEOS_FOLDER_HOST` | Caminho no host para a pasta de vídeos fonte | `/home/user/Videos` |

### Ollama

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `OLLAMA_URL` | `http://host.docker.internal:11434` | URL do serviço Ollama |
| `OLLAMA_MODEL` | `llama3` | Modelo padrão para geração de texto |

### Servidor

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `BACKEND_PORT` | `8000` | Porta do backend no host |
| `FRONTEND_PORT` | `80` | Porta do frontend no host |
| `ENVIRONMENT` | `production` | `production` ou `development` |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### Processamento de Vídeo

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `TTS_VOICE` | `en-US-JennyNeural` | Voz do edge-tts (ver `.env.example` para lista) |
| `DEFAULT_DIMENSION` | `16:9` | `16:9` (YouTube) ou `9:16` (Shorts) |
| `CLIP_MIN_DURATION` | `3` | Duração mínima dos clipes anti-plágio (segundos) |
| `CLIP_MAX_DURATION` | `6` | Duração máxima dos clipes anti-plágio (segundos) |
| `MAX_WORKERS` | `2` | Workers para processamento paralelo |

---

## Modo Desenvolvimento

O modo de desenvolvimento habilita hot reload automático para backend e frontend.

```bash
# Inicia com hot reload
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Ou com Make (Linux/Mac)
make dev
```

**URLs em modo dev:**
- Frontend (Vite HMR): http://localhost:5173
- Backend (com reload): http://localhost:8000
- API Docs: http://localhost:8000/docs

**Comportamentos em dev:**
- Qualquer mudança em arquivos `.py` reinicia o uvicorn automaticamente
- Qualquer mudança em `.vue` ou `.ts` atualiza o browser instantaneamente
- Logs em nível `DEBUG` (mais verboso)
- CORS liberado para `localhost:5173`
- Sem restart automático de containers (crashes ficam visíveis)

### Executar testes em desenvolvimento

```bash
# Todos os testes
make test

# Apenas backend (pytest com cobertura)
make test-backend

# Apenas frontend (vitest)
make test-frontend

# Lint (verifica formatação e estilo)
make lint
```

---

## Comandos Disponíveis

### Com Make

> **Windows:** instale o GNU make com `choco install make` (Chocolatey) ou use os comandos Docker diretamente.

```bash
make setup          # Cria .env e diretórios necessários
make dev            # Desenvolvimento com hot reload
make prod           # Produção em background
make stop           # Para todos os containers
make test           # Todos os testes
make test-backend   # Testes do backend
make test-frontend  # Testes do frontend
make lint           # Todos os linters
make build          # Build das imagens Docker
make clean          # Remove containers e imagens
make clean-volumes  # Remove containers, imagens e DADOS (irreversível)
make logs           # Logs em tempo real
make ps             # Status dos containers
make health         # Verificação de saúde do ambiente
make shell-backend  # Shell no container backend
make shell-frontend # Shell no container frontend
```

### Com Docker Compose diretamente

```bash
# Produção
docker compose up -d
docker compose down
docker compose logs -f
docker compose ps

# Desenvolvimento
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm backend pytest tests/

# Rebuild sem cache
docker compose build --no-cache

# Acessar shell do container
docker compose exec backend sh
docker compose exec frontend sh
```

---

## Verificação de Saúde

O script `scripts/healthcheck.py` verifica todos os componentes do ambiente:

```bash
python scripts/healthcheck.py
```

**Verifica:**
- Backend respondendo em `/health`
- Diretório do banco de dados acessível
- Ollama acessível com modelos instalados
- FFmpeg instalado
- Pasta de vídeos configurada com arquivos suportados

**Exemplo de saída:**

```
============================================================
  YouTube Automation — Verificação de Saúde do Ambiente
============================================================

Backend FastAPI:
  ✓ Backend: HTTP 200 — status=ok (http://localhost:8000/health)

Banco de Dados:
  ✓ Banco de dados: './data/youtube_automation.db' (12.5 KB)

Ollama (IA Local):
  ✓ Ollama: 2 modelo(s) em http://localhost:11434
         Modelos: llama3:latest, llama3.1:8b

FFmpeg (Processamento):
  ✓ FFmpeg: versão 6.1.1

Pasta de Vídeos:
  ✓ Pasta de vídeos: './videos' — 15 vídeo(s)
         Tipos: 12 .mp4, 3 .mov

------------------------------------------------------------
  ✓ Todos os 5 checks passaram — ambiente pronto!
```

---

## Arquitetura dos Containers

```
┌─────────────────────────────────────────────────┐
│                   Host Machine                   │
│                                                  │
│  ┌─────────────┐   ┌─────────────────────────┐  │
│  │   Ollama    │   │  YouTube Automation     │  │
│  │  :11434     │   │  Docker Network         │  │
│  └──────┬──────┘   │                         │  │
│         │          │  ┌──────────────────┐   │  │
│  :80    │     ┌────┼──│   frontend       │   │  │
│  ┌──────┴──┐  │    │  │   nginx :80      │   │  │
│  │ Browser │──┘    │  └────────┬─────────┘   │  │
│  └─────────┘       │           │ proxy /api  │  │
│                    │  ┌────────▼─────────┐   │  │
│  ./videos ─────────┼──│   backend        │   │  │
│  db-data  ─────────┼──│   fastapi :8000  │   │  │
│  credentials ──────┼──│   + ffmpeg       │   │  │
│                    │  └──────────────────┘   │  │
│                    └─────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

**Comunicação:**
- Usuário → Frontend (Nginx, porta 80)
- Nginx → Backend via proxy reverso (`/api/*` → `backend:8000`)
- Nginx → Backend SSE sem buffer (`/api/sse/*` → `backend:8000`)
- Backend → Ollama via `host.docker.internal:11434`
- Backend → edge-tts via HTTPS (internet)

**Volumes persistentes:**
- `youtube-automation-db` — banco SQLite
- `youtube-automation-credentials` — tokens OAuth criptografados
- `youtube-automation-output` — vídeos processados
- `${VIDEOS_FOLDER_HOST}` — vídeos fonte (bind mount, somente leitura em prod)

---

## Solução de Problemas

### Ollama não acessível dentro do container

**Sintoma:** `Connection refused` ou `Name resolution failed` para `host.docker.internal:11434`

**Causa:** No Linux, `host.docker.internal` não existe por padrão (diferente de macOS/Windows).

**Solução:** O `docker-compose.yml` já configura `extra_hosts: - "host.docker.internal:host-gateway"` para resolver isso. Verifique se o Ollama está iniciado:

```bash
# Verificar se Ollama está rodando
curl http://localhost:11434/api/tags

# Iniciar Ollama se necessário
ollama serve
```

---

### Container do backend não inicia (health check falhando)

**Verificar logs:**

```bash
docker compose logs backend
```

**Causas comuns:**
1. `SECRET_KEY` não definida no `.env` — gere com `openssl rand -hex 32`
2. Erro de permissão em `/app/data` — verifique permissões do volume
3. Porta 8000 já em uso — mude `BACKEND_PORT` no `.env`

---

### Frontend mostra erro 502 Bad Gateway

**Causa:** O backend não está `healthy` ainda quando o Nginx tenta fazer o proxy.

**Solução:** Aguarde o backend inicializar completamente (até 30s) e tente novamente. Para verificar o status:

```bash
docker compose ps
# Aguarde o status "healthy" para o container backend
```

---

### Vídeos não aparecem na interface

**Verificar:**
1. `VIDEOS_FOLDER_HOST` no `.env` aponta para a pasta correta
2. A pasta existe e tem arquivos `.mp4`, `.mov` ou `.avi`
3. O volume está montado corretamente:

```bash
# Verifica se os vídeos estão acessíveis dentro do container
docker compose exec backend ls -la /app/videos
```

---

### Erro de permissão ao processar vídeos

**Causa:** O container roda como usuário não-root (uid 1001). Se o diretório de output tiver permissões restritas, o processamento falha.

**Solução:**

```bash
# Ajusta permissões do volume de output
docker volume inspect youtube-automation-output
# Ou recria o volume
docker compose down
docker volume rm youtube-automation-output
docker compose up -d
```

---

### edge-tts falha ao gerar áudio

**Causa:** `edge-tts` requer conexão com internet (usa a API da Microsoft).

**Verificar:**
1. Container tem acesso à internet: `docker compose exec backend curl -s https://example.com`
2. Voz configurada existe: verifique `TTS_VOICE` no `.env`

---

### Atualizar dependências Python

```bash
# Rebuild completo do backend sem cache
docker compose build --no-cache backend
docker compose up -d backend
```

---

### Backup dos dados

Os dados importantes ficam em volumes Docker nomeados:

```bash
# Backup do banco de dados
docker run --rm \
  -v youtube-automation-db:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/backup-db-$(date +%Y%m%d).tar.gz /data

# Backup das credenciais OAuth
docker run --rm \
  -v youtube-automation-credentials:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/backup-credentials-$(date +%Y%m%d).tar.gz /data
```

---

## Licença

MIT — veja `LICENSE` para detalhes.
