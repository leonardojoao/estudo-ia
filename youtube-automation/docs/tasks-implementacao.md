# Tasks de Implementação — YouTube Automation

> Documento gerado pelo Arquiteto. Cobre 100% dos arquivos da estrutura definida.
> **76 tasks** organizadas em 6 fases. Cada task = 0.5 a 1 dia de trabalho.
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
    # Pipeline
    max_concurrent_jobs: int = 2       # limite de jobs simultâneos no runner
    debug_mode: bool = False            # habilita endpoints de debug em produção
    output_retention_days: int = 7     # dias para manter vídeos finais em /output
    audio_preview_ttl_hours: int = 1   # TTL de arquivos de preview de áudio

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)
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
- [ ] WAL mode habilitado via SQLAlchemy 2.0: `with engine.connect() as conn: conn.execute(text("PRAGMA journal_mode=WAL")); conn.commit()`
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
**Produz para:** TASK-011 (executa migration no lifespan)

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
- **`alembic/env.py` deve importar explicitamente todos os models** para que `alembic revision --autogenerate` detecte as tabelas: `from app.models.account import YouTubeAccount; from app.models.job import ProcessingJob; from app.models.job_step import JobStep; from app.models.settings import SystemSetting`

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
  - Incluir campos opcionais de conteúdo pré-gerado:
    ```python
    # Conteúdo pré-gerado no wizard (pula as etapas correspondentes no pipeline)
    pre_generated_text:              str | None = None
    pre_generated_audio_path:        str | None = None
    pre_generated_audio_duration:    float | None = None
    pre_generated_title:             str | None = None
    pre_generated_description:       str | None = None
    ```

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
```

> **Nota:** O módulo `scheduler.py` (TASK-032) é criado na Fase 4. O lifespan deve importá-lo de forma condicional (`try/import`) ou a inicialização do scheduler deve ser adicionada ao lifespan em uma atualização posterior (ao completar TASK-032).

app = FastAPI(title="YouTube Automation", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, ...)
register_exception_handlers(app)
app.include_router(settings_router, prefix="/api")
app.include_router(accounts_router, prefix="/api")
app.include_router(jobs_router, prefix="/api")
app.include_router(ollama_router, prefix="/api")
app.include_router(sse_router, prefix="/api")
app.include_router(text_generation_router, prefix="/api")  # TASK-059
app.include_router(audio_router, prefix="/api")            # TASK-060

@app.get("/health")
async def health(): return {"status": "ok", "version": "1.0.0"}
```

#### Critérios de conclusão
- [ ] `GET /health` retorna `200 {"status": "ok"}`
- [ ] CORS aceita origens de `settings.cors_origins`
- [ ] Lifespan executa `alembic upgrade head` na inicialização
- [ ] **Lifespan faz recovery de zombie jobs:** na startup, seta `status=error` em todos os jobs com `status=running` (interrompidos por crash/restart)
- [ ] Lifespan verifica se FFmpeg está disponível e loga warning se não estiver
- [ ] Aplicação inicia sem `.env` (usando defaults, exceto `secret_key`)

---

### TASK-012 — Criar api/routes/settings.py

**Módulo:** backend
**Arquivo(s):** `backend/app/api/routes/settings.py`
**US:** US-004, US-005, US-006
**Depende de:** TASK-007, TASK-009, TASK-010
**Produz para:** TASK-044 (SettingsView.vue consome esta API)

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
    "@vue/test-utils": "^2.4", "eslint": "^9", "prettier": "^3.2",
    "@vitejs/plugin-vue-jsx": "^4.0"
  }
}
```

`vite.config.ts`: proxy `/api` → `http://localhost:8000` em dev.

**Arquivos de configuração obrigatórios** (sem eles `npm run lint` e `npm run test` falham):

```javascript
// eslint.config.js
import pluginVue from 'eslint-plugin-vue'
import { defineConfig } from 'eslint/config'
export default defineConfig([
  pluginVue.configs['flat/recommended'],
  { rules: { 'vue/multi-word-component-names': 'off' } }
])
```

```json
// .prettierrc
{ "semi": false, "singleQuote": true, "tabWidth": 2, "trailingComma": "es5" }
```

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
export default defineConfig({
  plugins: [vue()],
  test: { environment: 'jsdom', coverage: { reporter: ['text', 'html'] } }
})
```

```env
# frontend/.env.example
VITE_API_URL=http://localhost:8000
```

#### Critérios de conclusão
- [ ] `npm install` executa sem erros
- [ ] `npm run dev` inicia Vite na porta 5173
- [ ] `npm run build` gera `dist/` sem erros de TypeScript
- [ ] Proxy `/api` redireciona para backend em `localhost:8000`
- [ ] `npm run lint` executa sem erro (requer `eslint.config.js`)
- [ ] `npm run test:run` executa sem erro (requer `vitest.config.ts`)
- [ ] `frontend/.env.example` criado com `VITE_API_URL`

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
export const textGenerationApi = { generate, generateBatch }   // TASK-059
export const audioApi = { generate, getPreviewUrl, getVoices } // TASK-060
export const metadataApi = { generate }                        // TASK-074
export const calendarApi = { getMonth }                        // TASK-070
export const batchApi = { preview, create, get, cancel }       // TASK-068
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
**Produz para:** TASK-031 (metadata/generator.py usa OllamaGenerator), TASK-039 (testes)

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
**US:** US-011 (Selecionar Modelo Ollama), US-010 (Selecionar voz TTS)
**Depende de:** TASK-018, TASK-010
**Produz para:** TASK-049 (TextGenForm carrega modelos), TASK-050 (AudioForm carrega vozes)

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
- [ ] **Retry com exponential backoff:** 3 tentativas (2s, 4s, 8s) antes de falhar com erro definitivo
- [ ] **Timeout de 30s** por requisição ao edge-tts (evita hang indefinido)
- [ ] `httpx.RemoteProtocolError` e HTTP 429 tratados como erros retentáveis (não como falha definitiva)

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
    Lança InsufficientVideosError se não houver vídeos elegíveis.
    """
```

Usar `ffprobe` (via `ffmpeg.probe()`) para ler metadados.

#### Critérios de conclusão
- [x] `scan_videos_folder` retorna lista vazia (não erro) para pasta sem vídeos suportados
- [x] `select_videos_for_duration` usa `random.shuffle()` na lista antes de selecionar
- [x] Duração total dos vídeos selecionados >= `required_duration * 1.10`
- [x] `InsufficientVideosError` com mensagem indicando duração disponível vs necessária

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
- [x] Corte não ultrapassa o final do vídeo (`start + duration <= video.duration`)
- [x] Arquivos de clipe salvos em `output_dir` com nome `clip_{i:04d}_{video_name}.mp4`
- [x] FFmpegError lançado com o stderr do FFmpeg se o corte falhar
- [x] `cut_clip` executado em ProcessPoolExecutor (CPU-bound)

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
- [x] Para N vídeos com distribuição uniforme, nenhum par consecutivo é do mesmo vídeo
- [x] Para 1 vídeo, lança `AntiPlagiarismError` com mensagem orientando adicionar mais vídeos
- [x] Para 2 vídeos com N/2 clipes cada, alterna perfeitamente ABABAB...
- [x] Lista de entrada vazia retorna lista vazia (sem erro)
- [x] Validação final garante a propriedade anti-plágio: usar `raise AntiPlagiarismError(...)`, não `assert` (que pode ser desabilitado com `python -O`)

