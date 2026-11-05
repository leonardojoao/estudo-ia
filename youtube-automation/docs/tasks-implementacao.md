# Tasks de Implementação — YouTube Automation

> Documento gerado pelo Arquiteto. Cobre 100% dos arquivos da estrutura definida.
> **67 tasks** organizadas em 6 fases. Cada task = 0.5 a 1 dia de trabalho.
> **NÃO é para implementar de uma vez** — siga a ordem das fases e dependências.

---

## Legenda

- **Módulo:** `backend` | `frontend` | `infra`
- **Produz para:** qual task consome o que esta cria
- **Depende de:** tasks que devem estar prontas antes desta

---

## FASE 1 — Fundação

> Setup do projeto, banco de dados, infraestrutura base de código.
> Nada das fases seguintes pode iniciar sem esta fase completa.

---

### TASK-001 — Criar requirements.txt com todas as dependências pinadas

**Módulo:** backend
**Arquivo(s):** `backend/requirements.txt`
**US:** US-001
**Depende de:** —
**Produz para:** todas as tasks de backend

#### O que criar
Arquivo `requirements.txt` com versões exatas (`==`) de todas as dependências:

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
sqlalchemy==2.0.30
alembic==1.13.1
pydantic-settings==2.2.1
sse-starlette==2.1.0
ollama==0.2.1
edge-tts==6.1.9
ffmpeg-python==0.2.0
google-api-python-client==2.130.0
google-auth-oauthlib==1.2.0
google-auth-httplib2==0.2.0
apscheduler==3.10.4
python-multipart==0.0.9
cryptography==42.0.7
aiofiles==23.2.1
mutagen==1.47.0
python-dotenv==1.0.1
```

#### Critérios de conclusão
- [ ] `pip install -r requirements.txt` executa sem erros em ambiente limpo
- [ ] Todas as versões são exatas (`==`), sem ranges (`>=`, `~=`)
- [ ] `pip check` não reporta conflitos de dependências

#### Pontos de atenção
- `mutagen` é necessária para ler metadados de áudio (duração real do MP3)
- `aiofiles` é necessária para leitura assíncrona de arquivos no pipeline
- Verificar compatibilidade entre `sqlalchemy 2.0` e `alembic 1.13`

---

### TASK-002 — Criar app/core/config.py (Pydantic Settings)

**Módulo:** backend
**Arquivo(s):** `backend/app/core/config.py`
**US:** US-001
**Depende de:** TASK-001
**Produz para:** TASK-013, TASK-004, todas as rotas e serviços

#### O que criar
Classe `Settings` usando `pydantic-settings` que lê do `.env` e variáveis de ambiente:

```python
class Settings(BaseSettings):
    # Banco
    database_path: str = "/app/data/youtube_automation.db"
    # Ollama
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    # Vídeo
    videos_folder: str = ""
    clip_min_duration: int = 3
    clip_max_duration: int = 6
    default_dimension: str = "16:9"
    # TTS
    tts_voice: str = "en-US-JennyNeural"
    # YouTube OAuth
    oauth_credentials_path: str = "/app/credentials"
    # Segurança
    secret_key: str
    # Servidor
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost"]
    log_level: str = "INFO"
    environment: str = "production"
    max_workers: int = 2

    model_config = SettingsConfig(env_file=".env", case_sensitive=False)
```

Função singleton `get_settings()` com `@lru_cache`.

#### Critérios de conclusão
- [ ] `from app.core.config import get_settings; s = get_settings()` funciona sem `.env`
- [ ] Todas as variáveis do `.env.example` têm campo correspondente em `Settings`
- [ ] `secret_key` sem default — levanta `ValidationError` se ausente
- [ ] Validação: `secret_key != "TROQUE-ESTA-CHAVE..."` em `environment == "production"`

#### Pontos de atenção
- `get_settings()` usa `@lru_cache` — em testes, usar `get_settings.cache_clear()` para resetar
- Não usar `os.getenv()` diretamente em nenhum outro módulo — centralizar aqui

---

### TASK-003 — Criar app/core/exceptions.py (exceções + handlers)

**Módulo:** backend
**Arquivo(s):** `backend/app/core/exceptions.py`
**US:** US-001
**Depende de:** —
**Produz para:** TASK-013, todos os serviços

#### O que criar
Hierarquia de exceções customizadas e função `register_exception_handlers(app)`:

```python
class AppError(Exception): ...
class NotFoundError(AppError): ...
class ValidationError(AppError): ...
class OllamaUnavailableError(AppError): ...
class FFmpegError(AppError): ...
class YouTubeAPIError(AppError): ...
class OAuthError(AppError): ...
class InsufficientVideosError(AppError): ...
class AntiPlagiarismError(AppError): ...
```

Handlers registram no FastAPI e retornam JSON padronizado:
```json
{ "error": "CÓDIGO_ERRO", "message": "Descrição legível", "details": {} }
```

#### Critérios de conclusão
- [ ] Todas as exceções herdam de `AppError`
- [ ] Handler global para `AppError` retorna HTTP 400/404/500 conforme o tipo
- [ ] Handler para `RequestValidationError` do FastAPI retorna HTTP 422 formatado
- [ ] Handler para `Exception` genérica retorna HTTP 500 sem expor stack trace em produção

---

### TASK-004 — Criar app/db/database.py (engine SQLite + Session)

**Módulo:** backend
**Arquivo(s):** `backend/app/db/database.py`
**US:** US-002
**Depende de:** TASK-002
**Produz para:** TASK-005, TASK-006, TASK-007, TASK-008, TASK-012

#### O que criar
- `engine` SQLite com `connect_args={"check_same_thread": False}`
- `SessionLocal` com `autocommit=False, autoflush=False`
- `Base = declarative_base()`
- Context manager `get_db()` para injeção de dependência no FastAPI
- Função `create_tables()` chamada no lifespan da aplicação

#### Critérios de conclusão
- [ ] `engine` aponta para o path de `Settings.database_path`
- [ ] `get_db()` fecha a sessão no finally (sem leak de conexão)
- [ ] WAL mode habilitado: `engine.execute("PRAGMA journal_mode=WAL")` no create_tables
- [ ] Tabela criada automaticamente se banco não existir

---

### TASK-005 — Criar app/models/account.py (SQLAlchemy)

**Módulo:** backend
**Arquivo(s):** `backend/app/models/account.py`
**US:** US-007
**Depende de:** TASK-004
**Produz para:** TASK-008, TASK-009, TASK-028, TASK-031

#### O que criar
Model `YouTubeAccount` com:
- `id`, `name`, `channel_id` (UNIQUE), `email`, `avatar_url`
- `credentials` (TEXT, JSON criptografado com Fernet)
- `is_active` (BOOLEAN DEFAULT 1)
- `created_at`, `updated_at` (DATETIME com trigger de update)

#### Critérios de conclusão
- [ ] `__tablename__ = "youtube_accounts"`
- [ ] `channel_id` tem índice único
- [ ] `updated_at` atualizado automaticamente via `onupdate=func.now()`
- [ ] `__repr__` implementado para debug

---

### TASK-006 — Criar app/models/job.py e job_step.py

**Módulo:** backend
**Arquivo(s):** `backend/app/models/job.py`, `backend/app/models/job_step.py`
**US:** US-031
**Depende de:** TASK-004
**Produz para:** TASK-008, TASK-009, TASK-010, TASK-034, TASK-038, TASK-040

#### O que criar

**ProcessingJob:**
- `id`, `name`, `status` (`pending|running|completed|error|cancelled`)
- `current_step`, `progress` (0-100), `config` (JSON TEXT)
- `output_video`, `youtube_urls` (JSON TEXT), `error_message`
- `scheduled_at`, `started_at`, `completed_at`, `created_at`
- Relationship `accounts` (M2M via `job_accounts`)
- Relationship `steps` (1:N com `JobStep`)

**JobStep:**
- `id`, `job_id` (FK), `step_name`, `status`
- `input` (JSON TEXT), `output` (JSON TEXT), `log` (TEXT)
- `duration_ms`, `started_at`, `completed_at`

**Tabela de associação `job_accounts`:**
- `job_id` (FK), `account_id` (FK), PK composta

#### Critérios de conclusão
- [ ] Relationships SQLAlchemy configurados com lazy loading correto
- [ ] `status` com validação via `CheckConstraint` ou Enum
- [ ] Indexes em `job_id` nas tabelas filhas

---

### TASK-007 — Criar app/models/settings.py

**Módulo:** backend
**Arquivo(s):** `backend/app/models/settings.py`
**US:** US-004, US-005, US-006
**Depende de:** TASK-004
**Produz para:** TASK-008, TASK-014

#### O que criar
Model `SystemSetting` (key-value store):
- `key` (TEXT PRIMARY KEY)
- `value` (TEXT NOT NULL)
- `updated_at` (DATETIME)

Método de classe `get(db, key, default=None)` e `set(db, key, value)`.

#### Critérios de conclusão
- [ ] `get` e `set` são métodos de classe que aceitam a sessão como parâmetro
- [ ] `set` faz upsert (INSERT OR REPLACE)
- [ ] `updated_at` atualizado no `set`

---

### TASK-008 — Configurar Alembic e criar migration inicial

**Módulo:** backend
**Arquivo(s):** `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/001_initial.py`
**US:** US-002
**Depende de:** TASK-004, TASK-005, TASK-006, TASK-007
**Produz para:** TASK-013 (executa migration no lifespan)

#### O que criar
1. `alembic init alembic` — inicializar Alembic no diretório backend
2. Configurar `alembic/env.py` para usar `Base.metadata` e `DATABASE_PATH` do settings
3. Criar migration `001_initial_schema.py` com:
   - `CREATE TABLE youtube_accounts`
   - `CREATE TABLE processing_jobs`
   - `CREATE TABLE job_accounts`
   - `CREATE TABLE job_steps`
   - `CREATE TABLE system_settings`
   - INSERT dos valores padrão em `system_settings`
4. `downgrade()` com `DROP TABLE` na ordem correta (FKs primeiro)

#### Critérios de conclusão
- [ ] `alembic upgrade head` cria todas as tabelas sem erro
- [ ] `alembic downgrade base` reverte sem erro
- [ ] `alembic current` mostra a revisão correta após upgrade
- [ ] `alembic history` exibe a migration inicial

#### Pontos de atenção
- SQLite não suporta `ALTER TABLE` com FK — downgrade deve fazer `DROP TABLE` completo
- Configurar `render_as_batch=True` no env.py para suporte a migrações futuras no SQLite

---

### TASK-009 — Criar todos os Pydantic schemas

**Módulo:** backend
**Arquivo(s):** `backend/app/schemas/account.py`, `backend/app/schemas/job.py`, `backend/app/schemas/settings.py`
**US:** US-001
**Depende de:** TASK-005, TASK-006, TASK-007
**Produz para:** todas as rotas API

#### O que criar

**schemas/account.py:**
- `AccountCreate`, `AccountResponse` (sem `credentials`), `AccountStatus`

**schemas/job.py:**
- `JobCreate` (config completa), `JobResponse`, `JobListResponse`
- `JobStepResponse`, `StepExecuteRequest`
- `JobConfig` (sub-schema com toda a configuração de um job)

**schemas/settings.py:**
- `SettingsResponse` (key-value dict), `SettingsUpdate`
- `OllamaModel`, `TTSVoice`

#### Critérios de conclusão
- [ ] Nenhum schema expõe `credentials` ou `secret_key`
- [ ] `JobConfig` valida todos os campos obrigatórios
- [ ] `model_config = ConfigDict(from_attributes=True)` nos schemas que mapeiam models

---

### TASK-010 — Criar app/api/deps.py

**Módulo:** backend
**Arquivo(s):** `backend/app/api/deps.py`
**US:** US-001
**Depende de:** TASK-004, TASK-002
**Produz para:** todas as rotas API

#### O que criar
```python
def get_db() -> Generator[Session, None, None]: ...
def get_settings() -> Settings: ...
```

Tipos anotados para uso com `Depends()` no FastAPI.

#### Critérios de conclusão
- [ ] `get_db` é um generator com `try/finally` garantindo `db.close()`
- [ ] `get_settings` retorna o singleton de TASK-002

---

### TASK-011 — Criar main.py (FastAPI app factory + /health)

**Módulo:** backend
**Arquivo(s):** `backend/main.py`
**US:** US-001
**Depende de:** TASK-002, TASK-003, TASK-004, TASK-008, TASK-010
**Produz para:** todos os endpoints

#### O que criar
```python
@asynccontextmanager
async def lifespan(app):
    # startup: run alembic upgrade, init scheduler, check FFmpeg
    yield
    # shutdown: stop scheduler

