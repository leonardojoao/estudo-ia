# Plano de Testes — YouTube Automation

**Versão:** 1.0  
**Autor:** QA Engineer  
**Data:** 2025  
**Baseado em:** Especificação de Produto v1.0 + Especificação Técnica v1.0

---

## Sumário

1. [Estratégia de Testes](#1-estratégia-de-testes)
2. [Casos de Teste por Módulo](#2-casos-de-teste-por-módulo)
3. [Casos Críticos que NÃO PODEM Falhar](#3-casos-críticos-que-não-podem-falhar)
4. [Cenários do Algoritmo Anti-Plágio](#4-cenários-do-algoritmo-anti-plágio)
5. [Cenários E2E do Pipeline Completo](#5-cenários-e2e-do-pipeline-completo)
6. [Matriz de Rastreabilidade](#6-matriz-de-rastreabilidade)
7. [Ambiente de Teste](#7-ambiente-de-teste)

---

## 1. Estratégia de Testes

### 1.1 Pirâmide de Testes

```
         ┌─────────┐
         │   E2E   │  ~10% — Playwright
        ┌┴─────────┴┐
        │ Integração │  ~30% — pytest + httpx
       ┌┴───────────┴┐
       │  Unitários  │  ~60% — pytest + Vitest
       └─────────────┘
```

### 1.2 Ferramentas por Camada

| Camada | Ferramenta | Propósito |
|---|---|---|
| **Unitário Backend** | `pytest` + `pytest-asyncio` | Testar serviços isolados (selector, cutter, sequencer, etc.) |
| **Unitário Frontend** | `Vitest` + `Vue Test Utils` | Testar componentes e stores Pinia |
| **Integração Backend** | `pytest` + `httpx` + `TestClient (FastAPI)` | Testar endpoints REST com banco em memória |
| **Integração Frontend** | `Vitest` + `MSW (Mock Service Worker)` | Testar chamadas HTTP mockadas no frontend |
| **E2E** | `Playwright` | Fluxos completos navegador → backend → banco |
| **Performance** | `Locust` | Carga nos endpoints SSE e de criação de jobs |
| **Segurança** | `bandit` (SAST) + testes manuais | Injeção de path, tokens, CORS |

### 1.3 Cobertura Mínima por Módulo

| Módulo | Cobertura Mínima | Justificativa |
|---|---|---|
| `services/video/sequencer.py` | 95% | Coração do sistema anti-plágio — risco máximo |
| `services/video/cutter.py` | 90% | Integração direta com FFmpeg — muitos casos de borda |
| `services/youtube/auth.py` | 90% | Segurança de tokens OAuth — dado sensível |
| `services/youtube/uploader.py` | 85% | Integração externa — propenso a falhas |
| `pipeline/runner.py` | 85% | Orquestrador — falha aqui paralisa tudo |
| `services/audio/edge_tts.py` | 80% | Depende de internet — muitos cenários de erro |
| `services/text_generation/ollama_generator.py` | 80% | Dependência externa local |
| `api/routes/*.py` | 80% | Contratos de API — regressão crítica |
| `services/video/selector.py` | 80% | Aleatoriedade — validar distribuição e casos de borda |
| `services/video/composer.py` | 75% | Delegado ao FFmpeg — testar inputs/outputs |
| `services/metadata/generator.py` | 75% | Derivado do text_generation |

### 1.4 Priorização por Risco

| Prioridade | Módulo/Funcionalidade | Risco |
|---|---|---|
| 🔴 **Crítico** | Algoritmo de sequenciamento anti-plágio | Falha silenciosa — vídeo gerado com consecutivos do mesmo fonte |
| 🔴 **Crítico** | Upload YouTube (OAuth + API v3) | Token inválido pode causar perda de job já processado |
| 🔴 **Crítico** | Pipeline runner (orquestração) | Falha em etapa pode corromper estado do job |
| 🟠 **Alto** | Geração e verificação de duração do áudio | Duração errada afeta todo o pipeline de vídeo |
| 🟠 **Alto** | Seleção e corte de vídeos (FFmpeg) | Arquivo corrompido ou FFmpeg ausente trava o job |
| 🟠 **Alto** | SSE de status em tempo real | Usuário sem feedback fica cego ao progresso |
| 🟡 **Médio** | Geração de texto via Ollama | Fallback é texto manual — impacto menor |
| 🟡 **Médio** | Configurações iniciais (settings) | Erros de configuração detectados cedo |
| 🟢 **Baixo** | Geração em lote | Feature secundária (Should) |
| 🟢 **Baixo** | Preview de voz TTS | Feature de conveniência |

### 1.5 Estratégia por Tipo de Teste

- **Testes unitários:** Sim — todos os serviços de `services/` com mocks das dependências externas (FFmpeg, Ollama, edge-tts, YouTube API)
- **Testes de integração:** Sim — todos os endpoints `api/routes/` com `TestClient` e banco SQLite in-memory, mocks externos via `pytest-mock`
- **Testes E2E:** Sim — 3 cenários principais com Playwright (pipeline IA, pipeline manual, pipeline agendado)
- **Testes de performance:** Sim — SSE com 50 conexões simultâneas, criação de 100 jobs concorrentes

---

## 2. Casos de Teste por Módulo

---

### 2.1 Módulo: Configurações do Sistema (`US-001`)

---

#### CT-001: Listar configurações com valores padrão

- **US:** US-001
- **Tipo:** Integração
- **Pré-condição:** Banco de dados recém-criado com dados padrão inseridos (INSERT INTO system_settings)
- **Passos:**
  1. Enviar `GET /api/settings`
  2. Verificar resposta HTTP 200
  3. Validar campos no payload
- **Resultado esperado:** Retorna JSON `{"data": {"ollama_url": "http://localhost:11434", "ollama_model": "llama3", "videos_folder": "", "tts_voice": "en-US-JennyNeural", "default_dimension": "16:9", "clip_min_duration": "3", "clip_max_duration": "6"}}` — todos os campos presentes
- **Casos de borda:** Banco corrompido deve retornar HTTP 500 com `{"error": "DB_ERROR"}`
- **Prioridade:** Alta

---

#### CT-002: Atualizar configurações com valores válidos

- **US:** US-001
- **Tipo:** Integração
- **Pré-condição:** Banco de dados inicializado. Ollama rodando em `http://localhost:11434`. Pasta `/tmp/test_videos` existindo com pelo menos 1 arquivo `.mp4`
- **Passos:**
  1. Criar pasta `/tmp/test_videos` (fixture)
  2. Enviar `PUT /api/settings` com body: `{"ollama_url": "http://localhost:11434", "videos_folder": "/tmp/test_videos", "tts_voice": "en-US-GuyNeural"}`
  3. Verificar resposta HTTP 200
  4. Enviar `GET /api/settings`
  5. Verificar que os valores atualizados foram persistidos
- **Resultado esperado:** HTTP 200 na PUT. GET subsequente retorna os novos valores. `updated_at` da tabela `system_settings` foi atualizado.
- **Casos de borda:** Atualizar apenas 1 chave não deve sobrescrever as demais
- **Prioridade:** Alta

---

#### CT-003: Rejeitar URL do Ollama com formato inválido

- **US:** US-001
- **Tipo:** Integração
- **Pré-condição:** Banco de dados inicializado
- **Passos:**
  1. Enviar `PUT /api/settings` com body: `{"ollama_url": "nao-eh-uma-url"}`
  2. Verificar status HTTP
  3. Verificar mensagem de erro
- **Resultado esperado:** HTTP 422 (Unprocessable Entity). Body contém `{"error": "VALIDATION_ERROR", "message": "URL do Ollama inválida"}`. Banco não é alterado.
- **Casos de borda:** `"http://"` (sem host), `""` (string vazia), `null`
- **Prioridade:** Média

---

#### CT-004: Rejeitar pasta de vídeos inexistente

- **US:** US-001
- **Tipo:** Integração
- **Pré-condição:** Banco de dados inicializado. Pasta `/caminho/que/nao/existe` não existe no sistema
- **Passos:**
  1. Enviar `PUT /api/settings` com body: `{"videos_folder": "/caminho/que/nao/existe"}`
  2. Verificar status HTTP e mensagem de erro
- **Resultado esperado:** HTTP 400 com `{"error": "INVALID_PATH", "message": "Pasta não encontrada: /caminho/que/nao/existe"}`
- **Casos de borda:** Path apontando para um arquivo (não diretório) deve também retornar erro
- **Prioridade:** Alta

---

#### CT-005: Prevenção de path traversal na pasta de vídeos

- **US:** US-001
- **Tipo:** Segurança
- **Pré-condição:** Banco de dados inicializado
- **Passos:**
  1. Enviar `PUT /api/settings` com body: `{"videos_folder": "/tmp/videos/../../etc"}`
  2. Verificar que o path é normalizado ou rejeitado
  3. Enviar com `{"videos_folder": "../../../../etc/passwd"}`
  4. Verificar comportamento
- **Resultado esperado:** Ambos os casos retornam HTTP 400 com erro de validação. Nenhum path com `..` deve ser aceito sem normalização e validação de que o resultado ainda está dentro de um diretório permitido.
- **Casos de borda:** Path com caracteres especiais: `; rm -rf /`, `$(whoami)`
- **Prioridade:** Alta

---

### 2.2 Módulo: Integração Ollama (`US-002`)

---

#### CT-006: Listar modelos com Ollama online

- **US:** US-002
- **Tipo:** Integração
- **Pré-condição:** Ollama mockado respondendo com lista de modelos `["llama3", "mistral", "phi3"]`
- **Passos:**
  1. Configurar mock do endpoint `GET http://localhost:11434/api/tags` para retornar `{"models": [{"name": "llama3"}, {"name": "mistral"}, {"name": "phi3"}]}`
  2. Enviar `GET /api/ollama/models`
  3. Verificar resposta
- **Resultado esperado:** HTTP 200 com `{"data": {"models": ["llama3", "mistral", "phi3"]}}`. Lista contém exatamente os modelos retornados pelo mock.
- **Casos de borda:** Ollama retornando lista vazia `{"models": []}` → deve retornar HTTP 200 com lista vazia e warning "Nenhum modelo instalado"
- **Prioridade:** Alta

---

#### CT-007: Listar modelos com Ollama offline

- **US:** US-002
- **Tipo:** Integração
- **Pré-condição:** Ollama mockado para rejeitar conexão (`ConnectionRefusedError`)
- **Passos:**
  1. Configurar mock para lançar `ConnectionRefusedError` ao chamar a URL do Ollama
  2. Enviar `GET /api/ollama/models`
  3. Verificar resposta
- **Resultado esperado:** HTTP 503 com `{"error": "OLLAMA_UNAVAILABLE", "message": "Não foi possível conectar ao Ollama em http://localhost:11434. Verifique se o serviço está rodando."}`
- **Casos de borda:** Timeout (aguarda 5s sem resposta), resposta 500 do Ollama
- **Prioridade:** Alta

---

#### CT-008: Listar modelos com timeout da requisição

- **US:** US-002
- **Tipo:** Integração
- **Pré-condição:** Ollama mockado para demorar mais de 10 segundos para responder
- **Passos:**
  1. Configurar mock com `asyncio.sleep(15)` antes de responder
  2. Definir timeout do cliente HTTP para 5 segundos
  3. Enviar `GET /api/ollama/models`
- **Resultado esperado:** HTTP 504 (Gateway Timeout) após 5s. Mensagem clara sobre timeout. Não deixar a requisição travada indefinidamente.
- **Casos de borda:** —
- **Prioridade:** Média

---

### 2.3 Módulo: Contas YouTube — OAuth (`US-003`)

---

#### CT-009: Gerar URL de autorização OAuth válida

- **US:** US-003
- **Tipo:** Integração
- **Pré-condição:** `client_secrets.json` configurado nas settings (mockado). `GOOGLE_CLIENT_ID` e `GOOGLE_CLIENT_SECRET` disponíveis como env vars de teste.
- **Passos:**
  1. Enviar `GET /api/accounts/oauth/url`
  2. Verificar resposta
  3. Validar estrutura da URL retornada
- **Resultado esperado:** HTTP 200 com `{"data": {"url": "https://accounts.google.com/o/oauth2/auth?..."}}`. A URL contém os parâmetros: `client_id`, `redirect_uri`, `scope=https://www.googleapis.com/auth/youtube.upload`, `response_type=code`, `access_type=offline`, `state` (token CSRF único).
- **Casos de borda:** Credenciais OAuth não configuradas → HTTP 400 com mensagem orientando a configurar
- **Prioridade:** Alta

---

#### CT-010: Callback OAuth com código de autorização válido

- **US:** US-003
- **Tipo:** Integração
- **Pré-condição:** Mock do Google OAuth configurado para trocar `code=valid_code` por tokens. Mock da YouTube Data API retornando dados do canal `{"id": "UC123", "snippet": {"title": "Meu Canal", "thumbnails": {...}}}`.
- **Passos:**
  1. Enviar `GET /api/accounts/oauth/callback?code=valid_code&state=csrf_token_valido`
  2. Verificar se conta foi criada no banco
  3. Verificar dados retornados
- **Resultado esperado:** HTTP 200. Conta criada na tabela `youtube_accounts` com `channel_id`, `name`, `email`, `avatar_url`. Credenciais (tokens) salvas criptografadas. `is_active = 1`. Resposta contém dados do canal.
- **Casos de borda:** Mesmo channel_id já cadastrado deve atualizar tokens (não duplicar)
- **Prioridade:** Alta

---

#### CT-011: Callback OAuth com código inválido ou expirado

- **US:** US-003
- **Tipo:** Integração
- **Pré-condição:** Mock do Google OAuth configurado para retornar erro `{"error": "invalid_grant"}` para o code `expired_code`
- **Passos:**
  1. Enviar `GET /api/accounts/oauth/callback?code=expired_code&state=csrf_token_valido`
  2. Verificar resposta e banco
- **Resultado esperado:** HTTP 400 com `{"error": "OAUTH_ERROR", "message": "Código de autorização inválido ou expirado"}`. Nenhuma conta criada no banco.
- **Casos de borda:** `code` ausente na query string → HTTP 400
- **Prioridade:** Alta

---

#### CT-012: Callback OAuth com state CSRF inválido

- **US:** US-003
- **Tipo:** Segurança
- **Pré-condição:** Banco inicializado
- **Passos:**
  1. Enviar `GET /api/accounts/oauth/callback?code=qualquer_code&state=state_forjado_pelo_atacante`
  2. Verificar resposta
- **Resultado esperado:** HTTP 400 com `{"error": "CSRF_VIOLATION", "message": "State inválido — possível ataque CSRF"}`. Código não é trocado por tokens. Nenhuma conta criada.
- **Casos de borda:** `state` ausente na query string deve ser tratado da mesma forma
- **Prioridade:** Alta

---

#### CT-013: Listar contas conectadas

- **US:** US-004
- **Tipo:** Integração
- **Pré-condição:** Banco com 2 contas: uma ativa, uma inativa
- **Passos:**
  1. Inserir 2 contas de teste no banco (fixture)
  2. Enviar `GET /api/accounts`
  3. Verificar estrutura da resposta
- **Resultado esperado:** HTTP 200 com lista de 2 contas. Cada conta contém: `id`, `name`, `channel_id`, `email`, `avatar_url`, `is_active`, `created_at`. Campo `credentials` (tokens) **não deve** aparecer na resposta.
- **Casos de borda:** Nenhuma conta cadastrada → `{"data": {"accounts": []}}` (não retornar erro 404)
- **Prioridade:** Alta

---

#### CT-014: Testar conexão com token válido

- **US:** US-004
- **Tipo:** Integração
- **Pré-condição:** Conta com token válido no banco. Mock da YouTube API retornando sucesso.
- **Passos:**
  1. Inserir conta com tokens válidos (fixture)
  2. Configurar mock de `GET https://www.googleapis.com/youtube/v3/channels?mine=true` para retornar HTTP 200
  3. Enviar `POST /api/accounts/{id}/test`
  4. Verificar resposta
- **Resultado esperado:** HTTP 200 com `{"data": {"status": "valid", "channel_name": "Meu Canal"}}`. `is_active` permanece `true` no banco.
- **Casos de borda:** —
- **Prioridade:** Alta

---

#### CT-015: Testar conexão com token expirado — refresh automático

- **US:** US-004
- **Tipo:** Integração
- **Pré-condição:** Conta com `access_token` expirado mas `refresh_token` válido. Mock do Google OAuth configurado para trocar refresh_token por novo access_token.
- **Passos:**
  1. Inserir conta com token expirado no banco
  2. Mock da YouTube API retorna HTTP 401 na primeira chamada
  3. Mock do OAuth retorna novo access_token no refresh
  4. Mock da YouTube API retorna HTTP 200 na segunda chamada
  5. Enviar `POST /api/accounts/{id}/test`
- **Resultado esperado:** HTTP 200. Tokens atualizados no banco com novo `access_token`. Status retornado é `valid`. Nenhum erro exposto ao usuário.
- **Casos de borda:** refresh_token também expirado → HTTP 200 com `{"data": {"status": "expired", "message": "Re-autenticação necessária"}}`
- **Prioridade:** Alta

---

#### CT-016: Desconectar conta

- **US:** US-004
- **Tipo:** Integração
- **Pré-condição:** Conta com id=1 no banco. Nenhum job pendente vinculado.
- **Passos:**
  1. Inserir conta de teste no banco
  2. Enviar `DELETE /api/accounts/1`
  3. Verificar resposta
  4. Enviar `GET /api/accounts`
  5. Verificar que conta não aparece mais
- **Resultado esperado:** HTTP 200. Conta removida do banco (ou marcada como inativa). Tokens removidos/apagados. `GET /api/accounts` não lista mais a conta.
- **Casos de borda:** Conta com jobs em andamento → HTTP 409 com mensagem "Conta está sendo usada por jobs em andamento"
- **Prioridade:** Alta

---

#### CT-017: Desconectar conta inexistente

- **US:** US-004
- **Tipo:** Integração
- **Pré-condição:** Banco sem conta com id=999
- **Passos:**
  1. Enviar `DELETE /api/accounts/999`
- **Resultado esperado:** HTTP 404 com `{"error": "ACCOUNT_NOT_FOUND", "message": "Conta #999 não encontrada"}`
- **Casos de borda:** `DELETE /api/accounts/abc` (id não numérico) → HTTP 422
- **Prioridade:** Média

---

### 2.4 Módulo: Geração de Texto (`US-006`, `US-007`, `US-008`)

---

#### CT-018: Gerar texto via Ollama com prompt válido

- **US:** US-006
- **Tipo:** Unitário
- **Pré-condição:** Mock do cliente Ollama (`ollama.AsyncClient`) retornando `{"response": "This is a generated text about nature."}` para qualquer prompt
- **Passos:**
  1. Instanciar `OllamaGenerator(base_url="http://localhost:11434", model="llama3")`
  2. Chamar `await generator.generate(TextGenInput(prompt="Write a short script about nature", max_tokens=500))`
  3. Verificar resultado
- **Resultado esperado:** `TextGenOutput` com `text="This is a generated text about nature."`, `model="llama3"`, `tokens_used` preenchido. Sem exceções.
- **Casos de borda:** Resposta do Ollama com texto vazio → lançar `TextGenerationError("Ollama retornou resposta vazia")`
- **Prioridade:** Alta

---

#### CT-019: Gerar texto com Ollama offline

- **US:** US-006
- **Tipo:** Unitário
- **Pré-condição:** Mock do cliente Ollama configurado para lançar `httpx.ConnectError`
- **Passos:**
  1. Instanciar `OllamaGenerator` com URL inválida
  2. Chamar `await generator.generate(TextGenInput(prompt="test", max_tokens=100))`
  3. Verificar exceção lançada
- **Resultado esperado:** Lança `OllamaUnavailableError` com mensagem informativa. Não lança exceção genérica não tratada.
- **Casos de borda:** Timeout de conexão → mesmo comportamento
- **Prioridade:** Alta

---

#### CT-020: Gerar texto com modelo inexistente no Ollama

- **US:** US-006
- **Tipo:** Unitário
- **Pré-condição:** Mock do Ollama retornando HTTP 404 com `{"error": "model 'modelo_inexistente' not found"}`
- **Passos:**
  1. Instanciar `OllamaGenerator(model="modelo_inexistente")`
  2. Chamar `generate()`
  3. Verificar exceção
- **Resultado esperado:** Lança `ModelNotFoundError("Modelo 'modelo_inexistente' não encontrado no Ollama")`. Mensagem clara para o usuário.
- **Casos de borda:** Nome de modelo com caracteres especiais, string vazia como nome do modelo
- **Prioridade:** Média

---

#### CT-021: Rejeitar prompt vazio

- **US:** US-006
- **Tipo:** Unitário
- **Pré-condição:** —
- **Passos:**
  1. Instanciar `OllamaGenerator`
  2. Chamar `generate(TextGenInput(prompt="", max_tokens=100))`
  3. Verificar comportamento
- **Resultado esperado:** `ValidationError` lançado pelo schema Pydantic antes de qualquer chamada à API Ollama. Nenhuma requisição HTTP é feita.
- **Casos de borda:** Prompt com apenas espaços em branco `"   "` deve ser tratado como vazio após `.strip()`
- **Prioridade:** Média

---

#### CT-022: Pipeline com texto manual (sem IA)

- **US:** US-007
- **Tipo:** Integração
- **Pré-condição:** Job criado com `config.text_mode = "manual"` e `config.manual_text = "Hello world this is my video script."`
- **Passos:**
  1. Criar job com modo manual via `POST /api/jobs`
  2. Executar etapa `text_generation` via `POST /api/jobs/{id}/steps/text_generation`
  3. Verificar output da etapa
- **Resultado esperado:** Etapa `text_generation` marca status como `completed` imediatamente. Output contém o texto inserido manualmente. **Nenhuma** chamada ao Ollama é realizada (verificar mock não chamado).
- **Casos de borda:** Texto manual vazio → HTTP 400 na criação do job
- **Prioridade:** Alta

---

#### CT-023: Geração em lote de 3 textos

- **US:** US-008
- **Tipo:** Integração
- **Pré-condição:** Mock do Ollama retornando textos distintos para cada chamada (usando `side_effect`). Configuração de lote: `batch_size=3, prompt="Write about technology"`
- **Passos:**
  1. Enviar `POST /api/jobs` com `config.batch_size=3`
  2. Iniciar pipeline via `POST /api/jobs/{id}/run`
  3. Monitorar SSE para acompanhar progresso
  4. Verificar ao final quantos textos foram gerados e salvos
- **Resultado esperado:** 3 jobs criados (ou 1 job com 3 iterações, conforme implementação). Progress SSE emite `1/3`, `2/3`, `3/3`. Todos os textos gerados são diferentes. Status final: `completed`.
- **Casos de borda:** `batch_size=0` → HTTP 400. `batch_size=100` → deve funcionar (sem timeout artificial)
- **Prioridade:** Baixa

---

#### CT-024: Cancelar geração em lote no meio

- **US:** US-008
- **Tipo:** Integração
- **Pré-condição:** Job de lote com `batch_size=5` em andamento (geração do segundo texto em progresso)
- **Passos:**
  1. Iniciar geração de lote com `batch_size=5`
  2. Aguardar confirmação SSE de `1/5` gerado
  3. Enviar `DELETE /api/jobs/{id}` (cancelamento)
  4. Verificar estado do job e quantos textos foram salvos
- **Resultado esperado:** Pipeline interrompido. Job com status `cancelled`. Textos já gerados (1 no mínimo) são preservados no banco. Nenhum estado inconsistente.
- **Casos de borda:** —
- **Prioridade:** Baixa

---

### 2.5 Módulo: Geração de Áudio TTS (`US-009`, `US-010`)

---

#### CT-025: Gerar áudio com texto e voz válidos

- **US:** US-009
- **Tipo:** Unitário
- **Pré-condição:** Mock do `edge_tts.Communicate` configurado para salvar um arquivo MP3 de teste (~10s de duração) quando chamado com voz `en-US-JennyNeural`
- **Passos:**
  1. Instanciar `EdgeTTSGenerator()`
  2. Chamar `await generator.generate(AudioGenInput(text="Hello, this is a test.", voice="en-US-JennyNeural", target_duration_s=10))`
  3. Verificar que arquivo MP3 foi salvo
  4. Verificar retorno
- **Resultado esperado:** `AudioGenOutput` com `audio_path` apontando para arquivo existente. Extensão `.mp3`. `actual_duration_s` preenchido com valor real. `voice_used = "en-US-JennyNeural"`.
- **Casos de borda:** —
- **Prioridade:** Alta

---

#### CT-026: Verificação de duração do áudio vs duração alvo

- **US:** US-009
- **Tipo:** Unitário
- **Pré-condição:** Arquivo de áudio de teste com 45 segundos de duração real. `target_duration_s=60`.
- **Passos:**
  1. Chamar `AudioVerifier.verify(audio_path="/tmp/test.mp3", target_duration_s=60)`
  2. Verificar retorno e log
- **Resultado esperado:** `AudioVerificationResult` com `actual_duration_s=45`, `target_duration_s=60`, `difference_s=15`, `within_tolerance=False` (tolerância padrão ±10%). Log indica diferença. Não lança exceção — a etapa retorna aviso mas continua.
- **Casos de borda:** Duração real exatamente igual à alvo → `within_tolerance=True`. Duração real 9% abaixo → `within_tolerance=True` (dentro da tolerância).
- **Prioridade:** Alta

---

#### CT-027: Rejeitar texto vazio para TTS

- **US:** US-009
- **Tipo:** Unitário
- **Pré-condição:** —
- **Passos:**
  1. Chamar `generator.generate(AudioGenInput(text="", voice="en-US-JennyNeural", target_duration_s=60))`
- **Resultado esperado:** `ValidationError` via Pydantic antes de qualquer chamada ao edge-tts. Mensagem: `"Texto não pode ser vazio"`.
- **Casos de borda:** Texto com apenas espaços e quebras de linha
- **Prioridade:** Alta

---

#### CT-028: Lidar com texto extremamente longo para TTS

- **US:** US-009
- **Tipo:** Unitário
- **Pré-condição:** Texto de teste com 50.000 caracteres (simula Ollama gerando texto excessivo). Mock edge-tts configurado.
- **Passos:**
  1. Chamar `generator.generate(AudioGenInput(text="A"*50000, voice="en-US-JennyNeural", target_duration_s=60))`
  2. Verificar comportamento
- **Resultado esperado:** Sistema trunca o texto antes de enviar ao edge-tts de forma que a duração gerada fique próxima de `target_duration_s`. Não lança exceção. Log informa que texto foi truncado.
- **Casos de borda:** Texto com caracteres Unicode especiais, emojis, HTML tags
- **Prioridade:** Média

---

#### CT-029: Falha na geração de áudio — sem internet (edge-tts)

- **US:** US-009
- **Tipo:** Unitário
- **Pré-condição:** Mock do `edge_tts.Communicate` lançando `aiohttp.ClientConnectorError` (sem rede)
- **Passos:**
  1. Chamar `generator.generate(AudioGenInput(text="Hello world", voice="en-US-JennyNeural", target_duration_s=30))`
- **Resultado esperado:** Lança `AudioGenerationError("Falha ao conectar ao serviço TTS. Verifique sua conexão com a internet.")`. Mensagem diferencia erro de rede de outros erros.
- **Casos de borda:** Timeout de rede, resposta parcial
- **Prioridade:** Alta

---

#### CT-030: Listar vozes TTS disponíveis

- **US:** US-010
- **Tipo:** Integração
- **Pré-condição:** Mock de `edge_tts.list_voices()` retornando lista de vozes em inglês
- **Passos:**
  1. Enviar `GET /api/ollama/voices`
  2. Verificar resposta
- **Resultado esperado:** HTTP 200 com lista de pelo menos 5 vozes em inglês. Cada voz contém: `name`, `short_name`, `gender`, `locale`. Apenas vozes com `locale` iniciando em `en-` são retornadas.
- **Casos de borda:** API edge-tts indisponível → HTTP 503 com lista de fallback (vozes conhecidas hardcoded)
- **Prioridade:** Baixa

---

### 2.6 Módulo: Seleção de Vídeos (`US-011`, `US-012`)

---

#### CT-031: Listar vídeos suportados na pasta configurada

- **US:** US-011
- **Tipo:** Unitário
- **Pré-condição:** Diretório de teste com: `video1.mp4`, `video2.mov`, `video3.avi`, `image.png`, `document.txt`, `.DS_Store`
- **Passos:**
  1. Chamar `VideoSelector.list_available(folder="/tmp/test_videos")`
- **Resultado esperado:** Retorna lista com apenas `["video1.mp4", "video2.mov", "video3.avi"]`. Arquivos não de vídeo e ocultos são ignorados.
- **Casos de borda:** Pasta com subpastas — subpastas não devem ser inclusas. Arquivos com extensão em maiúsculas `VIDEO.MP4` devem ser inclusos (case-insensitive).
- **Prioridade:** Alta

---

#### CT-032: Configurar pasta de vídeos vazia

- **US:** US-011
- **Tipo:** Integração
- **Pré-condição:** Pasta `/tmp/empty_videos` existe mas está vazia
- **Passos:**
  1. Enviar `PUT /api/settings` com `{"videos_folder": "/tmp/empty_videos"}`
  2. Verificar resposta e mensagem de aviso
- **Resultado esperado:** HTTP 200 (aceita a configuração) com warning no body: `{"data": {...}, "warning": "Pasta configurada está vazia. Adicione vídeos antes de iniciar processamentos."}`. Nenhum erro fatal.
- **Casos de borda:** —
- **Prioridade:** Alta

---

#### CT-033: Selecionar vídeos aleatórios para cobrir duração

- **US:** US-012
- **Tipo:** Unitário
- **Pré-condição:** Pasta com 3 vídeos de durações conhecidas: `v1.mp4` = 30s, `v2.mp4` = 45s, `v3.mp4` = 20s. `required_duration = 60s`.
- **Passos:**
  1. Chamar `VideoSelector.select(folder="/tmp/test_videos", required_duration_s=60)`
  2. Verificar lista retornada
  3. Executar 10 vezes para validar aleatoriedade
- **Resultado esperado:** Lista de vídeos com duração total somada ≥ 60s. A seleção é aleatória (distribuição varia entre execuções). Mesmo vídeo pode aparecer mais de uma vez se necessário.
- **Casos de borda:** `required_duration = 0` → retornar lista vazia. `required_duration` maior que a soma de todos os vídeos → reusar vídeos até cobrir.
- **Prioridade:** Alta

---

#### CT-034: Selecionar vídeos com pasta insuficiente de conteúdo

- **US:** US-012
- **Tipo:** Unitário
- **Pré-condição:** Pasta com apenas 1 vídeo de 5 segundos. `required_duration = 120s`.
- **Passos:**
  1. Chamar `VideoSelector.select(folder="/tmp/tiny_videos", required_duration_s=120)`
  2. Verificar que o vídeo é reusado o quanto necessário
- **Resultado esperado:** Lista retornada contém o mesmo vídeo repetido ~24 vezes (5s × 24 = 120s). Não lança exceção. Log indica que vídeo foi reutilizado.
- **Casos de borda:** Pasta com 0 vídeos → lança `NoVideosAvailableError`
- **Prioridade:** Alta

---

### 2.7 Módulo: Corte de Vídeos (`US-013`)

---

#### CT-035: Cortar clipe com duração aleatória entre 3-6s

- **US:** US-013
- **Tipo:** Unitário
- **Pré-condição:** Mock do `ffmpeg-python` capturando chamadas. Vídeo de teste `test.mp4` com 30s de duração (arquivo real ou mockado).
- **Passos:**
  1. Chamar `VideoCutter.cut(video_path="/tmp/test.mp4", output_path="/tmp/clip1.mp4")`
  2. Verificar parâmetros passados ao FFmpeg
  3. Executar 20 vezes e coletar durações geradas
- **Resultado esperado:** Cada clipe tem duração entre 3.0s e 6.0s (inclusive). O ponto de início (`-ss`) é aleatório dentro do range `[0, video_duration - clip_duration]`. Nunca inicia além do final do vídeo.
- **Casos de borda:** Vídeo com exatamente 3s de duração → clipe de 3s iniciando em 0s
- **Prioridade:** Alta

---

#### CT-036: Rejeitar vídeo menor que 3 segundos

- **US:** US-013
- **Tipo:** Unitário
- **Pré-condição:** Mock retornando que `short_video.mp4` tem 1.5s de duração via `ffprobe`
- **Passos:**
  1. Chamar `VideoCutter.cut(video_path="/tmp/short_video.mp4", output_path="/tmp/clip.mp4")`
- **Resultado esperado:** Lança `VideoTooShortError("Vídeo short_video.mp4 tem apenas 1.5s — mínimo necessário é 3s")`. Nenhum arquivo de saída criado.
- **Casos de borda:** Vídeo de exatamente 2.99s → mesmo erro. Vídeo de 3.0s → aceito.
- **Prioridade:** Alta

---

#### CT-037: Lidar com FFmpeg não instalado

- **US:** US-013
- **Tipo:** Unitário
- **Pré-condição:** Mock do `shutil.which("ffmpeg")` retornando `None`
- **Passos:**
  1. Chamar qualquer método do `VideoCutter`
- **Resultado esperado:** Lança `FFmpegNotFoundError("FFmpeg não encontrado. Instale em https://ffmpeg.org")` na instanciação ou na primeira chamada. Mensagem inclui instruções de instalação.
- **Casos de borda:** —
- **Prioridade:** Alta

---

#### CT-038: Lidar com vídeo corrompido

- **US:** US-013
- **Tipo:** Unitário
- **Pré-condição:** Arquivo `corrupted.mp4` existindo no disco mas com conteúdo inválido. Mock do ffprobe retornando erro.
- **Passos:**
  1. Chamar `VideoCutter.cut(video_path="/tmp/corrupted.mp4", output_path="/tmp/clip.mp4")`
- **Resultado esperado:** Lança `VideoProcessingError` com mensagem descrevendo o arquivo problemático. Não trava o processo. Job step marca status como `error` com log do erro do FFmpeg.
- **Casos de borda:** Arquivo de vídeo com extensão válida mas que é na verdade um PDF renomeado
- **Prioridade:** Alta

---

### 2.8 Módulo: Sequenciamento Anti-Plágio (`US-014`)

> Seção detalhada também na **Seção 4**.

---

#### CT-039: Validar sequenciamento básico com 3 vídeos

- **US:** US-014
- **Tipo:** Unitário
- **Pré-condição:** Lista de clipes de entrada:
  ```python
  clips = [
      Clip(video_id="v1", start=0, duration=4),
      Clip(video_id="v1", start=5, duration=3),
      Clip(video_id="v2", start=0, duration=5),
      Clip(video_id="v2", start=6, duration=4),
      Clip(video_id="v3", start=0, duration=3),
  ]
  ```
- **Passos:**
  1. Chamar `VideoSequencer.sequence(clips)`
  2. Verificar lista retornada
  3. Percorrer sequência e verificar consecutivos
- **Resultado esperado:** Lista retornada com 5 clipes onde `sequence[i].video_id != sequence[i+1].video_id` para todo `i`. Todos os 5 clipes originais presentes na saída.
- **Casos de borda:** —
- **Prioridade:** Alta

---

#### CT-040: Sequenciamento com lista vazia de clipes

- **US:** US-014
- **Tipo:** Unitário
- **Pré-condição:** —
- **Passos:**
  1. Chamar `VideoSequencer.sequence([])`
- **Resultado esperado:** Retorna lista vazia `[]`. Não lança exceção.
- **Casos de borda:** Lista com 1 único clipe → retorna lista com esse clipe
- **Prioridade:** Média

---

#### CT-041: Garantir que todos os clipes estão presentes após sequenciamento

- **US:** US-014
- **Tipo:** Unitário
- **Pré-condição:** Lista de 10 clipes de 3 vídeos diferentes
- **Passos:**
  1. Chamar `VideoSequencer.sequence(clips)`
  2. Verificar contagem de clipes de entrada vs saída
  3. Verificar que nenhum clipe foi perdido ou duplicado
- **Resultado esperado:** `len(result) == len(clips)`. Cada clipe original aparece exatamente uma vez na saída. `set(result) == set(clips)`.
- **Casos de borda:** —
- **Prioridade:** Alta

---

### 2.9 Módulo: Composição de Vídeo (`US-015`, `US-016`)

---

#### CT-042: Compor vídeo final 16:9 com áudio

- **US:** US-015
- **Tipo:** Unitário
- **Pré-condição:** Lista de clipes cortados (arquivos MP4 reais em diretório temporário). Arquivo de áudio MP3 real. Mock do `ffmpeg-python` capturando comandos gerados.
- **Passos:**
  1. Chamar `VideoComposer.compose(clips=[...], audio_path="/tmp/audio.mp3", output_path="/tmp/final.mp4", dimension="16:9")`
  2. Verificar que output file foi criado
  3. Verificar codec do arquivo de saída
- **Resultado esperado:** Arquivo `final.mp4` criado. Codec de vídeo: `H.264` (`libx264`). Codec de áudio: `AAC` (`aac`). Duração do vídeo final ≈ duração do áudio (±0.5s). Dimensão 16:9 mantida.
- **Casos de borda:** —
- **Prioridade:** Alta

---

#### CT-043: Compor vídeo 9:16 com crop centralizado

- **US:** US-016
- **Tipo:** Unitário
- **Pré-condição:** Vídeo fonte em 16:9 (1920×1080). Opção `crop=True` para 9:16.
- **Passos:**
  1. Chamar `VideoComposer.compose(..., dimension="9:16", crop=True)`
  2. Verificar filtros FFmpeg aplicados
- **Resultado esperado:** Filtro `crop` aplicado centralizando horizontalmente: `crop=1080:1920` não; `crop=ih*9/16:ih` correto para vídeo horizontal → para gerar 9:16 a partir de 16:9, o filtro deve ser `crop=in_h*9/16:in_h` aplicado ao centro. Output tem dimensão 1080×1920 (ou múltiplos).
- **Casos de borda:** Vídeo fonte já em 9:16 → sem transformação necessária
- **Prioridade:** Alta

---

#### CT-044: Compor vídeo 9:16 com barras pretas (sem crop)

- **US:** US-016
- **Tipo:** Unitário
- **Pré-condição:** Vídeo fonte em 16:9. Opção `crop=False` para 9:16.
- **Passos:**
  1. Chamar `VideoComposer.compose(..., dimension="9:16", crop=False)`
  2. Verificar filtro FFmpeg `pad` aplicado
- **Resultado esperado:** Filtro `pad` aplicado com barras pretas nas laterais para atingir aspect ratio 9:16. Vídeo centralizado horizontalmente. Conteúdo original não cortado.
- **Casos de borda:** —
- **Prioridade:** Média

---

#### CT-045: Duração do áudio maior que a soma dos clipes

- **US:** US-015
- **Tipo:** Unitário
- **Pré-condição:** 3 clipes totalizando 25s. Áudio com 30s de duração.
- **Passos:**
  1. Chamar `VideoComposer.compose(clips=[...25s total...], audio_path="30s_audio.mp3", ...)`
  2. Verificar comportamento
- **Resultado esperado:** Vídeo final tem duração = duração do áudio (30s). Os clipes são repetidos (loop) ou o último frame é estendido para cobrir a diferença. Não lança exceção — é um aviso no log.
- **Casos de borda:** Áudio significativamente mais longo que os clipes (ex: clipes = 10s, áudio = 120s)
- **Prioridade:** Média

---

### 2.10 Módulo: Geração de Metadados (`US-017`)

---

#### CT-046: Gerar título com máximo de 100 caracteres

- **US:** US-017
- **Tipo:** Unitário
- **Pré-condição:** Mock do Ollama retornando título longo: `"This Is An Extremely Long Title That Exceeds One Hundred Characters And Should Be Truncated By The System Before Being Used"` (115 chars)
- **Passos:**
  1. Chamar `MetadataGenerator.generate_title(text="narration script...", model="llama3")`
  2. Verificar retorno
- **Resultado esperado:** Título retornado tem no máximo 100 caracteres. Truncamento não corta no meio de uma palavra. `len(title) <= 100`.
- **Casos de borda:** Título com exatamente 100 chars → retornado sem modificação. Ollama retornando título vazio → relançar geração ou retornar erro.
- **Prioridade:** Alta

---

#### CT-047: Gerar descrição com máximo de 5000 caracteres

- **US:** US-017
- **Tipo:** Unitário
- **Pré-condição:** Mock do Ollama retornando descrição com 6000 caracteres
- **Passos:**
  1. Chamar `MetadataGenerator.generate_description(text="narration...", model="llama3")`
  2. Verificar retorno
- **Resultado esperado:** Descrição retornada tem no máximo 5000 caracteres. `len(description) <= 5000`. Truncamento respeita limites de frase/parágrafo quando possível.
- **Casos de borda:** Descrição com exatamente 5000 chars → retornada sem modificação
- **Prioridade:** Alta

---

#### CT-048: Geração de metadados com Ollama offline

- **US:** US-017
- **Tipo:** Unitário
- **Pré-condição:** Mock do Ollama lançando `OllamaUnavailableError`
- **Passos:**
  1. Chamar `MetadataGenerator.generate_title(...)` com Ollama mockado offline
- **Resultado esperado:** Lança `MetadataGenerationError` com mensagem clara. Job step registra erro. Pipeline pode continuar se metadados forem editados manualmente (não bloqueia upload se usuário inserir metadados).
- **Casos de borda:** —
- **Prioridade:** Média

---

### 2.11 Módulo: Upload YouTube (`US-018`, `US-019`)

---

#### CT-049: Upload para conta única com sucesso

- **US:** US-018
- **Tipo:** Integração
- **Pré-condição:** Mock da YouTube Data API v3: `POST /upload/youtube/v3/videos` retornando `{"id": "dQw4w9WgXcQ", "status": {"uploadStatus": "uploaded"}}`. Arquivo de vídeo `/tmp/final.mp4` existente (pode ser vazio para testes). Token válido no banco.
- **Passos:**
  1. Chamar `YouTubeUploader.upload(video_path="/tmp/final.mp4", title="Test", description="Desc", account_id=1)`
  2. Verificar retorno
  3. Verificar banco de dados
- **Resultado esperado:** `UploadOutput` com `video_id="dQw4w9WgXcQ"`, `video_url="https://youtube.com/watch?v=dQw4w9WgXcQ"`. Banco atualizado com URL do vídeo publicado. `job.youtube_urls` contém a URL.
- **Casos de borda:** —
- **Prioridade:** Alta

---

#### CT-050: Upload para múltiplas contas sequencialmente

- **US:** US-018
- **Tipo:** Integração
- **Pré-condição:** 3 contas com tokens válidos no banco. Mock da YouTube API configurado para cada conta retornar IDs de vídeo diferentes.
- **Passos:**
  1. Chamar `YouTubeUploader.upload_to_accounts(video_path="/tmp/final.mp4", title="Test", description="Desc", account_ids=[1, 2, 3])`
  2. Verificar retorno
- **Resultado esperado:** 3 uploads realizados sequencialmente. `UploadOutput` contém lista com 3 URLs distintas. Se 1 upload falhar, os outros continuam e o erro é reportado individualmente por conta.
- **Casos de borda:** Todas as contas falhando → retornar lista com erros individuais, não lançar exceção única
- **Prioridade:** Alta

---

#### CT-051: Upload com token expirado — tentativa de refresh e rejeição

- **US:** US-018
- **Tipo:** Integração
- **Pré-condição:** Conta com `access_token` expirado e `refresh_token` inválido. Mock do OAuth retornando `{"error": "invalid_grant"}` no refresh.
- **Passos:**
  1. Tentar upload com conta de token expirado
  2. Verificar que refresh foi tentado
  3. Verificar erro retornado
- **Resultado esperado:** `UploadError("Token expirado para conta #1. Re-autenticação necessária.")`. Job step registra o erro. `youtube_accounts.is_active` atualizado para `false` no banco. Upload não re-tentado infinitamente.
- **Casos de borda:** —
- **Prioridade:** Alta

---

#### CT-052: Agendamento de publicação para data futura

- **US:** US-019
- **Tipo:** Integração
- **Pré-condição:** Job configurado com `scheduled_at = now + 2h`. Mock da YouTube API aceitando upload com `status.privacyStatus="private"` e `status.publishAt`.
- **Passos:**
  1. Criar job com `scheduled_at = datetime.utcnow() + timedelta(hours=2)` via `POST /api/jobs`
  2. Executar pipeline
  3. Verificar chamada à YouTube API
  4. Verificar banco e status no SSE
- **Resultado esperado:** Vídeo enviado ao YouTube com `privacyStatus: "private"` e `publishAt: <data futura>`. Job com status `scheduled` no banco. SSE emite evento com status `scheduled` e data/hora de publicação.
- **Casos de borda:** `scheduled_at` no passado → HTTP 400 na criação do job com mensagem "Data de publicação deve ser no futuro"
- **Prioridade:** Alta

---

#### CT-053: Falha de rede durante upload

- **US:** US-018
- **Tipo:** Integração
- **Pré-condição:** Mock da YouTube API retornando erro de rede na primeira chamada e sucesso na segunda (retry automático)
- **Passos:**
  1. Configurar mock com 1 falha seguida de sucesso
  2. Chamar `YouTubeUploader.upload(...)`
  3. Verificar comportamento de retry
- **Resultado esperado:** Sistema faz pelo menos 1 retry automático com backoff. Se o retry funcionar, upload considerado bem-sucedido. Se todas as tentativas falharem, `UploadError` com detalhes.
- **Casos de borda:** Arquivo de vídeo removido durante o upload → erro específico de arquivo ausente
- **Prioridade:** Média

---

### 2.12 Módulo: Pipeline Runner (`US-020`, `US-021`, `US-022`)

---

#### CT-054: Criar novo job via API

- **US:** US-020
- **Tipo:** Integração
- **Pré-condição:** Banco inicializado. Pelo menos 1 conta YouTube cadastrada.
- **Passos:**
  1. Enviar `POST /api/jobs` com body:
     ```json
     {
       "name": "Test Job",
       "config": {
         "text_mode": "manual",
         "manual_text": "Hello world",
         "tts_voice": "en-US-JennyNeural",
         "target_duration_s": 30,
         "dimension": "16:9",
         "account_ids": [1]
       }
     }
     ```
  2. Verificar resposta e banco
- **Resultado esperado:** HTTP 201 com `{"data": {"job_id": 1, "status": "pending", "name": "Test Job"}}`. Job criado no banco com status `pending`. `job_steps` criados para cada etapa do pipeline com status `pending`.
- **Casos de borda:** `account_ids` vazio → HTTP 400. `name` vazio → HTTP 422. `target_duration_s <= 0` → HTTP 422.
- **Prioridade:** Alta

---

#### CT-055: Iniciar pipeline completo

- **US:** US-020
- **Tipo:** Integração
- **Pré-condição:** Job criado com status `pending`. Todos os serviços mockados para sucesso.
- **Passos:**
  1. Enviar `POST /api/jobs/{id}/run`
  2. Monitorar SSE para eventos de progresso
  3. Verificar status final do job e das steps
- **Resultado esperado:** HTTP 202 (aceito, execução assíncrona). SSE emite eventos para cada etapa: `text_generation`, `audio_generation`, `audio_verification`, `video_selection`, `video_cutting`, `video_sequencing`, `video_composition`, `metadata_generation`, `upload`. Job com status `completed` ao final. Todas as `job_steps` com status `completed`.
- **Casos de borda:** Job já em execução (`running`) → HTTP 409 "Job já está em andamento"
- **Prioridade:** Alta

---

#### CT-056: Executar etapa individual em modo debug

- **US:** US-021
- **Tipo:** Integração
- **Pré-condição:** Job em status `pending`. Etapa `text_generation` com step anterior completado (não necessário para text_generation que é a primeira).
- **Passos:**
  1. Enviar `POST /api/jobs/{id}/steps/text_generation`
  2. Verificar resposta e step no banco
- **Resultado esperado:** HTTP 202. Apenas a etapa `text_generation` é executada. As demais permanecem `pending`. `job_steps` da etapa executada atualizado com `status="completed"`, `output` preenchido, `duration_ms` registrado.
- **Casos de borda:** Executar etapa fora de ordem (ex: `video_cutting` antes de `video_selection`) → deve funcionar em modo debug mas com aviso no log
- **Prioridade:** Alta

---

#### CT-057: Inspecionar output de uma etapa

- **US:** US-022
- **Tipo:** Integração
- **Pré-condição:** Job com etapa `text_generation` completada. `job_steps.output` preenchido com `{"text": "Generated script...", "model": "llama3", "tokens": 450}`.
- **Passos:**
  1. Enviar `GET /api/jobs/{id}/steps/text_generation/output`
  2. Verificar resposta
- **Resultado esperado:** HTTP 200 com `{"data": {"step_name": "text_generation", "status": "completed", "output": {"text": "Generated script...", "model": "llama3", "tokens": 450}, "log": "...", "duration_ms": 2340, "started_at": "...", "completed_at": "..."}}`.
- **Casos de borda:** Etapa ainda não executada → `{"data": {"status": "pending", "output": null}}`
- **Prioridade:** Alta

---

#### CT-058: Cancelar job em andamento

- **US:** US-020
- **Tipo:** Integração
- **Pré-condição:** Job com status `running` (executando etapa `video_cutting`).
- **Passos:**
  1. Iniciar pipeline via `POST /api/jobs/{id}/run`
  2. Aguardar SSE confirmar início da execução
  3. Enviar `DELETE /api/jobs/{id}`
  4. Aguardar SSE de cancelamento
  5. Verificar status do job
- **Resultado esperado:** Job com status `cancelled`. Etapa em andamento marcada como `error` ou `cancelled`. Arquivos temporários gerados até o momento são limpos (opcionalmente). SSE emite evento `{"status": "cancelled"}`.
- **Casos de borda:** Job já `completed` → DELETE retorna HTTP 400 "Job já finalizado, não pode ser cancelado"
- **Prioridade:** Alta

---

#### CT-059: Falha em etapa interrompe pipeline

- **US:** US-020
- **Tipo:** Integração
- **Pré-condição:** Mock da etapa `audio_generation` configurado para lançar `AudioGenerationError`.
- **Passos:**
  1. Iniciar pipeline com mock de falha em `audio_generation`
  2. Monitorar SSE
  3. Verificar estado final
- **Resultado esperado:** Pipeline para na etapa `audio_generation`. Job com status `error`. `error_message` do job preenchido com detalhes da falha. `job_steps` das etapas subsequentes permanecem `pending`. SSE emite evento com `status: "error"` e a etapa que falhou.
- **Casos de borda:** —
- **Prioridade:** Alta

---

#### CT-060: Listar jobs com paginação e filtro por status

- **US:** US-020
- **Tipo:** Integração
- **Pré-condição:** 20 jobs no banco: 5 `pending`, 5 `running`, 5 `completed`, 5 `error`
- **Passos:**
  1. Enviar `GET /api/jobs?status=completed&page=1&page_size=3`
  2. Verificar resposta
- **Resultado esperado:** HTTP 200 com lista de 3 jobs (paginação aplicada). Todos os jobs retornados têm `status="completed"`. Body contém metadados de paginação: `{"data": {"jobs": [...], "total": 5, "page": 1, "page_size": 3, "pages": 2}}`.
- **Casos de borda:** `page=999` → retornar lista vazia (não HTTP 404). Sem filtro → retornar todos ordenados por `created_at DESC`.
- **Prioridade:** Média

---

### 2.13 Módulo: SSE (Server-Sent Events) (`US-020`)

---

#### CT-061: Conexão SSE recebe eventos de job em andamento

- **US:** US-020
- **Tipo:** Integração
- **Pré-condição:** Backend rodando. Job criado e pipeline iniciado.
- **Passos:**
  1. Abrir conexão SSE via `GET /api/sse/jobs/{id}` com `Accept: text/event-stream`
  2. Iniciar pipeline do job
  3. Coletar eventos recebidos
- **Resultado esperado:** Eventos recebidos no formato `event: job_update\ndata: {...}\n\n`. Cada transição de etapa gera ao menos 1 evento. Evento final com `status: "completed"`. Conexão permanece aberta até conclusão do job.
- **Casos de borda:** Job já `completed` quando cliente conecta → deve enviar o estado atual imediatamente e fechar (ou manter aberta)
- **Prioridade:** Alta

---

#### CT-062: SSE de todos os jobs

- **US:** US-020
- **Tipo:** Integração
- **Pré-condição:** 3 jobs simultâneos em diferentes etapas
- **Passos:**
  1. Abrir conexão SSE via `GET /api/sse/jobs`
  2. Verificar que eventos de todos os 3 jobs são recebidos
- **Resultado esperado:** Eventos de todos os jobs ativos aparecem no stream. Cada evento contém `job_id` para identificação. Eventos de jobs diferentes são intercalados conforme ocorrem.
- **Casos de borda:** Nenhum job ativo → conexão mantida (sem fechar), aguardando próximos eventos
- **Prioridade:** Média

---

#### CT-063: Reconexão automática após queda do SSE

- **US:** US-020
- **Tipo:** E2E (Playwright)
- **Pré-condição:** Job em andamento. Cliente SSE conectado no frontend.
- **Passos:**
  1. Conectar ao SSE pelo frontend (Dashboard)
  2. Simular queda de conexão (desconectar rede por 2s)
  3. Reconectar rede
  4. Verificar que SSE reconecta automaticamente
- **Resultado esperado:** Browser tenta reconectar automaticamente (comportamento padrão do `EventSource`). Ao reconectar, estado atual do job é exibido atualizado. Nenhuma mensagem de erro permanente no UI.
- **Casos de borda:** —
- **Prioridade:** Média

---

### 2.14 Módulo: Frontend — Stores Pinia

---

#### CT-064: Store de jobs atualiza via SSE

- **US:** US-020
- **Tipo:** Unitário (Vitest)
- **Pré-condição:** Store `useJobsStore()` instanciado. Mock de SSE configurado com `MSW` ou `vi.mock`.
- **Passos:**
  1. Inicializar store com job `{id: 1, status: "pending"}`
  2. Simular recebimento de evento SSE: `{job_id: 1, status: "running", current_step: "text_generation", progress: 10}`
  3. Verificar estado da store
- **Resultado esperado:** `jobsStore.jobs[0].status === "running"`. `jobsStore.jobs[0].progress === 10`. Store reativo atualiza componentes automaticamente.
- **Casos de borda:** Evento SSE para job inexistente na store → job adicionado automaticamente
- **Prioridade:** Alta

---

#### CT-065: Store de contas lista e remove

- **US:** US-004
- **Tipo:** Unitário (Vitest)
- **Pré-condição:** Mock de `GET /api/accounts` retornando 2 contas. Mock de `DELETE /api/accounts/1` retornando HTTP 200.
- **Passos:**
  1. Chamar `accountsStore.fetchAccounts()`
  2. Verificar `accountsStore.accounts.length === 2`
  3. Chamar `accountsStore.removeAccount(1)`
  4. Verificar `accountsStore.accounts.length === 1`
- **Resultado esperado:** Store atualiza estado local após remoção bem-sucedida. Não recarrega todos os dados desnecessariamente.
- **Casos de borda:** Falha na API ao remover → store reverte estado, exibe erro
- **Prioridade:** Média

---

### 2.15 Segurança Geral

---

#### CT-066: Tokens OAuth não expostos na API

- **US:** US-003, US-004
- **Tipo:** Segurança
- **Pré-condição:** Conta com tokens OAuth no banco
- **Passos:**
  1. Enviar `GET /api/accounts`
  2. Verificar todos os campos retornados
  3. Enviar `GET /api/accounts/{id}` (se existir)
  4. Verificar todos os campos
- **Resultado esperado:** Campo `credentials` (tokens OAuth) **nunca** aparece em nenhuma resposta da API. Somente: `id`, `name`, `channel_id`, `email`, `avatar_url`, `is_active`, `created_at`.
- **Casos de borda:** Checar todos os endpoints que retornam dados de conta
- **Prioridade:** Alta

---

#### CT-067: Injeção de path em etapas de vídeo

- **US:** US-013, US-015
- **Tipo:** Segurança
- **Pré-condição:** —
- **Passos:**
  1. Enviar `POST /api/jobs/{id}/steps/video_cutting` com input: `{"video_path": "/etc/passwd"}`
  2. Enviar com `{"video_path": "../../../../etc/shadow"}`
  3. Verificar comportamento
- **Resultado esperado:** Ambas as tentativas retornam HTTP 400 com erro de validação. Sistema verifica que o path está dentro da pasta de vídeos configurada antes de processar. Nenhum arquivo fora da pasta autorizada é acessado.
- **Casos de borda:** Path com null bytes: `"/tmp/video\x00.mp4"`
- **Prioridade:** Alta

---

#### CT-068: SQL Injection em campos de texto

- **US:** US-006, US-020
- **Tipo:** Segurança
- **Pré-condição:** —
- **Passos:**
  1. Criar job com `name = "'; DROP TABLE processing_jobs; --"`
  2. Criar job com `config.manual_text = "' OR '1'='1"`
  3. Verificar que banco não é afetado
- **Resultado esperado:** SQLAlchemy utiliza queries parametrizadas — injeção SQL não é possível. Strings são salvas literalmente no banco. Nenhuma tabela é afetada.
- **Casos de borda:** —
- **Prioridade:** Alta

---

#### CT-069: Validação de CORS

- **US:** N/A (infraestrutura)
- **Tipo:** Segurança
- **Pré-condição:** Backend rodando na porta 8000
- **Passos:**
  1. Enviar requisição com `Origin: http://evil-site.com`
  2. Verificar headers de resposta
- **Resultado esperado:** Headers `Access-Control-Allow-Origin` restritos apenas a origens permitidas (localhost/frontend). Origem maliciosa não é listada nos headers.
- **Casos de borda:** —
- **Prioridade:** Alta

---

## 3. Casos Críticos que NÃO PODEM Falhar

Os 10 cenários abaixo bloqueiam o MVP caso falhem. São os primeiros a serem executados em qualquer rodada de regressão.

| # | Caso de Teste | Módulo | Impacto |
|---|---|---|---|
| **1** | **CT-039 + CT-041**: Sequenciador anti-plágio nunca coloca dois clipes consecutivos do mesmo vídeo E preserva todos os clipes | `sequencer.py` | Produto sem anti-plágio não tem razão de existir |
| **2** | **CT-055**: Pipeline completo conclui com sucesso (todos os mocks respondendo OK) | `pipeline/runner.py` | Fluxo principal do produto |
| **3** | **CT-049**: Upload para YouTube com token válido retorna URL do vídeo publicado | `youtube/uploader.py` | Resultado final entregue ao usuário |
| **4** | **CT-010**: Callback OAuth com código válido cria conta no banco com tokens criptografados | `youtube/auth.py` | Sem conta OAuth, upload impossível |
| **5** | **CT-051**: Upload com token expirado tenta refresh e, se falhar, reporta erro claro (não fica em loop) | `youtube/uploader.py` | Falha silenciosa perderia jobs já processados |
| **6** | **CT-059**: Falha em qualquer etapa do pipeline interrompe o pipeline e marca job como `error` com mensagem clara | `pipeline/runner.py` | Estado inconsistente no banco é inaceitável |
| **7** | **CT-025 + CT-026**: edge-tts gera áudio e duração real é verificada e registrada | `audio/edge_tts.py` | Duração errada quebra toda a seleção/corte de vídeo |
| **8** | **CT-035**: Cutter gera clipes com duração entre 3-6s e ponto de início aleatório dentro do vídeo | `video/cutter.py` | Clipes fora do range ou início inválido corrompem o vídeo |
| **9** | **CT-061**: Frontend recebe atualizações de status via SSE em tempo real durante execução do pipeline | `api/sse.py` | Usuário sem feedback visual abandona o sistema |
| **10** | **CT-012**: Callback OAuth rejeita state CSRF inválido sem criar conta | `youtube/auth.py` | Vulnerabilidade de segurança crítica |

---

## 4. Cenários do Algoritmo Anti-Plágio

O `VideoSequencer` é o módulo de maior risco do sistema. Falhas silenciosas (sequência inválida gerada sem erro) são o pior cenário. Os testes abaixo foram projetados para cobrir todas as combinações relevantes.

---

### AP-001: Apenas 1 vídeo disponível na pasta

- **US:** US-014
- **Tipo:** Unitário
- **Pré-condição:** Lista de clipes com apenas 1 `video_id`:
  ```python
  clips = [
      Clip(video_id="v1", start=0, duration=4),
      Clip(video_id="v1", start=5, duration=5),
      Clip(video_id="v1", start=11, duration=3),
      Clip(video_id="v1", start=15, duration=6),
  ]
  ```
- **Passos:**
  1. Chamar `VideoSequencer.sequence(clips)`
  2. Verificar sequência retornada
  3. Verificar se variação de velocidade foi aplicada
- **Resultado esperado:** Como não há múltiplos vídeos, o algoritmo entra no fallback: aplica variação de velocidade leve (0.95x–1.05x) em cada clipe. Sequência contém todos os 4 clipes. Log registra: `"Apenas 1 fonte de vídeo disponível — variação de velocidade aplicada como fallback anti-plágio"`. **Nunca** lança exceção.
- **Casos de borda:** 1 único clipe com 1 único vídeo → retorna lista com 1 clipe + flag de variação

---

### AP-002: 2 vídeos com quantidade igual de clipes

- **US:** US-014
- **Tipo:** Unitário
- **Pré-condição:**
  ```python
  clips = [
      Clip(video_id="v1", start=0, duration=4),
      Clip(video_id="v1", start=5, duration=5),
      Clip(video_id="v2", start=0, duration=3),
      Clip(video_id="v2", start=4, duration=6),
  ]
  ```
- **Passos:**
  1. Chamar `VideoSequencer.sequence(clips)`
  2. Verificar sequência
  3. Verificar alternância perfeita
- **Resultado esperado:** Sequência alterna perfeitamente: `[v1, v2, v1, v2]` ou `[v2, v1, v2, v1]`. Nenhum consecutivo do mesmo vídeo. 4 clipes na saída. Todos os clipes presentes.
- **Propriedade a validar:** `all(seq[i].video_id != seq[i+1].video_id for i in range(len(seq)-1))`

---

### AP-003: 2 vídeos com quantidade desigual de clipes

- **US:** US-014
- **Tipo:** Unitário
- **Pré-condição:**
  ```python
  clips = [
      Clip(video_id="v1", start=0, duration=4),   # v1 tem 4 clipes
      Clip(video_id="v1", start=5, duration=3),
      Clip(video_id="v1", start=9, duration=5),
      Clip(video_id="v1", start=15, duration=4),
      Clip(video_id="v2", start=0, duration=6),   # v2 tem 2 clipes
      Clip(video_id="v2", start=7, duration=3),
  ]
  ```
- **Passos:**
  1. Chamar `VideoSequencer.sequence(clips)`
  2. Verificar 6 clipes na saída
  3. Verificar ausência de consecutivos do mesmo vídeo
  4. Verificar o que acontece com os 2 clipes excedentes de v1 (após esgotar v2)
- **Resultado esperado:** Primeiros 4 clipes alternam `[v1, v2, v1, v2]`. Os 2 clipes restantes de v1 entram com fallback de velocidade: `[..., v1(0.97x), v1(1.03x)]`. **Nenhuma** violação de consecutivos entre os primeiros 4. Os últimos 2 clipes de v1 não violam a regra entre si pois o fallback de velocidade os diferencia. Log indica uso do fallback.
- **Resultado alternativo aceitável:** Sistema repete clipes de v2 para entrelaçar com os excedentes de v1 — desde que a regra de não-consecutivos seja mantida.

---

### AP-004: 5 vídeos com distribuição variada de clipes

- **US:** US-014
- **Tipo:** Unitário
- **Pré-condição:**
  ```python
  # v1=6 clipes, v2=4 clipes, v3=3 clipes, v4=2 clipes, v5=1 clipe — total=16 clipes
  clips = gerar_clips_para_teste({"v1": 6, "v2": 4, "v3": 3, "v4": 2, "v5": 1})
  ```
- **Passos:**
  1. Chamar `VideoSequencer.sequence(clips)`
  2. Iterar sequência verificando todos os pares consecutivos
  3. Verificar que todos 16 clipes estão presentes
  4. Calcular distribuição de cada vídeo na sequência
- **Resultado esperado:** 16 clipes na saída. **Nenhum** par `(seq[i], seq[i+1])` com mesmo `video_id`. Distribuição equilibrada dos 5 vídeos ao longo da sequência.
- **Casos de borda:** Executar 100 vezes com clips idênticos e verificar que a propriedade nunca é violada (teste de invariante)

---

### AP-005: Validação automatizada da invariante anti-plágio (Property-Based Testing)

- **US:** US-014
- **Tipo:** Unitário (hypothesis)
- **Pré-condição:** Biblioteca `hypothesis` instalada
- **Passos:**
  1. Usar `@given(st.lists(...))` para gerar listas aleatórias de clipes com 1-10 vídeos distintos
  2. Para cada lista gerada, chamar `VideoSequencer.sequence(clips)`
  3. Verificar propriedade: sem consecutivos do mesmo vídeo
  4. Verificar propriedade: todos os clipes presentes
- **Resultado esperado:** Para qualquer entrada válida (lista não-vazia com pelo menos 1 clipe por vídeo), o sequenciador nunca viola as propriedades. Se `hypothesis` encontrar um contraexemplo, ele é reportado com o input mínimo reprodutível.
- **Prioridade:** Alta (substitui centenas de testes manuais de casos de borda)

---

### AP-006: Performance do sequenciador com 500 clipes

- **US:** US-014
- **Tipo:** Performance
- **Pré-condição:** Lista de 500 clipes distribuídos em 10 vídeos
- **Passos:**
  1. Gerar lista de 500 clipes (50 por vídeo)
  2. Medir tempo de execução de `VideoSequencer.sequence(clips)`
  3. Verificar resultado
- **Resultado esperado:** Tempo de execução < 100ms. Algoritmo com complexidade O(n log n) usando heap. Propriedade de não-consecutivos mantida em todos os 500 clipes.
- **Casos de borda:** —
- **Prioridade:** Média

---

## 5. Cenários E2E do Pipeline Completo

---

### E2E-001: Pipeline completo com IA (Ollama + TTS + Vídeo + Upload)

- **Ferramentas:** Playwright + mocks de serviços externos
- **US:** US-006, US-009, US-012–US-015, US-017, US-018

**Configuração de ambiente:**
- Backend rodando em `http://localhost:8000`
- Frontend em `http://localhost:5173`
- Mock do Ollama: servidor HTTP local simulando respostas
- Mock do edge-tts: retorna MP3 de 30s pré-gerado
- Mock do FFmpeg: aceita comandos, copia arquivo de saída pré-existente
- Mock da YouTube API: aceita upload, retorna ID de vídeo fictício
- Pasta `/tmp/e2e_videos/` com 3 vídeos MP4 de teste (30s cada)

**Pré-condições:**
- Configurações definidas: Ollama URL, pasta de vídeos, TTS voice
- 1 conta YouTube conectada (tokens mockados válidos)

**Passos:**

| # | Ação do Usuário | Verificação |
|---|---|---|
| 1 | Navegar para `/` (Dashboard) | Dashboard carregado sem erros de console |
| 2 | Clicar em "Novo Processamento" | Modal/página de criação de job aberta |
| 3 | Selecionar modo "Gerar com IA" | Campo de prompt visível e habilitado |
| 4 | Inserir prompt: `"Write a 30-second script about the importance of sleep"` | Prompt inserido no campo |
| 5 | Selecionar modelo Ollama: `"llama3"` | Modelo selecionado |
| 6 | Configurar duração alvo: 30 segundos | Valor 30 no campo de duração |
| 7 | Selecionar voz: `"en-US-JennyNeural"` | Voz selecionada |
| 8 | Selecionar dimensão: `"16:9"` | Opção 16:9 marcada |
| 9 | Selecionar conta YouTube: `"Canal de Teste"` | Checkbox da conta marcado |
| 10 | Clicar em "Criar e Executar" | Redirecionamento para tela de acompanhamento do job |
| 11 | Aguardar etapa `text_generation` no SSE | Barra de progresso atualizada, etapa exibida |
| 12 | Aguardar etapa `audio_generation` | Progresso avançado |
| 13 | Aguardar etapas de vídeo (selection → cutting → sequencing → composition) | Progresso avançado a cada etapa |
| 14 | Aguardar `metadata_generation` | Título e descrição exibidos no UI |
| 15 | Aguardar `upload` | Progresso do upload exibido |
| 16 | Verificar conclusão | Status `Concluído` com link para o vídeo no YouTube |

**Resultado esperado:**
- Job com status `completed` no banco
- Todas as 9 etapas com status `completed`
- URL do YouTube exibida e clicável na interface
- Sem erros de console no browser
- Duração total do E2E: < 2 minutos (com mocks)

---

### E2E-002: Pipeline com texto manual (sem IA)

- **Ferramentas:** Playwright
- **US:** US-007, US-009, US-015, US-018

**Pré-condições:** Mesmas do E2E-001, exceto que Ollama mock não precisa responder para geração de texto.

**Passos:**

| # | Ação | Verificação |
|---|---|---|
| 1 | Navegar para "Novo Processamento" | Página carregada |
| 2 | Selecionar modo "Texto Manual" | Toggle muda para manual; campo de prompt substitui campo de textarea |
| 3 | Inserir texto: `"Good morning everyone. Today we will talk about healthy habits that can transform your life."` | Texto inserido (91 chars) |
| 4 | Configurar duração alvo: 15s | Valor configurado |
| 5 | Selecionar conta e clicar "Executar" | Job criado |
| 6 | Verificar etapa `text_generation` no acompanhamento | Deve completar IMEDIATAMENTE (< 1s) sem chamada ao Ollama |
| 7 | Acompanhar demais etapas | Progresso normal |
| 8 | Verificar conclusão | Status `completed` |

**Resultado esperado:**
- Etapa `text_generation` completada sem nenhuma chamada ao mock do Ollama (verificar que mock.call_count == 0)
- Output da etapa `text_generation` contém o texto inserido manualmente exatamente como digitado
- Pipeline completa com sucesso

---

### E2E-003: Pipeline com agendamento de publicação

- **Ferramentas:** Playwright + APScheduler mock
- **US:** US-019, US-020

**Pré-condições:** Mesmas do E2E-001.

**Passos:**

| # | Ação | Verificação |
|---|---|---|
| 1 | Criar job com texto manual | — |
| 2 | Na seção de upload, selecionar "Agendar publicação" | Datepicker + timepicker aparecem |
| 3 | Configurar data/hora: amanhã às 10:00 | Data futura configurada |
| 4 | Clicar "Criar e Executar" | Job criado |
| 5 | Acompanhar pipeline até etapa `upload` | Progresso normal até upload |
| 6 | Na etapa de upload: verificar que vídeo é enviado como `privado` | Mock da YouTube API registra `privacyStatus: "private"` |
| 7 | Verificar que `publishAt` foi configurado na chamada à API | Data futura correta no mock |
| 8 | Verificar status final | Status `scheduled` (não `completed`) no dashboard |
| 9 | Verificar data de publicação exibida na lista de jobs | Data/hora configurada aparece na UI |
| 10 | Tentar criar job com data no passado | Validação no formulário bloqueia envio com mensagem de erro |

**Resultado esperado:**
- Job com status `scheduled` no banco, campo `scheduled_at` preenchido
- YouTube API chamada com `status.publishAt` correto
- Vídeo na lista de jobs mostra badge `Agendado` e a data/hora
- Tentativa com data passada rejeitada no frontend (validação client-side) E no backend (HTTP 400)

---

### E2E-004: Debug de pipeline por etapas individuais

- **Ferramentas:** Playwright
- **US:** US-021, US-022

**Pré-condições:** Job criado com status `pending`. Modo debug ativo.

**Passos:**

| # | Ação | Verificação |
|---|---|---|
| 1 | Abrir detalhe do job | Tela com lista de etapas exibida |
| 2 | Clicar "Executar" na etapa `text_generation` | Apenas essa etapa é executada |
| 3 | Aguardar conclusão da etapa | Status muda para `completed` com ícone verde |
| 4 | Clicar em "Ver Output" da etapa `text_generation` | Modal/painel com o texto gerado + metadata |
| 5 | Verificar que demais etapas ainda são `pending` | Etapas 2-9 permanecem inalteradas |
| 6 | Clicar "Executar" na etapa `audio_generation` | Apenas audio_generation executa |
| 7 | Verificar player de áudio no output | Player de áudio funcional exibido na UI |
| 8 | Clicar "Executar" na etapa `video_selection` | — |
| 9 | Verificar log de vídeos selecionados no output | Nomes dos vídeos selecionados listados |

**Resultado esperado:**
- Cada etapa pode ser executada de forma completamente isolada
- Output de cada etapa é visualizável na UI com formato adequado (texto, player de áudio, preview de vídeo)
- Etapas não executadas permanecem inalteradas
- Log detalhado de cada etapa com timestamp e duração em ms

---

## 6. Matriz de Rastreabilidade

| User Story | Casos de Teste |
|---|---|
| **US-001** — Configuração inicial | CT-001, CT-002, CT-003, CT-004, CT-005 |
| **US-002** — Listar modelos Ollama | CT-006, CT-007, CT-008 |
| **US-003** — Conectar conta YouTube OAuth2 | CT-009, CT-010, CT-011, CT-012 |
| **US-004** — Gerenciar contas | CT-013, CT-014, CT-015, CT-016, CT-017, CT-066 |
| **US-005** — Selecionar contas para upload | CT-050, CT-054 (campo account_ids) |
| **US-006** — Gerar texto via Ollama | CT-018, CT-019, CT-020, CT-021 |
| **US-007** — Texto manual | CT-022, E2E-002 |
| **US-008** — Geração em lote | CT-023, CT-024 |
| **US-009** — Gerar áudio TTS com duração alvo | CT-025, CT-026, CT-027, CT-028, CT-029 |
| **US-010** — Selecionar voz TTS | CT-030 |
| **US-011** — Configurar pasta de vídeos | CT-031, CT-032 |
| **US-012** — Selecionar vídeos por duração | CT-033, CT-034 |
| **US-013** — Cortes anti-plágio | CT-035, CT-036, CT-037, CT-038 |
| **US-014** — Sequenciamento anti-plágio | CT-039, CT-040, CT-041, AP-001 a AP-006 |
| **US-015** — Montar vídeo final | CT-042, CT-045 |
| **US-016** — Suporte 16:9 e 9:16 | CT-043, CT-044 |
| **US-017** — Gerar título e descrição | CT-046, CT-047, CT-048 |
| **US-018** — Upload para YouTube | CT-049, CT-050, CT-051, CT-053, E2E-001 |
| **US-019** — Agendamento de publicação | CT-052, E2E-003 |
| **US-020** — Dashboard de status em tempo real | CT-054, CT-055, CT-058, CT-060, CT-061, CT-062, CT-063, CT-064 |
| **US-021** — Executar etapas individuais | CT-056, E2E-004 |
| **US-022** — Inspecionar output das etapas | CT-057, E2E-004 |

**Segurança (transversal):** CT-005, CT-012, CT-066, CT-067, CT-068, CT-069

---

## 7. Ambiente de Teste

### 7.1 Estrutura de Pastas de Teste

```
backend/tests/
├── conftest.py                  # Fixtures globais: db, client, mocks base
├── unit/
│   ├── test_sequencer.py        # CT-039 a CT-041, AP-001 a AP-006
│   ├── test_cutter.py           # CT-035 a CT-038
│   ├── test_selector.py         # CT-031 a CT-034
│   ├── test_composer.py         # CT-042 a CT-045
│   ├── test_ollama_generator.py # CT-018 a CT-021
│   ├── test_edge_tts.py         # CT-025 a CT-030
│   ├── test_metadata.py         # CT-046 a CT-048
│   └── test_uploader.py         # CT-049 a CT-053
├── integration/
│   ├── test_api_settings.py     # CT-001 a CT-005
│   ├── test_api_ollama.py       # CT-006 a CT-008
│   ├── test_api_accounts.py     # CT-009 a CT-017
│   ├── test_api_jobs.py         # CT-054 a CT-060
│   └── test_api_sse.py          # CT-061 a CT-063
└── security/
    └── test_security.py         # CT-066 a CT-069

frontend/src/__tests__/
├── stores/
│   ├── test_jobs_store.ts       # CT-064
│   └── test_accounts_store.ts   # CT-065
└── components/
    ├── test_job_card.ts
    └── test_step_debugger.ts

e2e/
├── pipeline_with_ai.spec.ts     # E2E-001
├── pipeline_manual.spec.ts      # E2E-002
├── pipeline_scheduled.spec.ts   # E2E-003
└── debug_pipeline.spec.ts       # E2E-004
```

---

### 7.2 Mocks Necessários

#### Backend (pytest-mock / respx)

| Dependência externa | Biblioteca de mock | O que mockar |
|---|---|---|
| **Ollama** | `respx` (mock HTTP) ou `pytest-mock` | `GET /api/tags`, `POST /api/generate`, `POST /api/chat` |
| **edge-tts** | `pytest-mock` (`AsyncMock`) | `edge_tts.Communicate.save()`, `edge_tts.list_voices()` |
| **FFmpeg** | `pytest-mock` | `ffmpeg.input()`, `ffmpeg.run()`, `shutil.which("ffmpeg")` |
| **YouTube Data API** | `pytest-mock` + `responses` | `googleapiclient.discovery.build()`, upload, channels.list |
| **Google OAuth** | `pytest-mock` | `google_auth_oauthlib.flow.Flow.fetch_token()` |
| **Sistema de arquivos** | `tmp_path` (pytest built-in) | Criar arquivos de vídeo/áudio de teste reais em diretório temporário |

#### Frontend (Vitest / MSW)

| Dependência | Mock | Como |
|---|---|---|
| **Axios (API calls)** | `MSW (Mock Service Worker)` | `rest.get('/api/accounts', ...)` handlers |
| **SSE client** | `vi.mock('../services/sse')` | Simular eventos SSE disparados manualmente |
| **Vue Router** | `createMemoryHistory()` | Evitar navegação real nos testes de componente |

#### E2E (Playwright)

| Serviço | Strategy |
|---|---|
| **Ollama** | Servidor HTTP mínimo em Python (`http.server`) na porta 11434 retornando respostas fixas |
| **edge-tts** | Stub que copia arquivo `fixtures/test_audio_30s.mp3` para o path solicitado |
| **FFmpeg** | Shell script stub `ffmpeg` que copia arquivos de fixture sem processar |
| **YouTube API** | `playwright.route()` interceptando chamadas `https://www.googleapis.com/*` |

---

### 7.3 Fixtures e Dados de Teste

#### `conftest.py` (backend)

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.database import Base, get_db
from app.main import app

# Banco em memória para cada teste
@pytest.fixture(scope="function")
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    # Inserir dados padrão das configurações
    session.execute(text("""INSERT INTO system_settings (key, value) VALUES
        ('ollama_url', 'http://localhost:11434'),
        ('ollama_model', 'llama3'),
        ('videos_folder', '/tmp/test_videos'),
        ('tts_voice', 'en-US-JennyNeural'),
        ('default_dimension', '16:9'),
        ('clip_min_duration', '3'),
        ('clip_max_duration', '6')
    """))
    session.commit()
    yield session
    session.close()
    Base.metadata.drop_all(engine)

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

# Conta YouTube de teste
@pytest.fixture
def test_account(db_session):
    account = YouTubeAccount(
        name="Canal de Teste",
        channel_id="UC_TEST_CHANNEL_123",
        email="test@gmail.com",
        avatar_url="https://example.com/avatar.jpg",
        credentials='{"access_token": "test_token", "refresh_token": "test_refresh"}',
        is_active=True
    )
    db_session.add(account)
    db_session.commit()
    return account

# Pasta de vídeos de teste
@pytest.fixture
def test_videos_dir(tmp_path):
    videos_dir = tmp_path / "videos"
    videos_dir.mkdir()
    # Copiar vídeos de fixture (arquivos MP4 mínimos válidos)
    for i in range(1, 4):
        shutil.copy(f"tests/fixtures/test_video_{30*i}s.mp4", videos_dir / f"video{i}.mp4")
    return videos_dir

# Áudio de teste
@pytest.fixture
def test_audio_file(tmp_path):
    audio_path = tmp_path / "test_audio.mp3"
    shutil.copy("tests/fixtures/test_audio_30s.mp3", audio_path)
    return audio_path
```

---

### 7.4 Variáveis de Ambiente para Testes

Criar arquivo `backend/.env.test`:

```bash
# Banco de dados de teste (sobrescrito por in-memory em unitários)
DATABASE_URL=sqlite:///./test.db

# Desativar verificação de certificados TLS em testes
VERIFY_SSL=false

# Credenciais OAuth de teste (não reais — usadas apenas com mocks)
GOOGLE_CLIENT_ID=test-client-id-000000
GOOGLE_CLIENT_SECRET=test-client-secret-000000
GOOGLE_REDIRECT_URI=http://localhost:8000/api/accounts/oauth/callback

# Chave de criptografia de teste para tokens (32 bytes em base64)
ENCRYPTION_KEY=dGVzdC1rZXktMzItYnl0ZXMtZm9yLXRlc3Rpbmch

# Pasta de vídeos de teste (sobrescrita por tmp_path nas fixtures)
VIDEOS_FOLDER=/tmp/test_videos

# Timeout reduzido para testes (ms)
HTTP_TIMEOUT_MS=1000

# Desativar APScheduler em testes unitários
SCHEDULER_ENABLED=false

# Modo de teste: desativa SSE real (usa mock)
TESTING=true
```

Criar arquivo `frontend/.env.test`:

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_SSE_BASE_URL=http://localhost:8000
```

---

### 7.5 Arquivos de Fixture Necessários

| Arquivo | Descrição | Como Obter |
|---|---|---|
| `tests/fixtures/test_video_30s.mp4` | Vídeo MP4 válido 16:9, 30s, H.264 | `ffmpeg -f lavfi -i color=c=blue:size=1280x720:duration=30 -c:v libx264 test_video_30s.mp4` |
| `tests/fixtures/test_video_60s.mp4` | Vídeo MP4 válido 16:9, 60s | Mesmo comando com `duration=60` |
| `tests/fixtures/test_video_90s.mp4` | Vídeo MP4 válido 16:9, 90s | Mesmo comando com `duration=90` |
| `tests/fixtures/test_audio_30s.mp3` | Áudio MP3 válido, 30s, silêncio | `ffmpeg -f lavfi -i anullsrc=r=44100:cl=mono -t 30 -q:a 9 -acodec libmp3lame test_audio_30s.mp3` |
| `tests/fixtures/test_audio_60s.mp3` | Áudio MP3 válido, 60s | Mesmo com `-t 60` |
| `tests/fixtures/corrupted.mp4` | Arquivo MP4 com conteúdo inválido | `echo "not_a_video" > corrupted.mp4` |
| `tests/fixtures/short_video_2s.mp4` | Vídeo MP4 com apenas 2s | `ffmpeg ... duration=2 ...` |

> **Nota:** Os fixtures de vídeo/áudio podem ser gerados automaticamente com um script `tests/generate_fixtures.py` que roda uma única vez no setup do ambiente de CI.

---

### 7.6 Comandos para Execução

```bash
# ============================================
# BACKEND
# ============================================

# Todos os testes
pytest backend/tests/ -v

# Apenas unitários (rápido, < 30s)
pytest backend/tests/unit/ -v

# Apenas integração
pytest backend/tests/integration/ -v

# Apenas segurança
pytest backend/tests/security/ -v

# Com cobertura
pytest backend/tests/ --cov=app --cov-report=html --cov-fail-under=80

# Testes assíncronos (via pytest-asyncio)
pytest backend/tests/ -v --asyncio-mode=auto

# Testes do algoritmo anti-plágio com verbose
pytest backend/tests/unit/test_sequencer.py -v -s

# ============================================
# FRONTEND
# ============================================

# Todos os testes Vitest
npm run test --prefix frontend

# Watch mode durante desenvolvimento
npm run test:watch --prefix frontend

# Com cobertura
npm run test:coverage --prefix frontend

# ============================================
# E2E
# ============================================

# Instalar Playwright
npx playwright install

# Rodar E2E com servidor de mocks
npm run test:e2e

# E2E com UI (debug)
npx playwright test --ui

# ============================================
# ANÁLISE ESTÁTICA DE SEGURANÇA
# ============================================

# Bandit (SAST Python)
bandit -r backend/app/ -f json -o bandit_report.json

# ============================================
# PERFORMANCE
# ============================================

# Locust (SSE com 50 usuários)
locust -f backend/tests/performance/locustfile.py --headless -u 50 -r 10 --run-time 60s
```

---

### 7.7 Pipeline de CI — Integração dos Testes

```yaml
# Sugestão de stages para o pipeline CI/CD

stages:
  - lint-e-sast:
      - ruff check backend/
      - bandit -r backend/app/
      - eslint frontend/src/

  - testes-unitarios:
      - pytest backend/tests/unit/ --cov=app --cov-fail-under=80
      - vitest run frontend/src/__tests__/
      # Falha se cobertura < 80% nos módulos críticos

  - testes-integracao:
      - pytest backend/tests/integration/ -v
      - pytest backend/tests/security/ -v
      # Banco in-memory, mocks de serviços externos

  - testes-e2e:
      - Iniciar backend com mocks de serviços
      - Iniciar frontend em modo test
      - npx playwright test
      # Executado apenas em branches de release e main

  - relatorio-cobertura:
      - Publicar relatório HTML de cobertura como artefato
      - Verificar cobertura mínima por módulo (tabela da seção 1.3)
```

---

*Plano de Testes gerado com base na especificação de produto (22 US) e especificação técnica. Total: 69 casos de teste documentados (CT-001 a CT-069) + 6 cenários anti-plágio (AP-001 a AP-006) + 4 cenários E2E (E2E-001 a E2E-004) = **79 cenários de teste no total**.*