#### Pontos de atenção
- `heapq` em Python é min-heap — usar valores negativos para simular max-heap
- Manter o `video_id` do último clipe adicionado para evitar consecutivos
- **Nunca usar `assert` para a validação final** — usar `raise AntiPlagiarismError` pois `assert` é removido com `python -O`

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
- [x] Vídeo final tem codec H.264 (vídeo) e AAC (áudio)
- [x] Vídeo final tem duração aproximada do áudio (tolerância 1s)
- [x] 16:9 saída em 1920x1080
- [x] 9:16 saída em 1080x1920
- [x] Arquivos temporários (list.txt, temp_video.mp4) removidos após sucesso
- [x] Executado em ProcessPoolExecutor

---

### TASK-055 — Criar services/video/effects.py (efeito vintage)

**Módulo:** backend
**Arquivo(s):** `backend/app/services/video/effects.py`
**US:** US-039
**Depende de:** TASK-022, TASK-026
**Produz para:** TASK-056, TASK-034 (novo step no pipeline)

#### O que criar

```python
from enum import Enum

class VintageIntensity(str, Enum):
    LIGHT  = "light"
    MEDIUM = "medium"
    STRONG = "strong"

# Parâmetros por intensidade
INTENSITY_PARAMS = {
    VintageIntensity.LIGHT:  {"noise": 8,  "saturation": 0.85, "vignette": "PI/6", "contrast": 0.97},
    VintageIntensity.MEDIUM: {"noise": 18, "saturation": 0.65, "vignette": "PI/4", "contrast": 0.93},
    VintageIntensity.STRONG: {"noise": 30, "saturation": 0.40, "vignette": "PI/3", "contrast": 0.88},
}

async def apply_vintage_effect(
    input_path: str,
    output_path: str,
    intensity: VintageIntensity = VintageIntensity.MEDIUM,
) -> VideoCompositionOutput:
    """
    Aplica efeito de vídeo antigo via filtergraph do FFmpeg.

    Filtros encadeados (ordem importa):
    1. curves=vintage         → tom sépia/quente (filtro nativo do FFmpeg)
    2. noise=alls={n}:allf=t+u → granulação de filme (ruído temporal + uniforme)
    3. vignette={angle}       → vinheta (escurecimento das bordas)
    4. eq=saturation={s}:contrast={c} → dessaturação e contraste reduzido

    Comando FFmpeg resultante (exemplo intensidade MEDIUM):
      ffmpeg -i input.mp4 -vf
        "curves=vintage,
         noise=alls=18:allf=t+u,
         vignette=PI/4,
         eq=saturation=0.65:contrast=0.93"
        -c:v libx264 -c:a copy -crf 18 output.mp4

    Executa em ProcessPoolExecutor (CPU-bound).
    Remove input_path após sucesso se for arquivo temporário.
    Retorna VideoCompositionOutput com metadados do arquivo de saída.
    """
```

#### Critérios de conclusão
- [ ] `apply_vintage_effect` gera arquivo MP4 com efeito visível nos 3 níveis
- [ ] Áudio preservado sem alteração (`-c:a copy`)
- [ ] Codec de saída: H.264 com CRF 18 (qualidade alta, sem perdas perceptíveis)
- [ ] Executado em ProcessPoolExecutor (não bloqueia event loop)
- [ ] `FFmpegError` lançado com stderr se o comando falhar
- [ ] Arquivo de saída com sufixo `_vintage` no nome para identificação
- [ ] `VideoCompositionOutput` retornado com metadados atualizados do arquivo final

#### Pontos de atenção
- `curves=vintage` é um preset nativo do FFmpeg — não requer parâmetros extras, mas exige FFmpeg compilado com `--enable-libfreetype` (padrão nas distribuições comuns)
- `noise=allf=t+u` combina ruído temporal (`t`) e uniforme (`u`) — mais realista que apenas `u`
- A ordem dos filtros importa: sépia → ruído → vinheta → eq (do mais global ao mais local)
- `vignette` aceita ângulo em radianos — `PI/4 ≈ 45°` é o ponto visual ideal para "médio"
- Para o nível **Forte**, considerar adicionar `hue=s=0` (preto e branco) antes do `curves=vintage` para efeito mais dramático

---

### TASK-056 — Atualizar pipeline/steps.py com etapa VINTAGE_EFFECT

**Módulo:** backend
**Arquivo(s):** `backend/app/pipeline/steps.py`, `backend/app/pipeline/state.py`, `backend/app/pipeline/runner.py`
**US:** US-039
**Depende de:** TASK-034, TASK-055
**Produz para:** TASK-035 (runner precisa tratar etapa condicional)

#### O que criar

**steps.py** — adicionar ao enum e ao STEP_METADATA:
```python
class PipelineStep(str, Enum):
    # ... etapas existentes ...
    VINTAGE_EFFECT = "vintage_effect"   # etapa opcional — só executa se habilitada no config

STEP_METADATA = {
    # ... existentes ...
    PipelineStep.VINTAGE_EFFECT: StepMeta(
        name="Efeito Vintage",
        weight=8,          # reduz o peso das outras etapas proporcionalmente
        optional=True,     # flag que indica etapa condicional
    ),
}
```

**state.py** — adicionar campo ao `JobState`:
```python
class JobState(BaseModel):
    # ... campos existentes ...
    vintage_video_path: str | None = None   # preenchido se efeito foi aplicado
```

**runner.py** — tratar etapa opcional:
```python
# Na execução do pipeline, antes de METADATA_GENERATION:
if job_config.vintage_effect_enabled:
    # executa VINTAGE_EFFECT normalmente
    state.vintage_video_path = await run_vintage_step(state, settings)
    # atualiza composed_video_path para apontar ao vídeo com efeito
    state.composed_video_path = state.vintage_video_path
# else: pula a etapa, composed_video_path já aponta ao vídeo sem efeito
```

**schemas/job.py** — adicionar ao `JobConfig`:
```python
class JobConfig(BaseModel):
    # ... campos existentes ...
    vintage_effect_enabled: bool = False
    vintage_intensity: VintageIntensity = VintageIntensity.MEDIUM
```

#### Critérios de conclusão
- [ ] `PipelineStep.VINTAGE_EFFECT` adicionado ao enum
- [ ] `STEP_METADATA` atualizado com `optional=True` para o novo step
- [ ] `JobState` tem campo `vintage_video_path` e `temp_paths: list[str]` (para cleanup no finally)
- [ ] `runner.py` verifica `job_config.vintage_effect_enabled` antes de executar a etapa
- [ ] Se desabilitado, etapa aparece como `skipped` no `job_steps` (não `pending`)
- [ ] `composed_video_path` atualizado para o vídeo com efeito quando habilitado
- [ ] **Progresso com optional steps:** o cálculo de progresso filtra steps `skipped` da soma de pesos — a barra sempre chega a 100% independentemente do vintage estar ativo ou não

---

### TASK-057 — Atualizar VideoForm.vue com toggle de efeito vintage

**Módulo:** frontend
**Arquivo(s):** `frontend/src/components/forms/VideoForm.vue`
**US:** US-039
**Depende de:** TASK-051
**Produz para:** TASK-053 (NewJobView lê o config do form)

#### O que criar

Adicionar seção "Efeito Visual" no `VideoForm.vue` (abaixo da seleção de dimensão):