app = FastAPI(title="YouTube Automation", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, ...)
register_exception_handlers(app)
app.include_router(settings_router, prefix="/api")
app.include_router(accounts_router, prefix="/api")
app.include_router(jobs_router, prefix="/api")
app.include_router(ollama_router, prefix="/api")
app.include_router(sse_router, prefix="/api")

@app.get("/health")
async def health(): return {"status": "ok", "version": "1.0.0"}
```

#### Critérios de conclusão
- [ ] `GET /health` retorna `200 {"status": "ok"}`
- [ ] CORS aceita origens de `settings.cors_origins`
- [ ] Lifespan executa `alembic upgrade head` na inicialização
- [ ] Lifespan verifica se FFmpeg está disponível e loga warning se não estiver
- [ ] Aplicação inicia sem `.env` (usando defaults, exceto `secret_key`)

---

### TASK-012 — Criar api/routes/settings.py

**Módulo:** backend
**Arquivo(s):** `backend/app/api/routes/settings.py`
**US:** US-004, US-005, US-006
**Depende de:** TASK-007, TASK-009, TASK-010
**Produz para:** TASK-049 (frontend consome)

#### O que criar
```
GET  /api/settings      → retorna todas as configurações como dict
PUT  /api/settings      → atualiza uma ou mais chaves (upsert)
POST /api/settings/validate-videos-folder → valida pasta e conta vídeos
```

#### Critérios de conclusão
- [ ] `GET /api/settings` retorna todas as chaves da tabela `system_settings`
- [ ] `PUT /api/settings` aceita dict parcial (atualiza apenas as chaves enviadas)
- [ ] `POST /api/settings/validate-videos-folder` lista arquivos `.mp4|.mov|.avi|.mkv` e retorna count
- [ ] Validação de URL Ollama: verificar formato antes de salvar

---

### TASK-013 — Setup inicial do Frontend (package.json + vite.config + tsconfig)

**Módulo:** frontend
**Arquivo(s):** `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/tsconfig.node.json`
**US:** US-003
**Depende de:** —
**Produz para:** todas as tasks de frontend

#### O que criar
`package.json` com dependências e scripts:
```json
{
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc && vite build",
    "preview": "vite preview",
    "test:run": "vitest run",
    "test": "vitest",
    "lint": "eslint . --ext .vue,.ts,.tsx",
    "format:check": "prettier --check src/",
    "format": "prettier --write src/"
  },
  "dependencies": {
    "vue": "^3.4", "vue-router": "^4.3", "pinia": "^2.1",
    "axios": "^1.7", "@vueuse/core": "^10.9"
  },
  "devDependencies": {
    "vite": "^5.2", "@vitejs/plugin-vue": "^5.0",
    "typescript": "^5.4", "vue-tsc": "^2.0",
    "tailwindcss": "^3.4", "vitest": "^1.6",
    "@vue/test-utils": "^2.4", "eslint": "^9", "prettier": "^3.2"
  }
}
```

`vite.config.ts`: proxy `/api` → `http://localhost:8000` em dev.

#### Critérios de conclusão
- [ ] `npm install` executa sem erros
- [ ] `npm run dev` inicia Vite na porta 5173
- [ ] `npm run build` gera `dist/` sem erros de TypeScript
- [ ] Proxy `/api` redireciona para backend em `localhost:8000`

---

### TASK-014 — Setup Tailwind CSS + shadcn-vue

**Módulo:** frontend
**Arquivo(s):** `frontend/tailwind.config.js`, `frontend/src/assets/main.css`, componentes base shadcn
**US:** US-003
**Depende de:** TASK-013
**Produz para:** todos os componentes Vue

#### O que criar
- Instalar e configurar Tailwind CSS com `@tailwind base/components/utilities`
- Instalar shadcn-vue via CLI (`npx shadcn-vue@latest init`)
- Adicionar componentes base: `Button`, `Card`, `Input`, `Select`, `Badge`, `Dialog`, `Toast`, `Progress`, `Tabs`
- Configurar tema de cores no `tailwind.config.js`

#### Critérios de conclusão
- [ ] `<Button variant="default">` renderiza com estilos corretos
- [ ] Classes Tailwind aplicadas em qualquer componente
- [ ] `useToast()` composable disponível para notificações

---

### TASK-015 — Criar src/main.ts, App.vue e router/index.ts

**Módulo:** frontend
**Arquivo(s):** `frontend/src/main.ts`, `frontend/src/App.vue`, `frontend/src/router/index.ts`
**US:** US-003
**Depende de:** TASK-013, TASK-014
**Produz para:** todas as views e stores

#### O que criar

**main.ts:** Bootstrap Vue app com Pinia e Router.

**router/index.ts:** 4 rotas:
- `/` → `DashboardView`
- `/accounts` → `AccountsView`
- `/jobs/new` → `NewJobView`
- `/settings` → `SettingsView`

**App.vue:** Layout base com `<nav>` (4 links de navegação) + `<RouterView>`.

#### Critérios de conclusão
- [ ] Navegação entre as 4 rotas funciona sem reload
- [ ] Rota `/` é a padrão (redirect se acessar rota inválida)
- [ ] Link ativo destacado visualmente na nav

