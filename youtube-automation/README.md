# YouTube Automation

Aplicação para automatizar a criação e, futuramente, a publicação de vídeos no
YouTube usando IA local, síntese de voz e processamento de vídeo.

## Status atual

O backend executável está disponível e pode ser iniciado com Docker:

- FastAPI + Uvicorn;
- SQLite com persistência em volume Docker;
- migrations com Alembic;
- configurações via API;
- Ollama para geração de texto;
- FFmpeg dentro da imagem;
- testes, lint e health check.

O frontend Vue possui a base Creator Studio executável, com Dashboard,
Configurações, navegação, integração inicial com o backend e build Docker. As
integrações de contas YouTube, jobs, calendário, pipeline, OAuth, upload e SSE
continuam sendo implementadas nas próximas fases.

## Sumário

- [Arquitetura](#arquitetura)
- [Pré-requisitos](#pré-requisitos)
- [Instalação rápida do backend](#instalação-rápida-do-backend)
- [Instalação no Windows](#instalação-no-windows)
- [Instalação no Linux ou macOS](#instalação-no-linux-ou-macos)
- [Configuração do arquivo `.env`](#configuração-do-arquivo-env)
- [Configuração do Ollama](#configuração-do-ollama)
- [Inicialização e operação](#inicialização-e-operação)
- [Configuração OAuth do YouTube](#configuração-oauth-do-youtube)
- [Desenvolvimento](#desenvolvimento)
- [Testes e qualidade](#testes-e-qualidade)
- [Persistência e backup](#persistência-e-backup)
- [Solução de problemas](#solução-de-problemas)
- [Estrutura do projeto](#estrutura-do-projeto)

## Arquitetura

```text
Seu computador
├── Ollama :11434
└── Docker
    └── backend :8000
        ├── FastAPI
        ├── SQLite + Alembic
        └── FFmpeg
```

O backend acessa o Ollama no host por `host.docker.internal`. O banco, as
credenciais OAuth e os arquivos gerados ficam em volumes Docker persistentes.
A pasta de vídeos de entrada é montada no container como `/app/videos`.

## Pré-requisitos

### Obrigatórios

| Dependência | Versão recomendada | Observação |
|---|---:|---|
| Docker Desktop (Windows/macOS) ou Docker Engine (Linux) | 24+ | Deve estar iniciado |
| Docker Compose plugin | v2+ | Incluído nas versões atuais do Docker Desktop |
| Git | versão atual | Para clonar o projeto |
| Ollama | versão atual | Necessário para recursos de IA |

Python 3.11 é usado dentro do Docker. Não é necessário instalar Python no host
para executar a aplicação. Python no host só é necessário para executar o
script opcional de health check.

FFmpeg também não precisa ser instalado no host: ele já está na imagem Docker
do backend.

### Conferir o Docker

```bash
docker --version
docker compose version
docker info
```

No Windows, abra o Docker Desktop e aguarde o status **Engine running** antes
de executar os comandos do projeto.

## Instalação rápida do backend

Os comandos abaixo funcionam em Linux, macOS, Git Bash e WSL.

### 1. Clonar o repositório

```bash
git clone <URL_DO_REPOSITORIO>
cd <PASTA_DO_REPOSITORIO>/youtube-automation
```

### 2. Criar o arquivo de ambiente

```bash
cp .env.example .env
mkdir -p videos
```

No Windows PowerShell, use:

```powershell
Copy-Item .env.example .env
New-Item -ItemType Directory -Force videos
```

### 3. Gerar uma chave secreta

Linux/macOS/Git Bash:

```bash
openssl rand -hex 32
```

PowerShell:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Copie o resultado para `SECRET_KEY` no arquivo `.env`. Nunca publique essa
chave e nunca use o valor de exemplo em produção.

### 4. Configurar a pasta de vídeos

Para usar uma pasta dentro do projeto:

```dotenv
VIDEOS_FOLDER_HOST=./videos
```

No Windows, também é possível usar um caminho absoluto. Use aspas se o caminho
possuir espaços:

```dotenv
VIDEOS_FOLDER_HOST=C:\Users\SeuUsuario\Videos\youtube-source
```

Ou, no formato aceito pelo Docker Desktop:

```dotenv
VIDEOS_FOLDER_HOST=C:/Users/SeuUsuario/Videos/youtube-source
```

### 5. Iniciar somente o backend

```bash
docker compose up -d --build backend
```

### 6. Verificar a instalação

```bash
docker compose ps
curl http://localhost:8000/health
```

Resposta esperada:

```json
{"status":"ok"}
```

Também é possível abrir a documentação interativa em
<http://localhost:8000/docs> ou a documentação ReDoc em
<http://localhost:8000/redoc>.

## Instalação no Windows

### Docker Desktop

1. Instale o Docker Desktop pelo site oficial:
   <https://www.docker.com/products/docker-desktop/>
2. Inicie o Docker Desktop.
3. Confirme no PowerShell:

```powershell
docker --version
docker compose version
docker info
```

### Clonar e configurar

No PowerShell:

```powershell
git clone <URL_DO_REPOSITORIO>
Set-Location .\youtube-automation
Copy-Item .env.example .env
New-Item -ItemType Directory -Force .\videos
```

Edite o arquivo:

```powershell
notepad .env
```

Defina pelo menos:

```dotenv
SECRET_KEY=COLE_A_CHAVE_GERADA_AQUI
OLLAMA_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3
VIDEOS_FOLDER_HOST=./videos
```

Inicie e valide:

```powershell
docker compose up -d --build backend
docker compose ps
Invoke-RestMethod http://localhost:8000/health
```

Para acompanhar os logs:

```powershell
docker compose logs -f backend
```

Se o Docker Desktop bloquear o acesso a uma pasta absoluta, abra **Settings >
Resources > File Sharing** e permita a unidade ou pasta usada no volume.

## Instalação no Linux ou macOS

Instale Docker conforme a documentação oficial:

- Linux: <https://docs.docker.com/engine/install/>
- macOS: <https://docs.docker.com/desktop/install/mac-install/>

Depois execute:

```bash
git clone <URL_DO_REPOSITORIO>
cd youtube-automation
cp .env.example .env
mkdir -p videos
openssl rand -hex 32
# Edite .env e cole a chave gerada em SECRET_KEY
docker compose up -d --build backend
curl http://localhost:8000/health
```

Em Linux, o Compose já adiciona `host.docker.internal` usando
`host-gateway`, permitindo que o container alcance o Ollama no host.

## Configuração do arquivo `.env`

O arquivo `.env.example` contém todos os parâmetros. Os mais importantes são:

| Variável | Obrigatória | Padrão | Finalidade |
|---|---|---|---|
| `SECRET_KEY` | Sim em produção | Nenhum seguro | Criptografia e proteção administrativa |
| `OLLAMA_URL` | Sim para IA | `http://host.docker.internal:11434` | Endereço do Ollama |
| `OLLAMA_MODEL` | Não | `llama3` | Modelo usado pela aplicação |
| `VIDEOS_FOLDER_HOST` | Recomendado | `./videos` | Pasta de vídeos no host |
| `BACKEND_PORT` | Não | `8000` | Porta exposta pelo backend |
| `DATABASE_PATH` | Não | `/app/data/youtube_automation.db` | Arquivo SQLite no container |
| `LOG_LEVEL` | Não | `INFO` | Nível dos logs |
| `ENVIRONMENT` | Não | `production` | Ambiente da aplicação |
| `CORS_ORIGINS` | Não | `http://localhost,http://localhost:80` | Origens permitidas, separadas por vírgula |
| `TTS_VOICE` | Não | `en-US-JennyNeural` | Voz de síntese |
| `DEFAULT_DIMENSION` | Não | `16:9` | Formato normal ou `9:16` para Shorts |
| `CLIP_MIN_DURATION` | Não | `3` | Duração mínima dos clipes |
| `CLIP_MAX_DURATION` | Não | `6` | Duração máxima dos clipes |
| `MAX_WORKERS` | Não | `2` | Workers de processamento |

Não coloque credenciais, tokens ou chaves diretamente no `docker-compose.yml`.
O arquivo `.env` já está no `.gitignore` e não deve ser commitado.

## Configuração do Ollama

Instale o Ollama em <https://ollama.com/download>.

Depois confirme que o serviço está ativo:

```bash
ollama serve
```

Em outro terminal, baixe o modelo configurado:

```bash
ollama pull llama3
ollama list
curl http://localhost:11434/api/tags
```

No Windows, o aplicativo Ollama normalmente inicia o serviço automaticamente.
Se necessário, execute os mesmos comandos no PowerShell.

Se você usar outro modelo, altere:

```dotenv
OLLAMA_MODEL=llama3.1:8b
```

e baixe-o antes de iniciar o processamento:

```bash
ollama pull llama3.1:8b
```

## Inicialização e operação

### Produção

```bash
docker compose up -d --build backend
docker compose ps
docker compose logs -f backend
```

Parar o backend sem apagar volumes:

```bash
docker compose down
```

Reiniciar:

```bash
docker compose restart backend
```

Atualizar depois de baixar alterações:

```bash
git pull
docker compose up -d --build backend
```

### Endpoints disponíveis

| Endpoint | Função |
|---|---|
| `GET /health` | Health check básico |
| `GET /docs` | Swagger UI |
| `GET /redoc` | ReDoc |
| `GET /api/settings` | Consulta configurações não sensíveis |
| `PUT /api/settings` | Atualiza configurações administrativas |
| `POST /api/settings/validate-videos-folder` | Valida a pasta de vídeos |

As alterações administrativas exigem o header `X-Admin-Key` com o valor de
`SECRET_KEY`. A API não retorna a chave secreta nem credenciais OAuth.

Exemplo:

```bash
curl -X PUT http://localhost:8000/api/settings \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: SUA_SECRET_KEY" \
  -d '{"default_dimension":"9:16"}'
```

## Configuração OAuth do YouTube

Esta etapa é necessária somente para publicar no YouTube.

1. Acesse <https://console.cloud.google.com/>.
2. Crie ou selecione um projeto.
3. Ative **YouTube Data API v3** em **APIs e serviços > Biblioteca**.
4. Configure a tela de consentimento OAuth.
5. Adicione seu e-mail como usuário de teste quando o aplicativo estiver em
   modo de teste.
6. Crie uma credencial OAuth 2.0.
7. Baixe o JSON das credenciais.
8. Não faça commit desse JSON.
9. Configure o arquivo pela funcionalidade de contas quando ela estiver
   disponível na interface.

Os tokens devem permanecer no volume Docker `youtube-automation-credentials`.
Se o volume for removido, será necessário autorizar as contas novamente.

## Desenvolvimento

O Compose de desenvolvimento monta o código do backend e habilita reload:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build backend
```

O frontend possui os arquivos-fonte necessários para executar o Vite. O comando
de desenvolvimento completo é:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Backend em desenvolvimento:

- API: <http://localhost:8000>
- Swagger: <http://localhost:8000/docs>
- reload automático ao alterar arquivos Python;
- volumes de desenvolvimento separados dos volumes de produção.

## Testes e qualidade

### Testes no container de desenvolvimento

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm backend \
  pytest tests/ -v
```

Com cobertura:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm backend \
  pytest tests/ -v --cov=app --cov-report=term-missing
```

Lint e formatação:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm backend \
  sh -c "ruff check . && black --check --diff ."
```

### Usando Make

GNU Make é opcional. Os comandos Docker acima funcionam sem Make.

```bash
make setup
make dev
make prod
make stop
make test-backend
make lint-backend
make build-backend
make logs
make ps
make health
```

No Windows, instale GNU Make por Chocolatey:

```powershell
choco install make
```

ou por winget:

```powershell
winget install GnuWin32.Make
```

## Health check completo

Com o backend em execução:

```bash
python scripts/healthcheck.py
```

O script verifica backend, banco, Ollama, FFmpeg e pasta de vídeos. Como o
FFmpeg está dentro do container, o resultado do script executado no host pode
indicar que o FFmpeg não foi encontrado mesmo com o backend funcionando. Nesse
caso, execute verificações dentro do container:

```bash
docker compose exec backend ffmpeg -version
docker compose exec backend ls -la /app/videos
```

## Persistência e backup

Volumes de produção:

| Volume | Conteúdo |
|---|---|
| `youtube-automation-db` | Banco SQLite |
| `youtube-automation-credentials` | Credenciais/tokens OAuth |
| `youtube-automation-output` | Vídeos processados |

Listar volumes:

```bash
docker volume ls | findstr youtube-automation
```

No Linux/macOS/Git Bash, fazer backup:

```bash
mkdir -p backups
docker run --rm \
  -v youtube-automation-db:/data:ro \
  -v "$(pwd)/backups:/backup" \
  alpine tar czf /backup/db-$(date +%Y%m%d-%H%M%S).tar.gz /data

docker run --rm \
  -v youtube-automation-credentials:/data:ro \
  -v "$(pwd)/backups:/backup" \
  alpine tar czf /backup/credentials-$(date +%Y%m%d-%H%M%S).tar.gz /data
```

No PowerShell:

```powershell
New-Item -ItemType Directory -Force .\backups
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
docker run --rm -v youtube-automation-db:/data:ro -v "${PWD}\backups:/backup" `
  alpine tar czf "/backup/db-$stamp.tar.gz" /data
docker run --rm -v youtube-automation-credentials:/data:ro `
  -v "${PWD}\backups:/backup" alpine tar czf "/backup/credentials-$stamp.tar.gz" /data
```

> **Atenção:** `docker compose down -v`, `make clean-volumes` e a remoção
> manual dos volumes apagam dados. Faça backup antes.

## Solução de problemas

### `docker compose up` não inicia

```bash
docker info
docker compose config
docker compose ps
docker compose logs backend
```

Confirme que o Docker Desktop está aberto, que o `.env` existe e que a porta
8000 não está sendo usada.

### Erro de `SECRET_KEY`

Gere uma chave nova e substitua o valor no `.env`:

```bash
openssl rand -hex 32
```

Depois recrie o container:

```bash
docker compose up -d --build backend
```

### Porta 8000 ocupada

No `.env`:

```dotenv
BACKEND_PORT=8001
```

Depois acesse `http://localhost:8001/health`.

### Ollama não acessível

```bash
curl http://localhost:11434/api/tags
docker compose exec backend wget -qO- http://host.docker.internal:11434/api/tags
```

Se o primeiro comando falhar, inicie o Ollama. Se o segundo falhar, confira
firewall, URL e se o Docker está em execução.

### Pasta de vídeos vazia ou inexistente

Confira o valor de `VIDEOS_FOLDER_HOST` e teste o mount:

```bash
docker compose exec backend ls -la /app/videos
```

As extensões reconhecidas pelo health check são `.mp4`, `.mov`, `.avi`, `.mkv`
e `.webm`.

### Erro de permissão no Windows

Use uma pasta compartilhada pelo Docker Desktop e autorize o acesso em
**Settings > Resources > File Sharing**. Para um primeiro teste, mantenha:

```dotenv
VIDEOS_FOLDER_HOST=./videos
```

### Migration ou banco legado

As migrations são executadas automaticamente no startup. O backend também
reconhece volumes antigos que possuem tabelas sem uma versão Alembic e grava o
baseline compatível. Não remova o volume do banco sem fazer backup.

### O frontend não compila

Confirme que `frontend/package-lock.json` está presente e que a instalação foi
feita com `npm ci` dentro do container. Para reconstruir sem cache:

```bash
docker compose build --no-cache frontend
docker compose up -d frontend
docker compose logs frontend
```

## Estrutura do projeto

```text
youtube-automation/
├── backend/
│   ├── app/
│   │   ├── api/              # Rotas e dependências FastAPI
│   │   ├── core/             # Configurações e exceções
│   │   ├── db/               # Engine e sessões SQLAlchemy
│   │   ├── models/           # Modelos do banco
│   │   └── schemas/          # Schemas Pydantic
│   ├── alembic/              # Migrations
│   ├── tests/                # Testes automatizados
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                 # Vue 3 + Vite + shell Creator Studio
├── docs/                     # Especificações e plano de testes
├── scripts/                  # Scripts auxiliares
├── .env.example
├── docker-compose.yml
├── docker-compose.dev.yml
└── Makefile
```

## Segurança

- Não versione `.env`, tokens OAuth, arquivos JSON de credenciais ou backups.
- Use uma `SECRET_KEY` longa e aleatória.
- Restrinja `CORS_ORIGINS` em ambientes expostos.
- Não exponha a porta do backend diretamente à internet sem autenticação e
  proxy reverso.
- Faça backup dos volumes em local seguro e com acesso restrito.
- Troque credenciais imediatamente se elas forem expostas.

## Licença

Consulte o arquivo `LICENSE` quando ele estiver disponível no repositório.