```vue
<!-- Seção: Efeito Visual -->
<div class="space-y-3">
  <Label>Efeito Visual</Label>

  <!-- Toggle principal -->
  <div class="flex items-center gap-3">
    <Switch v-model="vintageEnabled" id="vintage-toggle" />
    <Label for="vintage-toggle">Efeito de Vídeo Antigo (Vintage)</Label>
  </div>

  <!-- Seletor de intensidade — visível apenas quando toggle ativo -->
  <div v-if="vintageEnabled" class="ml-7 space-y-2">
    <RadioGroup v-model="vintageIntensity">
      <RadioGroupItem value="light">
        <span class="font-medium">Leve</span>
        <span class="text-muted">— Tom levemente sépia, granulação sutil, vinheta discreta</span>
      </RadioGroupItem>
      <RadioGroupItem value="medium">
        <span class="font-medium">Médio</span>
        <span class="text-muted">— Sépia pronunciado, granulação de filme, vinheta visível</span>
      </RadioGroupItem>
      <RadioGroupItem value="strong">
        <span class="font-medium">Forte</span>
        <span class="text-muted">— Preto e branco envelhecido, granulação intensa, bordas escuras</span>
      </RadioGroupItem>
    </RadioGroup>

    <!-- Card explicativo dos efeitos aplicados -->
    <Card class="p-3 bg-muted/40">
      <p class="text-sm text-muted-foreground">
        <strong>Filtros aplicados:</strong>
        Tom sépia/quente · Granulação de filme · Vinheta nas bordas · Dessaturação
      </p>
    </Card>
  </div>
</div>
```

O componente expõe `vintageEnabled` e `vintageIntensity` via `defineExpose` ou como parte do objeto de configuração emitido para o `NewJobView`.

#### Critérios de conclusão
- [ ] Toggle visível na seção "Efeito Visual" do VideoForm
- [ ] Seletor de intensidade aparece apenas quando toggle está ativo
- [ ] Cada intensidade tem descrição textual clara do que muda
- [ ] Card explicativo descreve os filtros aplicados
- [ ] Valores `vintageEnabled` e `vintageIntensity` incluídos no `JobConfig` ao criar o processamento
- [ ] Estado persistido no Pinia ao navegar entre steps do wizard

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
- [x] `encrypt(decrypt(data))` == `data` (round-trip)
- [x] `SECRET_KEY` com menos de 32 bytes é derivado via PBKDF2 para gerar chave Fernet válida
- [x] `decrypt` lança erro descritivo se dados corrompidos (não `InvalidToken` genérico)

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
- **CSRF state storage:** gerar um UUID como `state` ao criar a URL OAuth → salvar em nova tabela `oauth_states(state_token TEXT, expires_at DATETIME)` com TTL de 10 min → validar e deletar no callback. Sem esse storage, a validação CSRF não pode ser implementada
- **SECRET_KEY rotation:** se a chave mudar, `decrypt()` lança `InvalidToken`. Tratar separadamente de token OAuth inválido → retornar status `"credentials_corrupted"` → UI exibe "Reconecte a conta" (diferente de "Token expirado")
- **`frontend_url` configurável:** o backend precisa de `settings.frontend_url` para redirecionar após OAuth. Adicionar ao `Settings`: `frontend_url: str = "http://localhost:5173"`. O callback usa `f"{settings.frontend_url}/accounts?connected=true"` — nunca hardcode

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
- [ ] **`quotaExceeded` tratado especificamente:** retornar mensagem orientada ao usuário com horário de renovação da quota (meia-noite PT) e sugerir reagendamento automático para 01h00 PT do dia seguinte
- [ ] **`services/youtube/schemas.py` criado:** `UploadInput(video_path, title, description, tags, category_id, privacy, publish_at)`, `UploadOutput(video_id, youtube_url)`, `ScheduleUploadInput`

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
- [ ] **Job de limpeza de audio preview:** job periódico a cada 1h que deleta arquivos em `/tmp/audio_preview/` com mais de `settings.audio_preview_ttl_hours` horas
- [ ] **Job de limpeza de oauth_states:** job periódico a cada 30min que deleta registros com `expires_at < now()` da tabela `oauth_states`
- [ ] **Job de retenção de outputs:** job diário que deleta arquivos em `/app/output/` com mais de `settings.output_retention_days` dias (apenas se já publicados no YouTube)

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
**Depende de:** TASK-017 (text_generation/schemas.py), TASK-020 (audio/schemas.py), TASK-022 (video/schemas.py)
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
**Depende de:** TASK-021, TASK-023, TASK-024, TASK-025, TASK-026, TASK-030, TASK-031, TASK-032, TASK-033, TASK-034
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
- [ ] Limpeza de temporários no `finally`: runner registra todos os paths temporários criados no `JobState.temp_paths` e executa `shutil.rmtree` no bloco `finally`, independentemente de sucesso ou falha
- [ ] Verificação de disco antes de iniciar: estimar espaço necessário (duração_audio × bitrate_estimado × 3) e verificar disponível via `shutil.disk_usage`. Falhar imediatamente com mensagem clara se insuficiente
- [ ] Progresso calculado dinamicamente: filtrar steps `skipped` antes de somar pesos — garante que barra sempre chegue a 100% independentemente de steps opcionais (vintage) estarem ativados ou não
- [ ] Concorrência limitada: máximo `settings.max_concurrent_jobs` (default: 2) jobs em paralelo. Job aguarda em fila se limite atingido
- [ ] **Conteúdo pré-gerado:** runner verifica `job_config.pre_generated_text` — se preenchido, pula `text_generation` e usa o valor diretamente no `JobState`. Mesmo para `pre_generated_audio_path` (pula `audio_generation` + `audio_verification`), `pre_generated_title` e `pre_generated_description` (pula geração de metadados)
- [ ] **`run_single_step` com pré-condições:** antes de executar etapa isolada, verificar `STEP_PREREQUISITES` — se inputs obrigatórios ausentes do `JobState`, retornar HTTP 422 com mensagem: `"Esta etapa requer: audio_path (execute audio_generation primeiro)"`
- [ ] **APScheduler + sessão:** função agendada recebe apenas `job_id: int` e cria sua própria sessão: `async with SessionLocal() as db: await run_pipeline(job_id, db, get_settings())`

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
**Depende de:** TASK-016
**Produz para:** TASK-047, TASK-048, TASK-052, TASK-053, TASK-054

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
- **Multi-select de contas** (checkboxes, não dropdown) — `job_accounts` é M2M, permite upload simultâneo para múltiplos canais
- Pelo menos uma conta deve estar selecionada para avançar
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
- [ ] Step 5 (Metadados) dispara `POST /api/jobs/{id}/steps/metadata_generation` para gerar título e descrição via IA (usando o endpoint de execução isolada de etapa definido na TASK-036)
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
| TASK-055 | US-039 | `services/video/effects.py` | 3 |
| TASK-056 | US-039 | `pipeline/steps.py` + `state.py` + `runner.py` | 5 |
| TASK-057 | US-039 | `VideoForm.vue` (atualização) | 6 |
| TASK-058 | US-029 | `services/youtube/uploader.py` (tags) | 4 |
| TASK-059 | US-013 | `api/routes/text_generation.py` (preview wizard) | 2 |
| TASK-060 | US-017 | `api/routes/audio.py` (preview wizard) | 2 |
| TASK-061 | US-007 | `app/db/migrations/002_oauth_states.py` | 4 |
| TASK-062 | US-001 | `src/types/index.ts` | 1 |
| TASK-063 | US-001 | `app/core/utils.py` | 1 |
| TASK-064 | US-031 | `stores/__tests__/*.test.ts` | 6 |