---

### TASK-016 — Criar src/services/api.ts (axios)

**Módulo:** frontend
**Arquivo(s):** `frontend/src/services/api.ts`
**US:** US-001
**Depende de:** TASK-013
**Produz para:** todas as stores e componentes

#### O que criar
```typescript
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 30000,
})

// Interceptor: adicionar Content-Type
// Interceptor: tratar erros globais (401, 500)
// Interceptor: log em development

export const settingsApi = { get, update, validateFolder }
export const accountsApi = { list, getOAuthUrl, delete, test }
export const jobsApi = { list, create, get, delete, run, runStep, getStepOutput }
export const ollamaApi = { getModels, getVoices }
```

#### Critérios de conclusão
- [ ] `baseURL` lida do env (`VITE_API_URL`) com fallback `/api`
- [ ] Erros HTTP são transformados em objetos com `error` e `message`
- [ ] Timeout configurado para 30s (uploads usam timeout separado de 600s)

---

## FASE 2 — Serviços de IA e Áudio

> Integração com Ollama e edge-tts. Sem dependência de vídeo ou YouTube.

---

### TASK-017 — Criar services/text_generation/base.py + schemas.py

**Módulo:** backend
**Arquivo(s):** `backend/app/services/text_generation/base.py`, `backend/app/services/text_generation/schemas.py`
**US:** US-013
**Depende de:** TASK-009
**Produz para:** TASK-018, TASK-034

#### O que criar

**base.py:**
```python
class TextGenerator(ABC):
    @abstractmethod
    async def generate(self, input: TextGenInput) -> TextGenOutput: ...
    @abstractmethod
    async def generate_batch(self, input: TextGenInput, count: int) -> list[TextGenOutput]: ...
```

**schemas.py:**
```python
class TextGenInput(BaseModel):
    prompt: str
    model: str
    max_tokens: int = 500
    temperature: float = 0.7

class TextGenOutput(BaseModel):
    text: str
    model: str
    duration_ms: int
    tokens_used: int | None
```

#### Critérios de conclusão
- [ ] Interface ABC não importa nada de Ollama (substituível por outro provider)
- [ ] Schemas validam `prompt` não vazio e `temperature` entre 0.0 e 2.0

---

### TASK-018 — Criar services/text_generation/ollama_generator.py

**Módulo:** backend
**Arquivo(s):** `backend/app/services/text_generation/ollama_generator.py`
**US:** US-013
**Depende de:** TASK-017
**Produz para:** TASK-022, TASK-034, TASK-039

#### O que criar
Implementação `OllamaGenerator(TextGenerator)`:
- Usar `ollama.AsyncClient` com `host` configurável
- `generate()`: chama `client.generate()` com o prompt, retorna `TextGenOutput`
- `generate_batch()`: loop sequencial com yield de progresso via callback
- `list_models()`: chama `GET {ollama_url}/api/tags` e retorna lista de modelos
- Tratar `httpx.ConnectError` → lançar `OllamaUnavailableError`

#### Critérios de conclusão
- [ ] `generate()` retorna texto não vazio com um modelo Ollama real
- [ ] `OllamaUnavailableError` lançado se Ollama não responder em 5s
- [ ] `generate_batch(count=3)` chama `generate()` 3 vezes sequencialmente
- [ ] `list_models()` retorna lista vazia (não erro) se não há modelos instalados

---

### TASK-019 — Criar api/routes/ollama.py

**Módulo:** backend
**Arquivo(s):** `backend/app/api/routes/ollama.py`
**US:** US-002 (listagem de modelos), US-010 (seleção de voz)
**Depende de:** TASK-018, TASK-010
**Produz para:** TASK-056 (frontend usa para popular selects)

#### O que criar
```
GET /api/ollama/models  → lista modelos do Ollama (OllamaGenerator.list_models)
GET /api/ollama/voices  → lista vozes edge-tts disponíveis em inglês
POST /api/ollama/test   → testa conexão com o Ollama (retorna status)
```

#### Critérios de conclusão
- [ ] `GET /api/ollama/models` retorna `[]` (não 500) se Ollama offline
- [ ] `GET /api/ollama/voices` retorna lista estática de vozes `en-*` do edge-tts
- [ ] `POST /api/ollama/test` retorna `{"ok": true, "models": [...]}` ou `{"ok": false, "error": "..."}`

---

### TASK-020 — Criar services/audio/base.py + schemas.py

**Módulo:** backend
**Arquivo(s):** `backend/app/services/audio/base.py`, `backend/app/services/audio/schemas.py`
**US:** US-017
**Depende de:** TASK-009
**Produz para:** TASK-021

#### O que criar

**base.py:**
```python
class AudioGenerator(ABC):
    @abstractmethod
    async def generate(self, input: AudioGenInput) -> AudioGenOutput: ...
    @abstractmethod
    async def list_voices(self) -> list[TTSVoice]: ...
```

**schemas.py:**
```python
class AudioGenInput(BaseModel):
    text: str
    voice: str = "en-US-JennyNeural"
    target_duration_seconds: float | None = None
    rate: str = "+0%"  # velocidade: "+10%", "-5%", etc.
    output_path: str

class AudioGenOutput(BaseModel):
    file_path: str
    actual_duration_seconds: float
    target_duration_seconds: float | None
    within_tolerance: bool
    voice: str
```

#### Critérios de conclusão
- [ ] `within_tolerance` calculado como `|actual - target| / target <= 0.10` (10%)
- [ ] `output_path` validado como caminho de arquivo (não diretório)

---

### TASK-021 — Criar services/audio/edge_tts.py

**Módulo:** backend
**Arquivo(s):** `backend/app/services/audio/edge_tts.py`
**US:** US-017, US-018
**Depende de:** TASK-020
**Produz para:** TASK-038, TASK-039

#### O que criar
Implementação `EdgeTTSGenerator(AudioGenerator)`:

1. `generate()`:
   - Chama `edge_tts.Communicate(text, voice, rate=rate).save(output_path)`
   - Lê duração real com `mutagen.mp3.MP3(output_path).info.length`
   - Calcula `within_tolerance`
   - Retorna `AudioGenOutput`

2. Se `target_duration_seconds` definido e duração está fora da tolerância:
   - Ajusta `rate` automaticamente (aumenta velocidade se muito longo, diminui se muito curto)
   - Segunda tentativa com novo rate
   - Máximo 2 tentativas automáticas

3. `list_voices()`: retorna lista hardcoded das principais vozes `en-*` do edge-tts

#### Critérios de conclusão
- [ ] Arquivo MP3 gerado em `output_path` após `generate()`
- [ ] `actual_duration_seconds` corresponde à duração real do arquivo gerado
- [ ] Segunda tentativa aplicada automaticamente se fora da tolerância
- [ ] `output_path` é criado com permissões corretas (sem erro de escrita)

#### Pontos de atenção
- `edge-tts` requer conexão com internet — lançar erro descritivo se falhar com `httpx.ConnectError`
- Usar `asyncio.get_event_loop().run_in_executor()` se a biblioteca não for async nativa

---

## FASE 3 — Pipeline de Vídeo

> Seleção de vídeos, cortes, sequenciamento anti-plágio e montagem final.
> FFmpeg deve estar disponível no PATH ou no container.

---

### TASK-022 — Criar services/video/schemas.py

**Módulo:** backend
**Arquivo(s):** `backend/app/services/video/schemas.py`
**US:** US-021, US-022, US-023, US-024
**Depende de:** TASK-009
**Produz para:** TASK-023, TASK-024, TASK-025, TASK-026

#### O que criar
```python
class VideoFile(BaseModel):
    path: str
    duration_seconds: float
    width: int
    height: int

class ClipSpec(BaseModel):
    source_video: str
    start_seconds: float
    duration_seconds: float
    clip_index: int

class SequencedClip(BaseModel):
    clip_spec: ClipSpec
    sequence_position: int
    output_path: str | None = None

class VideoCompositionInput(BaseModel):
    sequenced_clips: list[SequencedClip]
    audio_path: str
    output_path: str
    dimension: str = "16:9"  # "16:9" ou "9:16"
    crop_for_vertical: bool = False

class VideoCompositionOutput(BaseModel):
    output_path: str
    duration_seconds: float
    width: int
    height: int
    file_size_bytes: int
```

#### Critérios de conclusão
- [ ] Todos os schemas com validação (duração > 0, dimension em ["16:9", "9:16"])
- [ ] `ClipSpec` valida `start_seconds + duration_seconds` dentro dos limites do vídeo (validado no cutter)

---

### TASK-023 — Criar services/video/selector.py

**Módulo:** backend
**Arquivo(s):** `backend/app/services/video/selector.py`
**US:** US-021
**Depende de:** TASK-022
**Produz para:** TASK-024, TASK-038

