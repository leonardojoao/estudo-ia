# Plano de Implementação: Composição final de vídeo

## Visão geral

Implementar a TASK-026 para concatenar clipes sequenciados, aplicar a
dimensão configurada, mesclar áudio e retornar metadados do vídeo final.

## Decisões de arquitetura

- Delegar o fluxo síncrono completo a `ProcessPoolExecutor`.
- Criar temporários em `TemporaryDirectory` no diretório-pai do output.
- Manter concatenação, filtragem, merge e probe no mesmo worker para garantir
  limpeza centralizada.
- Reutilizar `VideoCompositionInput`, `VideoCompositionOutput` e
  `FFmpegError`.

## Tarefas

### Fase 1: Preparação e filtros

#### Tarefa 1: Criar lista de concatenação e filtros de dimensão

**Descrição:** Implementar helpers para ordenar clipes, escrever `list.txt` com
paths seguros e produzir os filtergraphs de 16:9 e 9:16.

**Critérios de aceitação:**

- [ ] Clipes são ordenados por `sequence_position`.
- [ ] Paths são escapados no formato do concat demuxer.
- [ ] Filtros cobrem 16:9, 9:16 crop e 9:16 pad.

**Verificação:**

- [ ] Testes unitários verificam ordem, escaping e cada filtro.
- [ ] Ruff e Black passam.

**Dependências:** Nenhuma.

**Arquivos prováveis:**

- `backend/app/services/video/composer.py`
- `backend/tests/test_video_composer.py`

**Escopo estimado:** Médio.

### Fase 2: Composição e metadados

#### Tarefa 2: Implementar worker FFmpeg e API assíncrona

**Descrição:** Executar concatenação, aplicação de filtro, merge de áudio e
probe do resultado em worker separado, removendo temporários em qualquer saída.

**Critérios de aceitação:**

- [ ] Output usa H.264, AAC e `-shortest`.
- [ ] Output 16:9 é 1920x1080.
- [ ] Output 9:16 é 1080x1920.
- [ ] Metadados retornam duração, resolução e tamanho.
- [ ] Falhas incluem stderr em `FFmpegError`.
- [ ] Temporários são removidos em sucesso e erro.

**Verificação:**

- [ ] Testes mockam FFmpeg/probe e validam os comandos.
- [ ] Teste verifica execução via `ProcessPoolExecutor`.
- [ ] Suíte backend passa no container.

**Dependências:** Tarefa 1.

**Arquivos prováveis:**

- `backend/app/services/video/composer.py`
- `backend/tests/test_video_composer.py`
- `docs/tasks-implementacao.md`

**Escopo estimado:** Médio.

### Checkpoint: Composer completo

- [ ] Ruff e Black direcionados passam.
- [ ] Suíte backend passa.
- [ ] `git diff --check` passa.
- [ ] Critérios da TASK-026 marcados como concluídos.
- [ ] Commit funcional separado criado.

## Riscos e mitigação

| Risco | Impacto | Mitigação |
|---|---|---|
| Paths com aspas quebrarem o concat | Alto | Escapar aspas simples conforme sintaxe do demuxer |
| Diretório pai do output não existir | Médio | Criar antes de abrir o `TemporaryDirectory` |
| FFmpeg falhar sem mensagem útil | Médio | Preservar stderr e usar mensagem padrão |
| Temporários permanecerem após erro | Alto | Usar `TemporaryDirectory` em escopo do worker |

## Questões em aberto

- Nenhuma para esta tarefa. O efeito vintage será tratado separadamente.