---

## Resumo por Fase

| Fase | Tasks | Foco |
|---|---|---|
| 1 — Fundação | TASK-001 a TASK-016 + TASK-062 + TASK-063 | Backend base + DB + Frontend scaffold + tipos TS + utils |
| 2 — IA e Áudio | TASK-017 a TASK-021 + TASK-059 + TASK-060 | Ollama + edge-tts + endpoints de preview |
| 3 — Vídeo | TASK-022 a TASK-026 + TASK-055 | FFmpeg + algoritmo anti-plágio + efeito vintage |
| 4 — YouTube | TASK-027 a TASK-032 + TASK-058 + TASK-061 | OAuth + upload + agendamento + tags + CSRF state |
| 5 — Orquestração | TASK-033 a TASK-039 + TASK-056 | Pipeline runner + SSE + testes + etapa vintage |
| 6 — Interface | TASK-040 a TASK-054 + TASK-057 + TASK-064 | Views + componentes + toggle vintage + testes frontend |
| **Total** | **65 tasks** | **Sistema completo** |

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
| `pipeline/runner.py` | `services/video/effects.py` | Executa `apply_vintage_effect()` condicionalmente (se `job_config.vintage_effect_enabled`) |
| `services/video/effects.py` | `pipeline/state.py` | Preenche `state.vintage_video_path` e atualiza `state.composed_video_path` |
| `pipeline/runner.py` | `app/core/events.py` | Publica eventos SSE a cada mudança de etapa |
| `api/routes/sse.py` | `app/core/events.py` | Subscribe no EventBus para stream ao cliente |
| `stores/jobs.ts` | `services/sse.ts` | SSE client notifica store via callback |
| `stores/jobs.ts` | `src/services/api.ts` | CRUD de jobs via axios |
| `stores/accounts.ts` | `src/services/api.ts` | OAuth URL + CRUD de contas |
| `NewJobView.vue` | `stores/jobs.ts` | Cria job + dispara pipeline |
| `DashboardView.vue` | `stores/jobs.ts` + `services/sse.ts` | Lista jobs + atualizações em tempo real |

---

## Tasks Adicionadas pela Análise de Escopo

---

### TASK-058 — Adicionar tags/keywords ao upload do YouTube

**Módulo:** backend
**Arquivo(s):** `backend/app/services/youtube/uploader.py`, `backend/app/services/metadata/generator.py`
**US:** US-029
**Depende de:** TASK-030, TASK-031
**Produz para:** TASK-036 (pipeline usa)

#### O que criar
- Adicionar parâmetro `tags: list[str]` ao `upload_video()`
- Em `metadata/generator.py`, adicionar `generate_tags(narrator_text, ollama_url, model) -> list[str]`: gera lista de 5-10 palavras-chave via Ollama
- Tags incluídas no payload da YouTube Data API (`snippet.tags`)
- `UploadForm.vue`: campo editável de tags (lista de badges, adicionar/remover), pré-preenchido pela IA

#### Critérios de conclusão
- [ ] `generate_tags()` retorna lista de 5-10 strings (sem `#`, sem espaços duplos)
- [ ] Cada tag ≤ 30 caracteres (limite da API)
- [ ] Tags enviadas no upload via `snippet.tags`
- [ ] `UploadForm.vue` exibe tags como badges editáveis

#### Pontos de atenção
- YouTube API limita tags a 500 caracteres total (soma de todas as tags)
- Tags com espaços são válidas mas devem ser enviadas sem aspas na API

---

### TASK-059 — Criar api/routes/text_generation.py (preview no wizard)

**Módulo:** backend
**Arquivo(s):** `backend/app/api/routes/text_generation.py`
**US:** US-013, US-014
**Depende de:** TASK-018
**Produz para:** TASK-049 (TextGenForm chama este endpoint)

#### O que criar
O wizard precisa gerar e exibir texto ANTES de criar o job. Sem este endpoint, TextGenForm.vue não tem como chamar o Ollama.

```
POST /api/text-generation/generate
  body: { prompt, model, max_tokens, temperature }
  response: { text, model, duration_ms }

POST /api/text-generation/generate-batch
  body: { prompt, model, count, max_tokens }
  response: { texts: [{ text, index, error? }], total, failed }
```

#### Critérios de conclusão
- [ ] `POST /api/text-generation/generate` retorna texto ou erro do Ollama
- [ ] `POST /api/text-generation/generate-batch` executa N gerações com streaming de progresso (SSE ou resposta ao final com array)
- [ ] Ambos tratam `OllamaUnavailableError` com HTTP 503 e mensagem descritiva
- [ ] Não persiste nada no banco — apenas geração sob demanda

---

### TASK-060 — Criar api/routes/audio.py (preview no wizard)

**Módulo:** backend
**Arquivo(s):** `backend/app/api/routes/audio.py`
**US:** US-017, US-018
**Depende de:** TASK-021
**Produz para:** TASK-050 (AudioForm chama este endpoint)

#### O que criar
O wizard precisa gerar e reproduzir áudio ANTES de criar o job. Sem este endpoint, AudioForm.vue não tem como gerar preview.

```
POST /api/audio/generate
  body: { text, voice, target_duration_seconds, rate }
  response: { file_url, actual_duration_seconds, within_tolerance }

GET /api/audio/preview/{filename}
  response: streaming do arquivo MP3 (para o player HTML5)

GET /api/audio/voices
  response: lista de vozes disponíveis
```

Os arquivos de preview ficam em `/tmp/audio_preview/` com TTL de 1h (limpeza periódica via APScheduler).

#### Critérios de conclusão
- [ ] `POST /api/audio/generate` gera MP3 e retorna URL de preview
- [ ] `GET /api/audio/preview/{filename}` serve o arquivo com `Content-Type: audio/mpeg`
- [ ] Arquivos de preview limpos automaticamente após 1h
- [ ] `GET /api/audio/voices` retorna lista de vozes (pode reusar lógica de TASK-019)

---

### TASK-061 — Criar migration 002: tabela oauth_states (CSRF)

**Módulo:** backend
**Arquivo(s):** `backend/alembic/versions/002_oauth_states.py`
**US:** US-007
**Depende de:** TASK-008
**Produz para:** TASK-028 (auth.py usa para validar CSRF)

#### O que criar
```sql
CREATE TABLE oauth_states (
    state_token TEXT PRIMARY KEY,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at  DATETIME NOT NULL  -- created_at + 10 minutos
);
```

Funções em `services/youtube/auth.py`:
- `create_oauth_state(db) -> str`: gera UUID, insere no banco, retorna o UUID
- `validate_oauth_state(db, state) -> bool`: verifica existência e expiração, deleta após validação
- Cleanup periódico de states expirados via APScheduler (a cada 30min)

#### Critérios de conclusão
- [ ] `alembic upgrade head` cria a tabela
- [ ] `create_oauth_state` insere state com `expires_at = now() + 10min`
- [ ] `validate_oauth_state` retorna `False` se não encontrado ou expirado (não levanta exceção)
- [ ] State deletado após validação bem-sucedida (uso único)
- [ ] Cleanup periódico de states expirados via APScheduler

---

### TASK-062 — Criar src/types/index.ts (tipos TypeScript compartilhados)