#### O que criar
```python
async def scan_videos_folder(folder: str) -> list[VideoFile]:
    """Lê pasta, extrai duração e resolução via ffprobe."""

async def select_videos_for_duration(
    folder: str,
    required_duration: float,
    safety_margin: float = 0.10,
) -> list[VideoFile]:
    """
    Seleciona vídeos aleatoriamente até cobrir required_duration * (1 + safety_margin).
    Ignora vídeos com duração < 6s.
    Permite repetição se necessário.
    Lança InsufficientVideosError se pasta vazia ou vídeos totais insuficientes.
    """
```

Usar `ffprobe` (via `ffmpeg.probe()`) para ler metadados.

#### Critérios de conclusão
- [ ] `scan_videos_folder` retorna lista vazia (não erro) para pasta sem vídeos suportados
- [ ] `select_videos_for_duration` usa `random.shuffle()` na lista antes de selecionar
- [ ] Duração total dos vídeos selecionados >= `required_duration * 1.10`
- [ ] `InsufficientVideosError` com mensagem indicando duração disponível vs necessária

---

### TASK-024 — Criar services/video/cutter.py

**Módulo:** backend
**Arquivo(s):** `backend/app/services/video/cutter.py`
**US:** US-022
**Depende de:** TASK-022
**Produz para:** TASK-025, TASK-038

#### O que criar
```python
async def generate_clip_specs(
    videos: list[VideoFile],
    total_duration_needed: float,
    min_clip: int = 3,
    max_clip: int = 6,
) -> list[ClipSpec]:
    """
    Para cada vídeo selecionado, gera ClipSpecs com:
    - duração aleatória entre min_clip e max_clip segundos
    - início aleatório dentro do vídeo (evitando ultrapassar o final)
    - quantos cortes forem necessários para cobrir total_duration_needed
    """

async def cut_clip(spec: ClipSpec, output_dir: str) -> str:
    """
    Executa o corte via ffmpeg-python usando -ss e -t.
    Retorna path do arquivo de clipe gerado.
    Usa codec copy quando possível (sem re-encode) para velocidade.
    """
```

#### Critérios de conclusão
- [ ] Corte não ultrapassa o final do vídeo (`start + duration <= video.duration`)
- [ ] Arquivos de clipe salvos em `output_dir` com nome `clip_{i:04d}_{video_name}.mp4`
- [ ] FFmpegError lançado com o stderr do FFmpeg se o corte falhar
- [ ] `cut_clip` executado em ProcessPoolExecutor (CPU-bound)

#### Pontos de atenção
- Usar `-ss` antes do `-i` (seek antes do input) para velocidade — `ffmpeg -ss {start} -i input.mp4 -t {dur} -c copy output.mp4`
- `-c copy` pode causar imprecisão nos cortes — aceitável para 3-6s

---

### TASK-025 — Criar services/video/sequencer.py (algoritmo anti-plágio)

**Módulo:** backend
**Arquivo(s):** `backend/app/services/video/sequencer.py`
**US:** US-023
**Depende de:** TASK-022
**Produz para:** TASK-026, TASK-038

#### O que criar
```python
def sequence_clips_anti_plagiarism(clips: list[ClipSpec]) -> list[SequencedClip]:
    """
    Algoritmo Interleave com max-heap:
    1. Agrupar clips por source_video
    2. Max-heap (heapq com negativo) por tamanho do grupo
    3. Loop: pop maior grupo A → adicionar clipe → pop próximo grupo B (≠ A) → adicionar → push de volta
    4. Se sobrar clipes de apenas 1 vídeo → aplicar flag de variação de velocidade
    5. Validação final: assert sequence[i].source_video != sequence[i+1].source_video
    """
```

#### Critérios de conclusão
- [ ] Para N vídeos com distribuição uniforme, nenhum par consecutivo é do mesmo vídeo
- [ ] Para 1 vídeo, lança `AntiPlagiarismError` com mensagem orientando adicionar mais vídeos
- [ ] Para 2 vídeos com N/2 clipes cada, alterna perfeitamente ABABAB...
- [ ] Lista de entrada vazia retorna lista vazia (sem erro)
- [ ] Validação final com `assert` (ou exceção) garante a propriedade anti-plágio

#### Pontos de atenção
- `heapq` em Python é min-heap — usar valores negativos para simular max-heap
- Manter o `video_id` do último clipe adicionado para evitar consecutivos

---

### TASK-026 — Criar services/video/composer.py

**Módulo:** backend
**Arquivo(s):** `backend/app/services/video/composer.py`
**US:** US-024, US-025, US-026
**Depende de:** TASK-022
**Produz para:** TASK-038

#### O que criar
```python
async def compose_video(input: VideoCompositionInput) -> VideoCompositionOutput:
    """
    1. Criar arquivo de lista de concatenação (concat demuxer do FFmpeg)
    2. Concatenar clipes: ffmpeg -f concat -safe 0 -i list.txt -c copy temp_video.mp4
    3. Aplicar dimensão (16:9 ou 9:16):
       - 16:9: scale=1920:1080, pad para letterbox se necessário
       - 9:16 com crop: crop=1080:1920 centralizado
       - 9:16 sem crop: scale + pad com barras laterais
    4. Merge áudio: -i temp_video.mp4 -i audio.mp3 -c:v copy -c:a aac -shortest output.mp4
    5. Limpar arquivos temporários
    6. Ler duração e resolução do arquivo final via ffprobe
    """
```

#### Critérios de conclusão
- [ ] Vídeo final tem codec H.264 (vídeo) e AAC (áudio)
- [ ] Vídeo final tem duração aproximada do áudio (tolerância 1s)
- [ ] 16:9 saída em 1920x1080
- [ ] 9:16 saída em 1080x1920
- [ ] Arquivos temporários (list.txt, temp_video.mp4) removidos após sucesso
- [ ] Executado em ProcessPoolExecutor

---

## FASE 4 — YouTube e Upload

> OAuth2, upload com retomada, metadados via Ollama e agendamento.

---

### TASK-027 — Criar app/core/crypto.py (criptografia de tokens)

**Módulo:** backend
**Arquivo(s):** `backend/app/core/crypto.py`
**US:** US-007
**Depende de:** TASK-002
**Produz para:** TASK-028, TASK-029

#### O que criar
```python
def get_fernet(settings: Settings) -> Fernet:
    """Cria Fernet a partir de SECRET_KEY (derivando com PBKDF2 se necessário)."""

def encrypt(data: str, settings: Settings) -> str:
    """Criptografa string e retorna base64."""

def decrypt(data: str, settings: Settings) -> str:
    """Descriptografa base64 e retorna string original."""
```

#### Critérios de conclusão
- [ ] `encrypt(decrypt(data))` == `data` (round-trip)
- [ ] `SECRET_KEY` com menos de 32 bytes é derivado via PBKDF2 para gerar chave Fernet válida
- [ ] `decrypt` lança erro descritivo se dados corrompidos (não `InvalidToken` genérico)

---

### TASK-028 — Criar services/youtube/auth.py (OAuth2 flow)

**Módulo:** backend
**Arquivo(s):** `backend/app/services/youtube/auth.py`
**US:** US-007
**Depende de:** TASK-027, TASK-009
**Produz para:** TASK-029, TASK-030

#### O que criar
```python
def get_oauth_authorization_url(settings: Settings) -> str:
    """Gera URL de autorização OAuth com scopes youtube.upload + youtube.readonly."""

async def exchange_code_for_tokens(code: str, settings: Settings) -> dict:
    """Troca code por access_token + refresh_token via google-auth-oauthlib."""

async def get_channel_info(credentials: dict) -> dict:
    """Busca nome, channel_id e avatar_url via YouTube Data API."""

async def refresh_token_if_expired(account: YouTubeAccount, db: Session, settings: Settings) -> Credentials:
    """Verifica expiração, renova via refresh_token se necessário, persiste no banco."""

async def test_token(account: YouTubeAccount, settings: Settings) -> bool:
    """Faz requisição simples à API para validar o token."""
```

#### Critérios de conclusão
- [ ] URL de autorização inclui `access_type=offline` (para obter refresh_token)
- [ ] Tokens armazenados como JSON criptografado com Fernet (TASK-027)
- [ ] `refresh_token_if_expired` atualiza `credentials` e `updated_at` no banco
- [ ] `test_token` retorna `False` (não levanta exceção) se token inválido

#### Pontos de atenção
- O callback OAuth deve usar `http://localhost:8000/api/accounts/oauth/callback` como `redirect_uri`
- Google Cloud Console deve ter este URI cadastrado como redirect autorizado

---

### TASK-029 — Criar api/routes/accounts.py

**Módulo:** backend
**Arquivo(s):** `backend/app/api/routes/accounts.py`
**US:** US-007, US-008, US-009, US-010
**Depende de:** TASK-028, TASK-005, TASK-009, TASK-010
**Produz para:** TASK-046, TASK-051, TASK-052

