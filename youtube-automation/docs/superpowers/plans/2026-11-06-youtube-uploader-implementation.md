# Plano de implementação: Uploader YouTube

## Visão geral

Implementar upload resumable para vídeos locais usando a API YouTube Data v3,
reutilizando as credenciais criptografadas e o refresh OAuth já existentes.

## Fase 1: Contratos

### Tarefa 1: Criar schemas de upload

**Descrição:** Definir inputs/outputs tipados para upload imediato e agendado,
com validações de caminho, título, privacidade e data.

**Critérios de aceite:**
- [ ] `UploadInput` rejeita caminho inexistente e privacidade inválida.
- [ ] `UploadOutput` expõe `video_id` e `youtube_url`.
- [ ] `ScheduleUploadInput` exige data de publicação.

**Verificação:** Testes Pydantic para entradas válidas e inválidas.

**Dependências:** TASK-029.

**Arquivos prováveis:** `app/services/youtube/schemas.py`,
`tests/test_youtube_uploader.py`.

**Escopo:** Pequeno.

## Fase 2: Upload

### Tarefa 2: Implementar upload resumable

**Descrição:** Criar o serviço assíncrono que renova credenciais, configura
`MediaFileUpload` em chunks de 1 MiB, executa `next_chunk` em thread e reporta
progresso.

**Critérios de aceite:**
- [ ] Upload usa `resumable=True` e retorna o ID final.
- [ ] Callback é chamado por chunk.
- [ ] `publish_at` força private e envia `publishAt`.
- [ ] Falhas de refresh desativam a conta.

**Verificação:** Testes com mocks do cliente Google para resposta completa,
progresso, refresh e agendamento.

**Dependências:** Tarefa 1.

**Arquivos prováveis:** `app/services/youtube/uploader.py`,
`tests/test_youtube_uploader.py`.

**Escopo:** Médio.

### Tarefa 3: Mapear erros da API

**Descrição:** Converter `HttpError` para `YouTubeAPIError` com código e
mensagem, incluindo orientação específica para quota excedida.

**Critérios de aceite:**
- [ ] Erro comum preserva status e mensagem.
- [ ] `quotaExceeded` informa meia-noite PT e sugere 01:00 PT.
- [ ] Falhas de arquivo e credenciais não são silenciosas.

**Verificação:** Testes de erro com payloads Google simulados.

**Dependências:** Tarefa 2.

**Arquivos prováveis:** `app/services/youtube/uploader.py`,
`app/core/exceptions.py` se necessário, `tests/test_youtube_uploader.py`.

**Escopo:** Pequeno.

## Checkpoint: Completo

- [ ] Suíte backend passa.
- [ ] Ruff e Black passam.
- [ ] Schemas e serviço estão importáveis sem chamada real ao Google.
- [ ] TASK-030 é marcada no backlog e documentação operacional é atualizada.

## Riscos

| Risco | Impacto | Mitigação |
|---|---|---|
| API síncrona bloquear FastAPI | Alto | Executar loop em `asyncio.to_thread` |
| Resposta de quota variar | Médio | Inspecionar código e detalhes do `HttpError` |
| Refresh falhar durante upload | Alto | Desativar conta e propagar erro de domínio |