**Módulo:** frontend
**Arquivo(s):** `frontend/src/types/index.ts`
**US:** US-001
**Depende de:** TASK-009 (schemas do backend como referência)
**Produz para:** todas as stores e componentes Vue

#### O que criar
Arquivo centralizado com todas as interfaces TypeScript usadas no frontend. Deve espelhar os Pydantic schemas do backend:

```typescript
// Contas
export interface Account {
  id: number
  name: string
  channel_id: string
  email: string | null
  avatar_url: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

// Jobs
export type JobStatus = 'pending' | 'running' | 'completed' | 'error' | 'cancelled' | 'scheduled'
export type StepStatus = 'pending' | 'running' | 'completed' | 'error' | 'skipped'

export interface JobStep {
  id: number
  job_id: number
  step_name: string
  status: StepStatus
  input: Record<string, unknown> | null
  output: Record<string, unknown> | null
  log: string | null
  duration_ms: number | null
  started_at: string | null
  completed_at: string | null
}

export interface Job {
  id: number
  name: string
  status: JobStatus
  current_step: string | null
  progress: number
  output_video: string | null
  youtube_urls: Record<string, string> | null
  error_message: string | null
  scheduled_at: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
  steps?: JobStep[]
  accounts?: Account[]
}

// Configuração do Job
export type VintageIntensity = 'light' | 'medium' | 'strong'

export interface JobConfig {
  name: string
  account_ids: number[]
  // Texto
  text_mode: 'ai' | 'manual'
  text_prompt?: string
  text_model?: string
  narrator_text?: string
  text_count: number
  // Áudio
  tts_voice: string
  target_duration_seconds: number
  // Vídeo
  dimension: '16:9' | '9:16'
  crop_for_vertical: boolean
  vintage_effect_enabled: boolean
  vintage_intensity: VintageIntensity
  // Metadados
  title_prompt?: string
  description_prompt?: string
  video_title?: string
  video_description?: string
  video_tags: string[]
  // Upload
  privacy: 'public' | 'private' | 'unlisted'
  publish_at?: string | null
}

// SSE
export interface SSEJobEvent {
  job_id: number
  status: JobStatus
  current_step: string | null
  progress: number
  step_log: string | null
}

// Configurações
export interface SystemSettings {
  ollama_url: string
  ollama_model: string
  videos_folder: string
  tts_voice: string
  default_dimension: string
  clip_min_duration: string
  clip_max_duration: string
}

// Ollama
export interface OllamaModel {
  name: string
  size: number
  modified_at: string
}

export interface TTSVoice {
  name: string
  short_name: string
  gender: string
  locale: string
}
```

#### Critérios de conclusão
- [ ] Todos os tipos usados em stores (`jobs.ts`, `accounts.ts`, `settings.ts`) importados deste arquivo
- [ ] `JobConfig` corresponde exatamente ao schema Pydantic do backend
- [ ] `SSEJobEvent` corresponde ao formato de evento SSE do backend
- [ ] Sem redefinição de tipos em arquivos individuais (DRY)

---

### TASK-063 — Criar app/core/utils.py (funções utilitárias)

**Módulo:** backend
**Arquivo(s):** `backend/app/core/utils.py`
**US:** US-001
**Depende de:** TASK-002
**Produz para:** TASK-035 (runner usa check de disco), TASK-024 (cutter usa sanitize_filename)

#### O que criar
```python
import shutil
import os
from pathlib import Path

def check_disk_space(path: str, required_bytes: int) -> tuple[bool, int]:
    """
    Verifica se há espaço suficiente no disco.
    Retorna (tem_espaço, bytes_disponíveis).
    """
    usage = shutil.disk_usage(path)
    return usage.free >= required_bytes, usage.free

def estimate_video_size_bytes(duration_seconds: float, bitrate_kbps: int = 2000) -> int:
    """Estima tamanho do vídeo final em bytes baseado na duração e bitrate."""
    return int(duration_seconds * bitrate_kbps * 1000 / 8)

def sanitize_filename(filename: str) -> str:
    """
    Remove ou substitui caracteres inválidos em nomes de arquivo.
    Previne path traversal: remove '../', '/', '\\', etc.
    """
    safe = Path(filename).name  # remove path components
    safe = "".join(c if c.isalnum() or c in "._- " else "_" for c in safe)
    return safe[:200]  # limita comprimento

def ensure_dir(path: str) -> None:
    """Cria diretório e pais se não existirem."""
    Path(path).mkdir(parents=True, exist_ok=True)
```

#### Critérios de conclusão
- [ ] `check_disk_space` funciona em Linux e macOS
- [ ] `sanitize_filename("../../etc/passwd")` retorna `"..etc_passwd"` (sem path traversal)
- [ ] `estimate_video_size_bytes(60)` retorna ~15MB (60s × 2Mbps)
- [ ] Funções documentadas com docstrings

---

### TASK-064 — Criar testes de frontend (stores Pinia + componentes)

**Módulo:** frontend
**Arquivo(s):** `frontend/src/stores/__tests__/jobs.test.ts`, `frontend/src/stores/__tests__/accounts.test.ts`, `frontend/src/components/__tests__/JobCard.test.ts`
**US:** US-031, US-008
**Depende de:** TASK-042, TASK-041, TASK-047
**Produz para:** CI/CD

#### O que criar

**Setup de testes (`src/test-setup.ts`):**
```typescript
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach } from 'vitest'

beforeEach(() => {
  setActivePinia(createPinia())
})
```

**`stores/__tests__/jobs.test.ts`:**
- `loadJobs()` popula `jobs` com dados mockados da API
- `updateJobFromSSE({ job_id: 1, status: 'completed', progress: 100 })` atualiza o job correto
- `filteredJobs` retorna apenas jobs com o status do filtro
- `createJob()` chama `POST /api/jobs` e adiciona à lista

**`stores/__tests__/accounts.test.ts`:**
- `loadAccounts()` popula lista de contas
- `activeAccounts` retorna apenas contas com `is_active = true`
- `removeAccount(1)` remove o item correto da lista

**`components/__tests__/JobCard.test.ts`:**
- Renderiza com status `running` mostrando barra de progresso animada
- Renderiza com status `completed` mostrando link do YouTube
- Botão "Ver detalhes" dispara evento de navegação

#### Critérios de conclusão
- [ ] `npm run test:run` passa 100% para todos os testes de frontend
- [ ] Mocks de API implementados com `vi.mock('../services/api')`
- [ ] Sem chamadas reais à API nos testes (tudo mockado)
- [ ] Cobertura das stores ≥ 80%

---

## Funcionalidade: Agendamento em Lote + Calendário de Publicações

---

### TASK-065 — Criar migration 003: tabela job_batches e campo batch_id

**Módulo:** backend
**Arquivo(s):** `backend/alembic/versions/003_job_batches.py`, `backend/app/models/job_batch.py`
**US:** US-040
**Depende de:** TASK-008
**Produz para:** TASK-066, TASK-067, TASK-068

#### O que criar

**Model `JobBatch` (`app/models/job_batch.py`):**
```python
class JobBatch(Base):
    __tablename__ = "job_batches"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    name       = Column(Text, nullable=False)
    total_jobs = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    jobs       = relationship("ProcessingJob", back_populates="batch")
```

**Atualizar `ProcessingJob` (`app/models/job.py`):**
```python
batch_id = Column(Integer, ForeignKey("job_batches.id"), nullable=True, index=True)
batch    = relationship("JobBatch", back_populates="jobs")
```