#### O que criar
```
GET  /api/accounts              → lista todas as contas (sem credentials)
GET  /api/accounts/oauth/url    → retorna URL de autorização OAuth
GET  /api/accounts/oauth/callback?code=XXX → troca code, salva conta, redirect para frontend
DELETE /api/accounts/{id}       → remove conta e apaga tokens
POST /api/accounts/{id}/test    → testa validade do token
```

#### Critérios de conclusão
- [ ] `GET /api/accounts` nunca retorna `credentials` no payload
- [ ] Callback OAuth salva conta no banco e redireciona para `/accounts` no frontend
- [ ] `DELETE` remove tokens criptografados e o registro da conta
- [ ] `POST /{id}/test` retorna `{"valid": true|false, "error": "..."}` — nunca 500
- [ ] Contas com token expirado aparecem na lista com `is_active: false`

---

### TASK-030 — Criar services/youtube/uploader.py

**Módulo:** backend
**Arquivo(s):** `backend/app/services/youtube/uploader.py`
**US:** US-029, US-030
**Depende de:** TASK-028
**Produz para:** TASK-039

#### O que criar
```python
async def upload_video(
    account: YouTubeAccount,
    video_path: str,
    title: str,
    description: str,
    category_id: str = "22",  # "People & Blogs"
    privacy: str = "public",  # "public"|"private"|"unlisted"
    publish_at: datetime | None = None,
    progress_callback: Callable[[int], None] | None = None,
) -> str:
    """
    Upload via YouTube Data API v3 com resumable upload.
    Retorna video_id do YouTube.
    Chama progress_callback com percentual (0-100) a cada chunk.
    Se publish_at definido: sobe como 'private' com scheduledStartTime.
    """
```

#### Critérios de conclusão
- [ ] Usa resumable upload (MediaFileUpload com `resumable=True`)
- [ ] `progress_callback` chamado a cada chunk (~1MB)
- [ ] `video_id` retornado após upload completo
- [ ] `YouTubeAPIError` lançado com code e message da API em caso de falha
- [ ] Token renovado automaticamente se expirado antes do upload

---

### TASK-031 — Criar services/metadata/generator.py

**Módulo:** backend
**Arquivo(s):** `backend/app/services/metadata/generator.py`
**US:** US-027, US-028
**Depende de:** TASK-018
**Produz para:** TASK-039

#### O que criar
```python
async def generate_title(
    narrator_text: str,
    ollama_url: str,
    model: str,
    title_prompt: str | None = None,
) -> str:
    """
    Gera título com máx. 100 chars.
    Prompt padrão: "Based on the following text, create a YouTube video title (max 100 chars): {text}"
    Trunca automaticamente se modelo gerar mais de 100 chars.
    """

async def generate_description(
    narrator_text: str,
    ollama_url: str,
    model: str,
    description_prompt: str | None = None,
) -> str:
    """Gera descrição com máx. 5000 chars."""
```

#### Critérios de conclusão
- [ ] Título sempre ≤ 100 caracteres após `generate_title`
- [ ] Descrição sempre ≤ 5000 caracteres
- [ ] Se Ollama offline, lança `OllamaUnavailableError` (não retorna string vazia)

---

### TASK-032 — Configurar APScheduler para agendamento de uploads

**Módulo:** backend
**Arquivo(s):** `backend/app/core/scheduler.py`
**US:** US-030
**Depende de:** TASK-002, TASK-004
**Produz para:** TASK-039, TASK-011 (lifespan)

#### O que criar
```python
def get_scheduler() -> AsyncIOScheduler:
    """Singleton AsyncIOScheduler com SQLAlchemyJobStore (usa o SQLite do projeto)."""

async def schedule_upload_job(job_id: int, scheduled_at: datetime) -> str:
    """
    Agenda execução do upload do job para a data especificada.
    Retorna o ID do job no scheduler.
    """

async def cancel_scheduled_job(scheduler_job_id: str) -> None: ...
```

#### Critérios de conclusão
- [ ] Scheduler inicia/para no lifespan da aplicação (TASK-011)
- [ ] Jobs agendados persistidos no SQLite (sobrevivem a restart do servidor)
- [ ] `schedule_upload_job` usa fuso UTC internamente
- [ ] Job cancelado quando processamento é deletado

---

## FASE 5 — Orquestração e Pipeline Runner

> Integra todos os serviços em um pipeline coeso com rastreamento de etapas e SSE.

---

### TASK-033 — Criar app/core/events.py (SSE event bus)

**Módulo:** backend
**Arquivo(s):** `backend/app/core/events.py`
**US:** US-035
**Depende de:** —
**Produz para:** TASK-036, TASK-037, TASK-041

#### O que criar
```python
class EventBus:
    """In-memory pub/sub para SSE. Thread-safe via asyncio.Queue."""
    
    async def publish(self, job_id: int, event: dict) -> None: ...
    async def subscribe(self, job_id: int | None) -> AsyncGenerator[dict, None]: ...
    def unsubscribe(self, job_id: int | None, queue: asyncio.Queue) -> None: ...

event_bus = EventBus()  # Singleton global
```

Formato padrão do evento:
```python
{
    "job_id": 1,
    "status": "running",
    "current_step": "video_cutting",
    "progress": 45,
    "step_log": "Cortando clipe 3/8..."
}
```

#### Critérios de conclusão
- [ ] Múltiplos subscribers recebem o mesmo evento (fan-out)
- [ ] Subscribe com `job_id=None` recebe eventos de todos os jobs
- [ ] Queue tem maxsize=100 (descarta eventos antigos se subscriber lento)
- [ ] Unsubscribe limpa a queue do subscriber

---

### TASK-034 — Criar pipeline/steps.py e pipeline/state.py

**Módulo:** backend
**Arquivo(s):** `backend/app/pipeline/steps.py`, `backend/app/pipeline/state.py`
**US:** US-036
**Depende de:** TASK-022
**Produz para:** TASK-035

#### O que criar

**steps.py:**
```python
class PipelineStep(str, Enum):
    TEXT_GENERATION = "text_generation"
    AUDIO_GENERATION = "audio_generation"
    AUDIO_VERIFICATION = "audio_verification"
    VIDEO_SELECTION = "video_selection"
    VIDEO_CUTTING = "video_cutting"
    VIDEO_SEQUENCING = "video_sequencing"
    VIDEO_COMPOSITION = "video_composition"
    METADATA_GENERATION = "metadata_generation"
    UPLOAD = "upload"

STEP_METADATA = {
    PipelineStep.TEXT_GENERATION: StepMeta(name="Geração de Texto", weight=10),
    # ... peso de cada etapa para cálculo de progresso global
}
```

**state.py:**
```python
class JobState(BaseModel):
    job_id: int
    config: JobConfig
    # Outputs de cada etapa (acumulativos)
    generated_text: str | None = None
    audio_path: str | None = None
    audio_duration: float | None = None
    selected_videos: list[VideoFile] | None = None
    clip_specs: list[ClipSpec] | None = None
    sequenced_clips: list[SequencedClip] | None = None
    composed_video_path: str | None = None
    video_title: str | None = None
    video_description: str | None = None

    def to_step_input(self, step: PipelineStep) -> dict: ...
    def save_step_output(self, step: PipelineStep, output: dict) -> None: ...
```

#### Critérios de conclusão
- [ ] `JobState` serializável para JSON (para persistir no `job_steps.output`)
- [ ] `to_step_input` retorna apenas os dados necessários para a etapa especificada
- [ ] `STEP_METADATA` pesos somam 100 (para cálculo correto de progress%)

---

### TASK-035 — Criar pipeline/runner.py (orquestrador do pipeline)

**Módulo:** backend
**Arquivo(s):** `backend/app/pipeline/runner.py`
**US:** US-031, US-036
**Depende de:** TASK-021, TASK-023, TASK-024, TASK-025, TASK-026, TASK-030, TASK-031, TASK-033, TASK-034
**Produz para:** TASK-036

#### O que criar
```python
async def run_pipeline(job_id: int, db: Session, settings: Settings) -> None:
    """
    Executa o pipeline completo:
    1. Carrega job e config do banco
    2. Cria JobState
    3. Para cada PipelineStep na ordem:
       a. Atualiza job.current_step e job.progress no banco
       b. Publica evento SSE
       c. Salva JobStep com status=running e input
       d. Executa o serviço correspondente
       e. Salva output no JobStep
       f. Atualiza JobState
    4. Ao final: job.status=completed, job.output_video=path
    5. Em erro: job.status=error, job.error_message=str(exc)
    """

async def run_single_step(
    job_id: int,
    step: PipelineStep,
    db: Session,
    settings: Settings,
) -> dict:
    """Executa uma etapa isolada (modo debug). Retorna o output da etapa."""
```