**Migration `003_job_batches.py`:**
```sql
CREATE TABLE job_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    total_jobs INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE processing_jobs ADD COLUMN batch_id INTEGER REFERENCES job_batches(id);
CREATE INDEX idx_jobs_batch_id ON processing_jobs(batch_id);
```

#### Critérios de conclusão
- [ ] `alembic upgrade head` aplica a migration sem erro
- [ ] `alembic downgrade` reverte (drop index → drop column → drop table)
- [ ] `ProcessingJob.batch` relationship funciona (eager ou lazy)
- [ ] `batch_id = NULL` para jobs individuais (não obrigatório)

#### Pontos de atenção
- SQLite não suporta `ADD COLUMN ... REFERENCES` diretamente — usar `op.batch_alter_table` com Alembic `render_as_batch=True`

---

### TASK-066 — Criar schemas de batch e calendário

**Módulo:** backend
**Arquivo(s):** `backend/app/schemas/batch.py`
**US:** US-040, US-041
**Depende de:** TASK-009, TASK-065
**Produz para:** TASK-067, TASK-068, TASK-069

#### O que criar

```python
class BatchScheduleConfig(BaseModel):
    start_date:   date
    days_of_week: list[int]      # 0=Seg, 6=Dom; Field(min_length=1)
    window_start: time           # ex: time(9, 0)
    window_end:   time           # ex: time(21, 0)
    timezone:     str = "UTC"

    @model_validator(mode='after')
    def validate_window(self):
        if self.window_end <= self.window_start:
            raise ValueError("window_end deve ser após window_start")
        if not all(0 <= d <= 6 for d in self.days_of_week):
            raise ValueError("dias devem estar entre 0 (Seg) e 6 (Dom)")
        return self

class BatchJobCreate(BaseModel):
    name:         str
    count:        int = Field(ge=1, le=50)
    account_ids:  list[int] = Field(min_length=1)
    job_template: JobConfig
    schedule:     BatchScheduleConfig

class BatchPreview(BaseModel):
    slots: list[dict]   # [{ "index": 1, "scheduled_at": "2024-01-15T09:00:00Z" }]
    total_days: int
    first_date: date
    last_date:  date

class BatchDetail(BaseModel):
    id:         int
    name:       str
    total_jobs: int
    created_at: datetime
    jobs:       list[JobResponse]

class CalendarPublication(BaseModel):
    job_id:          int
    job_name:        str
    scheduled_at:    datetime
    status:          str
    account_id:      int
    account_name:    str
    account_avatar:  str | None
    youtube_url:     str | None
    error_message:   str | None

class CalendarDay(BaseModel):
    date:         date
    publications: list[CalendarPublication]

class CalendarResponse(BaseModel):
    days:               list[CalendarDay]
    total_publications: int
```

#### Critérios de conclusão
- [ ] `BatchScheduleConfig` rejeita janela inválida (end <= start) com mensagem descritiva
- [ ] `BatchScheduleConfig` rejeita `count > 50`
- [ ] `CalendarDay` com `publications=[]` para dias sem publicações (não omitir dias)
- [ ] `CalendarResponse` cobre exatamente o intervalo `start_date..end_date`

---

### TASK-067 — Criar services/scheduler/distributor.py (algoritmo de slots)

**Módulo:** backend
**Arquivo(s):** `backend/app/services/scheduler/distributor.py`
**US:** US-040
**Depende de:** TASK-066
**Produz para:** TASK-068

#### O que criar

```python
from datetime import date, time, datetime, timedelta
from zoneinfo import ZoneInfo

def distribute_slots(
    count: int,
    start_date: date,
    days_of_week: list[int],   # 0=Segunda, 6=Domingo (Python weekday())
    window_start: time,
    window_end: time,
    timezone: str = "UTC",
) -> list[datetime]:
    """
    Distribui `count` publicações em slots dentro da janela configurada.

    ESTRATÉGIA:
    1. Iterar dias a partir de start_date, incluir apenas os em days_of_week
    2. Distribuir vídeos entre os dias de forma equilibrada:
       - videos_per_day[i] = count // total_days + (1 if i < count % total_days else 0)
    3. Para cada dia com N vídeos:
       - Se N == 1: horário = window_start
       - Se N > 1: intervalo = (window_end - window_start) / (N - 1)
                   horários: window_start, +intervalo, ..., window_end
    4. Converter cada datetime para UTC via ZoneInfo
    5. Retornar lista ordenada cronologicamente

    CASOS ESPECIAIS:
    - Se slots disponíveis < count: continuar gerando mais dias até cobrir count
    - Garantir que nenhum slot é no passado (validar no endpoint, não aqui)
    """

def preview_slots(config: BatchScheduleConfig, count: int) -> BatchPreview:
    """Chama distribute_slots e monta BatchPreview para exibição no frontend."""

def validate_slots_available(config: BatchScheduleConfig, count: int) -> tuple[bool, str]:
    """
    Verifica se a configuração é viável para o count desejado.
    Retorna (válido, mensagem_de_erro).
    """
```

#### Critérios de conclusão
- [ ] `distribute_slots(10, ..., [0,1,2,3,4], ...)` distribui em Mon-Fri (2 vídeos nos primeiros 5 dias)
- [ ] `distribute_slots(7, ..., [0,2,4], ...)` distribui em Seg/Qua/Sex: [3, 2, 2]
- [ ] Horários dentro da janela nunca ultrapassam `window_end`
- [ ] Slots convertidos corretamente para UTC (verificar DST se timezone com horário de verão)
- [ ] `validate_slots_available` retorna erro descritivo com sugestões quando inviável

#### Pontos de atenção
- Usar `zoneinfo.ZoneInfo` (Python 3.9+) em vez de `pytz` — sem dependência extra
- Se `window_start == window_end`, todos os slots no mesmo horário — não é erro, mas deve ser documentado

---

### TASK-068 — Atualizar api/routes/jobs.py com endpoints de batch

**Módulo:** backend
**Arquivo(s):** `backend/app/api/routes/jobs.py` (atualização)
**US:** US-040
**Depende de:** TASK-036, TASK-066, TASK-067
**Produz para:** TASK-071 (frontend consome)

#### O que criar

Adicionar aos endpoints existentes de jobs:

```
POST /api/jobs/batch
  body: BatchJobCreate
  response: { batch_id, jobs_created: N, schedule: [{ job_id, scheduled_at }] }
  → 1. Valida slots com validate_slots_available
  → 2. Chama distribute_slots → lista de datetimes
  → 3. Cria JobBatch no banco
  → 4. Para cada slot: cria ProcessingJob com scheduled_at e batch_id
  → 5. Cada job inicia pipeline em background com APScheduler
  → 6. Retorna batch criado

GET /api/jobs/batch/{batch_id}
  → retorna BatchDetail (info do lote + lista de jobs com status atual)

DELETE /api/jobs/batch/{batch_id}
  → cancela todos os jobs do lote que ainda não iniciaram (status=pending|scheduled)

POST /api/jobs/batch/preview
  body: { count, schedule: BatchScheduleConfig }
  response: BatchPreview
  → retorna a lista de slots sem criar nada (para preview antes de confirmar)
```