#### Critérios de conclusão
- [ ] Pipeline para e persiste erro se qualquer etapa lançar exceção
- [ ] Job cancelado (`status=cancelled`) interrompe o pipeline graciosamente
- [ ] `run_pipeline` executado em background task (não bloqueia o endpoint)
- [ ] Cada etapa tem seu `JobStep` salvo com `started_at` e `completed_at`

---

### TASK-036 — Criar api/routes/jobs.py

**Módulo:** backend
**Arquivo(s):** `backend/app/api/routes/jobs.py`
**US:** US-031, US-034, US-036
**Depende de:** TASK-006, TASK-009, TASK-010, TASK-035
**Produz para:** TASK-039, TASK-047, TASK-048, TASK-062

#### O que criar
```
GET    /api/jobs                        → lista jobs com filtro por status
POST   /api/jobs                        → cria novo job (não inicia o pipeline)
GET    /api/jobs/{id}                   → detalhe do job + steps
DELETE /api/jobs/{id}                   → cancela/remove job
POST   /api/jobs/{id}/run               → inicia pipeline completo (background task)
POST   /api/jobs/{id}/steps/{step}      → executa etapa isolada (debug)
GET    /api/jobs/{id}/steps/{step}/output → retorna output de uma etapa
```

#### Critérios de conclusão
- [ ] `POST /api/jobs/{id}/run` retorna imediatamente (não aguarda pipeline)
- [ ] `DELETE` em job running seta `status=cancelled` (não força kill da task)
- [ ] `GET /api/jobs` suporta query param `?status=running` para filtro
- [ ] `GET /api/jobs/{id}/steps/{step}/output` retorna 404 se etapa não executada

---

### TASK-037 — Criar api/routes/sse.py

**Módulo:** backend
**Arquivo(s):** `backend/app/api/routes/sse.py`
**US:** US-035
**Depende de:** TASK-033
**Produz para:** TASK-048 (SSE client no frontend)

#### O que criar
```
GET /api/sse/jobs           → stream SSE de todos os jobs
GET /api/sse/jobs/{id}      → stream SSE de um job específico
```

Usar `EventSourceResponse` do `sse-starlette`. Stream publica eventos do `EventBus`.

#### Critérios de conclusão
- [ ] Conexão SSE mantida aberta até cliente desconectar
- [ ] Heartbeat (`:ping`) enviado a cada 15s para evitar timeout de proxy
- [ ] `EventSourceResponse` com `media_type="text/event-stream"`
- [ ] Eventos no formato `data: {json}\n\n`

---

### TASK-038 — Testes unitários do sequencer e pipeline

**Módulo:** backend
**Arquivo(s):** `backend/tests/services/test_sequencer.py`, `backend/tests/conftest.py`
**US:** US-023
**Depende de:** TASK-025, TASK-034
**Produz para:** CI/CD

#### O que criar

**conftest.py:** fixtures compartilhadas:
- `db_session`: banco SQLite in-memory para testes
- `settings_override`: settings com caminhos temporários
- `mock_ffmpeg`: mock do subprocess do FFmpeg
- `sample_videos`: lista de `VideoFile` para testes

**test_sequencer.py:** cenários do algoritmo anti-plágio:
- 1 vídeo → `AntiPlagiarismError`
- 2 vídeos iguais em quantidade → alternância perfeita ABABAB
- 3 vídeos com distribuição desigual → validação final garante não-consecutivo
- 10 vídeos, 50 clipes → validação final garante propriedade
- Lista vazia → lista vazia retornada

#### Critérios de conclusão
- [ ] `pytest tests/services/test_sequencer.py` passa 100%
- [ ] Cobertura do módulo `sequencer.py` ≥ 95%
- [ ] Nenhum teste faz I/O de arquivo (tudo mockado)

---

### TASK-039 — Testes de integração das rotas de accounts e jobs

**Módulo:** backend
**Arquivo(s):** `backend/tests/api/test_accounts.py`, `backend/tests/api/test_jobs.py`
**US:** US-007, US-031
**Depende de:** TASK-029, TASK-036
**Produz para:** CI/CD

#### O que criar
Usar `httpx.AsyncClient` com `app` do FastAPI (sem servidor real).

**test_accounts.py:**
- `GET /api/accounts` retorna lista vazia
- `GET /api/accounts/oauth/url` retorna URL válida
- `DELETE /api/accounts/{id}` com conta existente → 204
- `DELETE /api/accounts/{id}` com conta inexistente → 404
- `POST /api/accounts/{id}/test` com token mockado → `{"valid": true}`

**test_jobs.py:**
- `POST /api/jobs` cria job com status `pending`
- `GET /api/jobs` retorna lista com o job criado
- `GET /api/jobs/{id}` retorna detalhes do job
- `DELETE /api/jobs/{id}` remove job

#### Critérios de conclusão
- [ ] `pytest tests/api/` passa 100%
- [ ] Banco de dados real não é acessado (fixture `db_session` in-memory)
- [ ] Dependências externas (Ollama, YouTube API) são mockadas

---

## FASE 6 — Interface Vue

> Todas as views, components, stores e serviços do frontend.

---

### TASK-040 — Criar stores/settings.ts (Pinia)

**Módulo:** frontend
**Arquivo(s):** `frontend/src/stores/settings.ts`
**US:** US-033
**Depende de:** TASK-016
**Produz para:** TASK-049

#### O que criar
```typescript
export const useSettingsStore = defineStore('settings', () => {
  const settings = ref<Record<string, string>>({})
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function loadSettings(): Promise<void> { ... }
  async function updateSettings(updates: Record<string, string>): Promise<void> { ... }
  async function validateVideosFolder(path: string): Promise<{ valid: boolean; count: number }> { ... }

  return { settings, loading, error, loadSettings, updateSettings, validateVideosFolder }
})
```

#### Critérios de conclusão
- [ ] `loadSettings()` chamado uma vez na montagem de `SettingsView`
- [ ] `updateSettings()` faz PUT e relê as settings após sucesso
- [ ] Erro persistido em `error` (não lançado como exceção)

---

### TASK-041 — Criar stores/accounts.ts (Pinia)

**Módulo:** frontend
**Arquivo(s):** `frontend/src/stores/accounts.ts`
**US:** US-008, US-009, US-010
**Depende de:** TASK-016
**Produz para:** TASK-051, TASK-052

#### O que criar
```typescript
export const useAccountsStore = defineStore('accounts', () => {
  const accounts = ref<Account[]>([])
  
  async function loadAccounts(): Promise<void> { ... }
  async function getOAuthUrl(): Promise<string> { ... }
  async function removeAccount(id: number): Promise<void> { ... }
  async function testAccount(id: number): Promise<{ valid: boolean }> { ... }
  
  const activeAccounts = computed(() => accounts.value.filter(a => a.is_active))
  
  return { accounts, activeAccounts, loadAccounts, getOAuthUrl, removeAccount, testAccount }
})
```

#### Critérios de conclusão
- [ ] `activeAccounts` computed filtra contas com `is_active = true`
- [ ] `removeAccount` atualiza lista local após sucesso na API
- [ ] `getOAuthUrl` redireciona o browser para a URL retornada

---

### TASK-042 — Criar stores/jobs.ts (Pinia)

**Módulo:** frontend
**Arquivo(s):** `frontend/src/stores/jobs.ts`
**US:** US-031, US-034
**Depende de:** TASK-016, TASK-048
**Produz para:** TASK-053, TASK-054, TASK-055, TASK-062

#### O que criar
```typescript
export const useJobsStore = defineStore('jobs', () => {
  const jobs = ref<Job[]>([])
  const currentJob = ref<JobDetail | null>(null)
  const filter = ref<string>('all')

  async function loadJobs(): Promise<void> { ... }
  async function createJob(config: JobConfig): Promise<Job> { ... }
  async function runJob(id: number): Promise<void> { ... }
  async function deleteJob(id: number): Promise<void> { ... }
  async function runStep(jobId: number, step: string): Promise<StepOutput> { ... }

  // Atualiza job pelo ID via evento SSE
  function updateJobFromSSE(event: SSEJobEvent): void { ... }

  const filteredJobs = computed(() => ...)

  return { jobs, currentJob, filter, filteredJobs, loadJobs, createJob, runJob, deleteJob, runStep, updateJobFromSSE }
})
```

#### Critérios de conclusão
- [ ] `updateJobFromSSE` atualiza o job correto na lista sem re-fetch
- [ ] `filteredJobs` filtra por `filter.value` (all, running, completed, error)
- [ ] `createJob` navega para dashboard após criação

---

### TASK-043 — Criar services/sse.ts (SSE client)

**Módulo:** frontend
**Arquivo(s):** `frontend/src/services/sse.ts`
**US:** US-035
**Depende de:** TASK-016
**Produz para:** TASK-055

#### O que criar
```typescript
export function useJobsSSE(onEvent: (event: SSEJobEvent) => void) {
  let source: EventSource | null = null

  function connect() {
    source = new EventSource('/api/sse/jobs')
    source.onmessage = (e) => onEvent(JSON.parse(e.data))
    source.onerror = () => {
      source?.close()
      setTimeout(connect, 3000)  // reconexão automática após 3s
    }
  }

  function disconnect() { source?.close() }

  return { connect, disconnect }
}
```