#### Critérios de conclusão
- [ ] `POST /api/jobs/batch` cria exatamente `count` jobs vinculados ao mesmo `batch_id`
- [ ] `POST /api/jobs/batch/preview` retorna slots sem persistir no banco
- [ ] `DELETE /api/jobs/batch/{id}` cancela apenas jobs `pending` ou `scheduled` (não interrompe jobs `running`)
- [ ] Jobs do lote agendados via APScheduler com `scheduled_at` correto em UTC
- [ ] Endpoint retorna 422 com erro descritivo se slots insuficientes

---

### TASK-069 — Criar api/routes/calendar.py

**Módulo:** backend
**Arquivo(s):** `backend/app/api/routes/calendar.py`
**US:** US-041, US-042
**Depende de:** TASK-066, TASK-010
**Produz para:** TASK-072 (frontend consome)

#### O que criar

```
GET /api/calendar?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&account_ids=1,2,3
```

Lógica:
1. Query em `processing_jobs` onde `scheduled_at BETWEEN start_date AND end_date`
2. Filtrar por `account_ids` se fornecido (via `job_accounts`)
3. Agrupar por dia: `{ "2024-01-15": [pub1, pub2, ...] }`
4. Incluir dias sem publicações como lista vazia (para o calendário renderizar todos os dias do mês)
5. Montar `CalendarResponse`

Constraints:
- Intervalo máximo: 31 dias (proteger contra queries pesadas)
- `account_ids` como query param: `?account_ids=1&account_ids=2` ou `?account_ids=1,2`

Registrar no `main.py`:
```python
app.include_router(calendar_router, prefix="/api")
```

#### Critérios de conclusão
- [ ] Retorna todos os dias do intervalo, mesmo sem publicações
- [ ] `account_ids` vazio = retorna todos os canais
- [ ] Intervalo > 31 dias retorna HTTP 422 com mensagem descritiva
- [ ] `youtube_url` preenchido apenas quando `status = completed` E `youtube_urls` no job
- [ ] Performance: query com JOIN otimizado (não N+1)
- [ ] **Jobs "publicar agora" incluídos:** query usa `COALESCE(scheduled_at, completed_at)` como campo de data. Jobs com `scheduled_at = NULL` e `status = completed` aparecem na data de `completed_at`. Jobs com `scheduled_at = NULL` e `status != completed` aparecem na data de `created_at` (agendamento implícito)

---

### TASK-070 — Criar stores/calendar.ts (Pinia)

**Módulo:** frontend
**Arquivo(s):** `frontend/src/stores/calendar.ts`
**US:** US-041, US-042
**Depende de:** TASK-016, TASK-062
**Produz para:** TASK-073

#### O que criar

```typescript
export const useCalendarStore = defineStore('calendar', () => {
  const currentMonth = ref(new Date())
  const calendarData  = ref<CalendarResponse | null>(null)
  const selectedDay   = ref<CalendarDay | null>(null)
  const selectedAccountIds = ref<number[]>([])  // [] = todos
  const loading       = ref(false)

  // Carrega dados do mês atual filtrados pelos canais selecionados
  async function loadMonth(year: number, month: number): Promise<void> { ... }

  // Navegação
  function nextMonth(): void { currentMonth.value = addMonths(currentMonth.value, 1) }
  function prevMonth(): void { currentMonth.value = addMonths(currentMonth.value, -1) }

  // Filtro client-side por canal
  const filteredDays = computed<CalendarDay[]>(() => {
    if (!calendarData.value) return []
    if (selectedAccountIds.value.length === 0) return calendarData.value.days
    return calendarData.value.days.map(day => ({
      ...day,
      publications: day.publications.filter(
        p => selectedAccountIds.value.includes(p.account_id)
      )
    }))
  })

  // Total de publicações no mês filtrado
  const totalFiltered = computed(() =>
    filteredDays.value.reduce((sum, d) => sum + d.publications.length, 0)
  )

  return {
    currentMonth, calendarData, selectedDay,
    selectedAccountIds, loading,
    filteredDays, totalFiltered,
    loadMonth, nextMonth, prevMonth
  }
})
```

**Adicionar ao `src/services/api.ts`:**
```typescript
export const calendarApi = {
  getMonth: (startDate: string, endDate: string, accountIds?: number[]) => ...
}
export const batchApi = {
  preview:  (count: number, schedule: BatchScheduleConfig) => ...,
  create:   (data: BatchJobCreate) => ...,
  get:      (batchId: number) => ...,
  cancel:   (batchId: number) => ...,
}
```

#### Critérios de conclusão
- [ ] `loadMonth` chama `GET /api/calendar` com `start_date` = 1º do mês e `end_date` = último do mês
- [ ] `filteredDays` refiltra client-side sem nova requisição ao mudar `selectedAccountIds`
- [ ] `nextMonth`/`prevMonth` trigam `loadMonth` automaticamente
- [ ] `selectedDay` atualizado ao clicar em um dia no calendário

---

### TASK-071 — Criar BatchScheduleForm.vue

**Módulo:** frontend
**Arquivo(s):** `frontend/src/components/forms/BatchScheduleForm.vue`
**US:** US-040
**Depende de:** TASK-016, TASK-041
**Produz para:** TASK-074 (BatchJobView usa)

#### O que criar

Formulário de configuração do lote com:

1. **Quantidade de vídeos:** campo numérico (1-50)
2. **Configuração de agendamento:**
   - Date picker para data de início
   - Checkboxes dos dias da semana (Seg/Ter/Qua/Qui/Sex/Sáb/Dom), estilo pill/badge
   - Time pickers para início e fim da janela
   - Select de fuso horário (lista filtrada: fusos das Américas, Europa, Ásia)
3. **Preview automático:** ao alterar qualquer parâmetro, debounce de 500ms chama `POST /api/jobs/batch/preview` e exibe tabela com slots gerados:
   ```
   Vídeo 1 → Seg, 15 Jan • 09:00
   Vídeo 2 → Seg, 15 Jan • 15:00
   Vídeo 3 → Ter, 16 Jan • 09:00
   ...
   ```
4. **Mensagem de erro** se slots insuficientes (ex: "Apenas 8 slots disponíveis para 10 vídeos. Amplie a janela ou selecione mais dias.")

#### Critérios de conclusão
- [ ] Preview atualizado automaticamente com debounce de 500ms
- [ ] Erro de validação exibido inline (não alert)
- [ ] "Todos os dias úteis" (Seg-Sex) como preset rápido
- [ ] Emite `@update:modelValue` com o `BatchScheduleConfig` completo quando válido

---

### TASK-072 — Criar CalendarView.vue e componentes de calendário

**Módulo:** frontend
**Arquivo(s):** `frontend/src/views/CalendarView.vue`, `frontend/src/components/calendar/`
**US:** US-041, US-042
**Depende de:** TASK-070, TASK-015
**Produz para:** —

#### O que criar

**`CalendarMonth.vue`** — grid CSS 7×N com os dias do mês:
- Cabeçalho: Seg | Ter | Qua | Qui | Sex | Sáb | Dom
- Cada célula: número do dia + badges coloridos por canal (máx 3 visíveis + "+N mais")
- Dia com publicações: fundo levemente destacado
- Dia selecionado: borda colorida
- Dias do mês anterior/seguinte: opacidade reduzida

**`CalendarDay.vue`** — célula individual:
- Props: `date`, `publications: CalendarPublication[]`, `isSelected`
- Badges: cor do canal (derivada do `account_id` via hash de cor consistente)
- Emite `@click` com o dia

**`PublicationList.vue`** — painel lateral deslizante:
- Aparece ao clicar em um dia
- Lista de cards por publicação: avatar do canal, título, horário, badge de status
- Link "Abrir no YouTube" quando disponível
- Fechar ao clicar fora ou no X

**`ChannelFilter.vue`** — barra de filtros:
- Linha horizontal com checkbox+avatar de cada canal
- Toggle "Todos" que seleciona/deseleciona todos

**`CalendarView.vue`** — view principal:
```vue
<template>
  <div class="flex gap-4">
    <div class="flex-1">
      <CalendarHeader />      <!-- mês/ano + setas de navegação -->
      <ChannelFilter />       <!-- filtros de canal -->
      <CalendarMonth />       <!-- grid -->
    </div>
    <PublicationList />       <!-- painel lateral (v-if selectedDay) -->
  </div>
</template>
```

**Atualizar `router/index.ts`:**
```typescript
{ path: '/calendar', component: () => import('../views/CalendarView.vue') }
```

**Atualizar `App.vue`:**
- Adicionar link "Calendário" com ícone de calendário na nav

#### Critérios de conclusão
- [ ] Navegação entre meses carrega novos dados sem reload da página
- [ ] Clicar em um dia abre `PublicationList` com as publicações daquele dia
- [ ] `ChannelFilter` filtra instantaneamente sem nova requisição
- [ ] Badges coloridos por canal (cor gerada via hash do `account_id`)
- [ ] Responsivo: em mobile, `PublicationList` ocupa a tela toda

---

### TASK-073 — Criar BatchJobView.vue (tela de criação de lote)

**Módulo:** frontend
**Arquivo(s):** `frontend/src/views/BatchJobView.vue`
**US:** US-040
**Depende de:** TASK-051, TASK-071, TASK-042
**Produz para:** —

#### O que criar

View acessível em `/jobs/batch` para criar um lote de vídeos com agendamento automático.

**Estrutura em 3 seções:**

1. **Configuração base do vídeo** (igual ao NewJobView, sem step de texto individual):
   - Seleção de contas (multi-select)
   - Configuração de áudio (voz, duração alvo)
   - Configuração de vídeo (pasta, dimensão, vintage)
   - Configuração de metadados (prompts de título e descrição)
   - Prompt base para geração de texto (os N textos serão gerados pelo pipeline de cada job)

2. **Configuração do lote** (`BatchScheduleForm`):
   - Quantidade de vídeos
   - Janela de agendamento + dias
   - Preview da distribuição

3. **Resumo e confirmação:**
   - Card resumindo: N vídeos, datas de início e fim, contas selecionadas
   - Botão "Criar Lote" → chama `POST /api/jobs/batch` e redireciona para `/calendar`

**Atualizar `App.vue` / `DashboardView.vue`:**
- Botão "Novo Lote" ao lado de "Novo Processamento" no dashboard

**Atualizar `router/index.ts`:**
```typescript
{ path: '/jobs/batch', component: () => import('../views/BatchJobView.vue') }
```

#### Critérios de conclusão
- [ ] Redireciona para `/calendar` após criação bem-sucedida do lote
- [ ] Errors da API exibidos inline (não alert)
- [ ] "Criar Lote" desabilitado enquanto preview está carregando ou tem erro
- [ ] Estado não perdido ao navegar entre as seções

---

## Atualização da Tabela de Rastreabilidade

| Task | US | Arquivo Principal | Fase |
|---|---|---|---|
| TASK-065 | US-040 | `alembic/versions/003_job_batches.py` + `models/job_batch.py` | 1 |
| TASK-066 | US-040, US-041 | `schemas/batch.py` | 1 |
| TASK-067 | US-040 | `services/scheduler/distributor.py` | 2 |
| TASK-068 | US-040 | `api/routes/jobs.py` (atualização — batch endpoints) | 5 |
| TASK-069 | US-041, US-042 | `api/routes/calendar.py` | 5 |
| TASK-070 | US-041, US-042 | `stores/calendar.ts` | 6 |
| TASK-071 | US-040 | `components/forms/BatchScheduleForm.vue` | 6 |
| TASK-072 | US-041, US-042 | `CalendarView.vue` + `components/calendar/` | 6 |
| TASK-073 | US-040 | `BatchJobView.vue` | 6 |

---

## Correções da Análise de Fluxo

---

### TASK-074 — Criar api/routes/metadata.py (preview de metadados no wizard)

**Módulo:** backend
**Arquivo(s):** `backend/app/api/routes/metadata.py`
**US:** US-027, US-028
**Depende de:** TASK-031, TASK-010
**Produz para:** TASK-053 (Step 5 do wizard chama este endpoint)

#### O que criar

Endpoint de geração de metadados sob demanda, sem criar job:

```
POST /api/metadata/generate
  body: {
    text: str,                  # texto da narração (pré-gerado)
    model: str,
    title_prompt: str | None,
    description_prompt: str | None,
    tags_prompt: str | None
  }
  response: {
    title: str,                 # ≤ 100 chars
    description: str,           # ≤ 5000 chars
    tags: list[str]             # 5-10 tags
  }
```

Reutiliza `services/metadata/generator.py` (TASK-031) e `services/text_generation/ollama_generator.py` (TASK-018).

Registrar em `main.py`:
```python
app.include_router(metadata_router, prefix="/api")
```

#### Critérios de conclusão
- [ ] Endpoint retorna `{ title, description, tags }` com Ollama disponível
- [ ] Retorna HTTP 503 com mensagem clara se Ollama offline
- [ ] `title` sempre ≤ 100 chars, `description` ≤ 5000 chars (truncado se necessário)
- [ ] Cada geração (título, descrição, tags) pode ser feita independentemente via query param `?fields=title,tags`
- [ ] Adicionado ao `src/services/api.ts` como `metadataApi.generate(...)`

---

### TASK-075 — Atualizar src/types/index.ts com campos pré-gerados e frontend_url

**Módulo:** frontend + backend
**Arquivo(s):** `frontend/src/types/index.ts`, `backend/app/core/config.py`
**US:** US-013, US-017, US-027
**Depende de:** TASK-062, TASK-002
**Produz para:** TASK-053, TASK-073

#### O que criar

**`frontend/src/types/index.ts` — atualizar `JobConfig`:**
```typescript
export interface JobConfig {
  // ... campos existentes ...

  // Conteúdo pré-gerado no wizard (pula etapas correspondentes no pipeline)
  pre_generated_text?:           string
  pre_generated_audio_path?:     string
  pre_generated_audio_duration?: number
  pre_generated_title?:          string
  pre_generated_description?:    string
}
```

**`backend/app/core/config.py` — adicionar `frontend_url`:**
```python
class Settings(BaseSettings):
    # ... campos existentes ...
    frontend_url: str = "http://localhost:5173"   # usado no redirect OAuth
```

**`backend/app/api/routes/accounts.py` — usar `settings.frontend_url`:**
```python
# No callback OAuth:
redirect_url = f"{settings.frontend_url}/accounts?connected=true"
return RedirectResponse(url=redirect_url)
```

#### Critérios de conclusão
- [ ] `JobConfig.pre_generated_text` e demais campos opcionais no TypeScript
- [ ] Backend `JobConfig` Pydantic com mesmos campos opcionais (`str | None = None`)
- [ ] OAuth callback usa `settings.frontend_url` (nunca string literal)
- [ ] `FRONTEND_URL` adicionado ao `.env.example`