#### Critérios de conclusão
- [ ] Reconexão automática após 3s em caso de erro
- [ ] `disconnect()` fecha a conexão sem tentar reconectar
- [ ] `onEvent` recebe objeto tipado (não string raw)

---

### TASK-044 — Criar SettingsView.vue

**Módulo:** frontend
**Arquivo(s):** `frontend/src/views/SettingsView.vue`
**US:** US-033
**Depende de:** TASK-040, TASK-014, TASK-019
**Produz para:** —

#### O que criar
View com 3 seções usando `<Tabs>`:

1. **Vídeos Fonte:** campo de path + botão "Validar pasta" (mostra count de vídeos)
2. **Ollama:** campo de URL + seletor de modelo padrão + botão "Testar conexão"
3. **API Google:** campos de Client ID e Client Secret (tipo password com toggle)

Cada seção tem botão "Salvar" independente com toast de feedback.

#### Critérios de conclusão
- [ ] Configurações carregadas do store ao montar a view
- [ ] "Testar conexão Ollama" exibe lista de modelos se bem-sucedido
- [ ] "Validar pasta" exibe `N vídeos encontrados` ou erro
- [ ] Client ID/Secret mascarados por padrão com botão de reveal

---

### TASK-045 — Criar AccountCard.vue e OAuthButton.vue

**Módulo:** frontend
**Arquivo(s):** `frontend/src/components/accounts/AccountCard.vue`, `.../OAuthButton.vue`
**US:** US-008, US-009
**Depende de:** TASK-041
**Produz para:** TASK-046

#### O que criar

**AccountCard.vue:** card exibindo avatar, nome do canal, email, badge de status (Ativo/Expirado/Inválido), botões "Testar" e "Remover" (com modal de confirmação).

**OAuthButton.vue:** botão com logo do Google que chama `accountsStore.getOAuthUrl()` e redireciona.

#### Critérios de conclusão
- [ ] Badge colorido: verde (ativo), amarelo (expirado), vermelho (inválido)
- [ ] Modal de confirmação antes de remover (exibe nome da conta)
- [ ] Botão "Remover" desabilitado durante a operação (loading state)

---

### TASK-046 — Criar AccountsView.vue

**Módulo:** frontend
**Arquivo(s):** `frontend/src/views/AccountsView.vue`
**US:** US-032
**Depende de:** TASK-041, TASK-045
**Produz para:** —

#### O que criar
View com:
- Grid de `AccountCard` para cada conta conectada
- Estado vazio com mensagem e botão "Conectar primeira conta"
- Botão "Conectar nova conta" (usa `OAuthButton`)
- Loading skeleton durante carregamento

#### Critérios de conclusão
- [ ] Lista recarregada após retorno do OAuth (detectar `?connected=true` na URL)
- [ ] Estado vazio com ilustração orientando o usuário
- [ ] Contador de contas ativas no título da aba

---

### TASK-047 — Criar JobCard.vue e JobStatus.vue

**Módulo:** frontend
**Arquivo(s):** `frontend/src/components/job/JobCard.vue`, `.../JobStatus.vue`
**US:** US-031
**Depende de:** TASK-042
**Produz para:** TASK-048

#### O que criar

**JobStatus.vue:** componente reutilizável que exibe badge com ícone por status:
- 🔵 `running` | ✅ `completed` | ❌ `error` | ⏳ `pending` | ⏰ `scheduled`

**JobCard.vue:** card com nome do job, status badge, barra de progresso, etapa atual, conta de destino, data de criação. Link para o vídeo no YouTube se concluído.

#### Critérios de conclusão
- [ ] Barra de progresso animada durante `status=running`
- [ ] Link para YouTube visível e clicável após `status=completed`
- [ ] Botão "Ver detalhes" navega para rota de detalhe do job

---

### TASK-048 — Criar DashboardView.vue

**Módulo:** frontend
**Arquivo(s):** `frontend/src/views/DashboardView.vue`
**US:** US-031, US-035
**Depende de:** TASK-042, TASK-043, TASK-047
**Produz para:** —

#### O que criar
View com:
- Grid de `JobCard` com todos os processamentos
- Filtros por status (`Todos | Em andamento | Concluídos | Erros`)
- Botão "Novo Processamento" (navega para `/jobs/new`)
- SSE conectado via `useJobsSSE()` → chama `jobsStore.updateJobFromSSE()`
- Estado vazio com CTA para criar primeiro processamento

#### Critérios de conclusão
- [ ] Status atualizado em tempo real via SSE (sem polling)
- [ ] SSE desconectado ao sair da view (no `onUnmounted`)
- [ ] Filtro de status funciona client-side (sem nova requisição)

---

### TASK-049 — Criar TextGenForm.vue

**Módulo:** frontend
**Arquivo(s):** `frontend/src/components/forms/TextGenForm.vue`
**US:** US-013, US-015
**Depende de:** TASK-016, TASK-040
**Produz para:** TASK-062

#### O que criar
Formulário com:
- Toggle "Usar IA / Texto manual"
- Modo IA: seletor de modelo + textarea do prompt (com contador de caracteres) + campo de quantidade (1-50)
- Modo manual: textarea para o texto
- Botão "Gerar" (ou "Adicionar" no modo manual)
- Preview dos textos gerados/inseridos (lista editável)
- Progress bar para geração em lote

#### Critérios de conclusão
- [ ] Toggle não apaga textos já gerados (pede confirmação)
- [ ] Progress mostra `Gerando N/total...` durante lote
- [ ] Cada texto na lista tem botões "Editar", "Regenerar" e "Remover"
- [ ] Validação: prompt não vazio em modo IA; texto não vazio em modo manual

---

### TASK-050 — Criar AudioForm.vue

**Módulo:** frontend
**Arquivo(s):** `frontend/src/components/forms/AudioForm.vue`
**US:** US-016, US-017, US-018
**Depende de:** TASK-016
**Produz para:** TASK-062

#### O que criar
Formulário com:
- Campo de duração alvo em segundos (com display em mm:ss)
- Seletor de voz (lista carregada de `GET /api/ollama/voices`)
- Botão "Gerar Áudios" (um por texto da etapa anterior)
- Lista de resultados com duração real, status de tolerância (✅/⚠️) e player HTML5

#### Critérios de conclusão
- [ ] Player de áudio nativo (`<audio>`) para cada arquivo gerado
- [ ] Status ✅ / ⚠️ comparando duração real vs alvo
- [ ] Botão "Regenerar" individual para cada áudio

---

### TASK-051 — Criar VideoForm.vue e UploadForm.vue

**Módulo:** frontend
**Arquivo(s):** `frontend/src/components/forms/VideoForm.vue`, `.../UploadForm.vue`
**US:** US-021, US-025, US-026, US-029, US-030
**Depende de:** TASK-016, TASK-041
**Produz para:** TASK-062

#### O que criar

**VideoForm.vue:**
- Display da pasta configurada (com link para Configurações se vazia)
- Seletor de dimensão: "16:9 (YouTube)" / "9:16 (Shorts)"
- Se 9:16: toggle "Com crop / Sem crop (letterbox)"
- Preview ilustrativo da dimensão escolhida

**UploadForm.vue:**
- Seletor de conta (dropdown das contas ativas)
- Campo de título (pré-preenchido se gerado por IA, editável)
- Textarea de descrição (pré-preenchida se gerada por IA, editável)
- Toggle "Publicar agora / Agendar"
- Se agendar: datepicker + timepicker

#### Critérios de conclusão
- [ ] Conta inválida/expirada aparece desabilitada no dropdown
- [ ] Data de agendamento não pode ser no passado (validação)
- [ ] Campos de título e descrição com contadores de caracteres (100 / 5000)

---

### TASK-052 — Criar StepOutput.vue e StepDebugger.vue

**Módulo:** frontend
**Arquivo(s):** `frontend/src/components/job/StepOutput.vue`, `.../StepDebugger.vue`
**US:** US-037, US-036
**Depende de:** TASK-042
**Produz para:** TASK-053, TASK-062

#### O que criar

**StepOutput.vue:** Área de log estilo terminal com scroll, timestamps, níveis coloridos (INFO=cinza, ERROR=vermelho, DEBUG=azul). Botão "Copiar log".

**StepDebugger.vue:** Painel com lista de todas as etapas do pipeline, cada uma com status badge e botão "Executar isolado". Ao executar, exibe `StepOutput` da etapa.

#### Critérios de conclusão
- [ ] Log renderiza com fonte monospace e scroll automático para o fim
- [ ] Botão "Executar isolado" desabilitado se pré-condições não atendidas
- [ ] Erro de execução isolada exibido no StepOutput (não como alert)

---

### TASK-053 — Criar NewJobView.vue (wizard multi-step)

**Módulo:** frontend
**Arquivo(s):** `frontend/src/views/NewJobView.vue`
**US:** US-034
**Depende de:** TASK-042, TASK-041, TASK-049, TASK-050, TASK-051
**Produz para:** —

#### O que criar
Wizard com 6 steps usando `<Tabs>` ou stepper visual:
1. **Conta** — selecionar conta YouTube destino
2. **Texto** — `TextGenForm`
3. **Áudio** — `AudioForm`
4. **Vídeo** — `VideoForm`
5. **Metadados** — título + descrição (gerados ou manuais)
6. **Publicação** — `UploadForm` + resumo final

Botões "Anterior" / "Próximo" com validação por step. Botão "Iniciar Processamento" no último step.

Estado da view persistido no Pinia (`useJobsStore`) para não perder ao navegar.

#### Critérios de conclusão
- [ ] Não é possível avançar sem preencher campos obrigatórios do step atual
- [ ] Step 5 chama `GET /api/ollama/generate` para título e descrição automaticamente (se IA ativada)
- [ ] "Iniciar Processamento" chama `POST /api/jobs` + `POST /api/jobs/{id}/run` e redireciona para dashboard
- [ ] Estado não é perdido ao navegar para `/accounts` e voltar

---

### TASK-054 — Criar página de detalhes do job

**Módulo:** frontend
**Arquivo(s):** `frontend/src/views/JobDetailView.vue`, `router/index.ts` (atualização)
**US:** US-037, US-036
**Depende de:** TASK-042, TASK-052
**Produz para:** —

#### O que criar
View acessível em `/jobs/{id}` com:
- Header com nome do job, status, progresso global
- Lista de steps com `StepOutput` para cada um (collapsible)
- `StepDebugger` para execução isolada
- Botão "Voltar para Dashboard"

#### Critérios de conclusão
- [ ] Rota `/jobs/:id` adicionada no router
- [ ] Steps atualizados em tempo real via SSE específico do job
- [ ] SSE desconectado ao sair da view

---

## Tabela de Rastreabilidade

| Task | US | Arquivo Principal | Fase |
|---|---|---|---|
| TASK-001 | US-001 | `requirements.txt` | 1 |
| TASK-002 | US-001 | `app/core/config.py` | 1 |
| TASK-003 | US-001 | `app/core/exceptions.py` | 1 |
| TASK-004 | US-002 | `app/db/database.py` | 1 |
| TASK-005 | US-007 | `app/models/account.py` | 1 |
| TASK-006 | US-031 | `app/models/job.py` | 1 |
| TASK-007 | US-004 | `app/models/settings.py` | 1 |
| TASK-008 | US-002 | `alembic/versions/001_initial.py` | 1 |
| TASK-009 | US-001 | `app/schemas/*.py` | 1 |
| TASK-010 | US-001 | `app/api/deps.py` | 1 |
| TASK-011 | US-001 | `main.py` | 1 |
| TASK-012 | US-004 | `api/routes/settings.py` | 1 |
| TASK-013 | US-003 | `frontend/package.json` | 1 |
| TASK-014 | US-003 | `tailwind.config.js` + shadcn | 1 |
| TASK-015 | US-003 | `src/main.ts` + `App.vue` + `router/index.ts` | 1 |
| TASK-016 | US-001 | `src/services/api.ts` | 1 |
| TASK-017 | US-013 | `services/text_generation/base.py` | 2 |
| TASK-018 | US-013 | `services/text_generation/ollama_generator.py` | 2 |
| TASK-019 | US-002 | `api/routes/ollama.py` | 2 |
| TASK-020 | US-017 | `services/audio/base.py` | 2 |
| TASK-021 | US-017 | `services/audio/edge_tts.py` | 2 |
| TASK-022 | US-021 | `services/video/schemas.py` | 3 |
| TASK-023 | US-021 | `services/video/selector.py` | 3 |
| TASK-024 | US-022 | `services/video/cutter.py` | 3 |
| TASK-025 | US-023 | `services/video/sequencer.py` | 3 |
| TASK-026 | US-024 | `services/video/composer.py` | 3 |
| TASK-027 | US-007 | `app/core/crypto.py` | 4 |
| TASK-028 | US-007 | `services/youtube/auth.py` | 4 |
| TASK-029 | US-007 | `api/routes/accounts.py` | 4 |
| TASK-030 | US-029 | `services/youtube/uploader.py` | 4 |
| TASK-031 | US-027 | `services/metadata/generator.py` | 4 |
| TASK-032 | US-030 | `app/core/scheduler.py` | 4 |
| TASK-033 | US-035 | `app/core/events.py` | 5 |
| TASK-034 | US-036 | `pipeline/steps.py` + `state.py` | 5 |
| TASK-035 | US-031 | `pipeline/runner.py` | 5 |
| TASK-036 | US-031 | `api/routes/jobs.py` | 5 |
| TASK-037 | US-035 | `api/routes/sse.py` | 5 |
| TASK-038 | US-023 | `tests/services/test_sequencer.py` | 5 |
| TASK-039 | US-031 | `tests/api/test_accounts.py` + `test_jobs.py` | 5 |
| TASK-040 | US-033 | `stores/settings.ts` | 6 |
| TASK-041 | US-008 | `stores/accounts.ts` | 6 |
| TASK-042 | US-031 | `stores/jobs.ts` | 6 |
| TASK-043 | US-035 | `services/sse.ts` | 6 |
| TASK-044 | US-033 | `SettingsView.vue` | 6 |
| TASK-045 | US-008 | `AccountCard.vue` + `OAuthButton.vue` | 6 |
| TASK-046 | US-032 | `AccountsView.vue` | 6 |
| TASK-047 | US-031 | `JobCard.vue` + `JobStatus.vue` | 6 |
| TASK-048 | US-031 | `DashboardView.vue` | 6 |
| TASK-049 | US-013 | `TextGenForm.vue` | 6 |
| TASK-050 | US-017 | `AudioForm.vue` | 6 |
| TASK-051 | US-021 | `VideoForm.vue` + `UploadForm.vue` | 6 |
| TASK-052 | US-037 | `StepOutput.vue` + `StepDebugger.vue` | 6 |
| TASK-053 | US-034 | `NewJobView.vue` | 6 |
| TASK-054 | US-037 | `JobDetailView.vue` | 6 |

---

## Resumo por Fase

| Fase | Tasks | Foco |
|---|---|---|
| 1 — Fundação | TASK-001 a TASK-016 | Backend base + DB + Frontend scaffold |
| 2 — IA e Áudio | TASK-017 a TASK-021 | Ollama + edge-tts |
| 3 — Vídeo | TASK-022 a TASK-026 | FFmpeg + algoritmo anti-plágio |
| 4 — YouTube | TASK-027 a TASK-032 | OAuth + upload + agendamento |
| 5 — Orquestração | TASK-033 a TASK-039 | Pipeline runner + SSE + testes |
| 6 — Interface | TASK-040 a TASK-054 | Todas as views e componentes Vue |
| **Total** | **54 tasks** | **Sistema completo** |

---

## Integrações Críticas (pontos de conexão entre módulos)

| De | Para | Como |
|---|---|---|
| `pipeline/runner.py` | `services/text_generation/ollama_generator.py` | Chama `OllamaGenerator.generate()` com config do job |
| `pipeline/runner.py` | `services/audio/edge_tts.py` | Chama `EdgeTTSGenerator.generate()` com o texto gerado |
| `pipeline/runner.py` | `services/video/selector.py` | Passa duração do áudio para `select_videos_for_duration()` |
| `pipeline/runner.py` | `services/video/cutter.py` | Gera `ClipSpec` a partir dos vídeos selecionados |
| `pipeline/runner.py` | `services/video/sequencer.py` | Passa lista de `ClipSpec` para ordenação anti-plágio |
| `pipeline/runner.py` | `services/video/composer.py` | Passa `SequencedClip[]` + `audio_path` para montagem |
| `pipeline/runner.py` | `services/metadata/generator.py` | Passa `narrator_text` para gerar título e descrição |
| `pipeline/runner.py` | `services/youtube/uploader.py` | Passa `video_path` + metadados + conta para upload |
| `pipeline/runner.py` | `app/core/events.py` | Publica eventos SSE a cada mudança de etapa |
| `api/routes/sse.py` | `app/core/events.py` | Subscribe no EventBus para stream ao cliente |
| `stores/jobs.ts` | `services/sse.ts` | SSE client notifica store via callback |
| `stores/jobs.ts` | `src/services/api.ts` | CRUD de jobs via axios |
| `stores/accounts.ts` | `src/services/api.ts` | OAuth URL + CRUD de contas |
| `NewJobView.vue` | `stores/jobs.ts` | Cria job + dispara pipeline |
| `DashboardView.vue` | `stores/jobs.ts` + `services/sse.ts` | Lista jobs + atualizações em tempo real |
