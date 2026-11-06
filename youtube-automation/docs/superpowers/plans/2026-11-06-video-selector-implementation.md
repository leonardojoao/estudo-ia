# Plano de Implementação: Selector de vídeos

## Visão geral

Implementar a TASK-023 do pipeline de vídeo. O serviço irá descobrir arquivos
suportados em uma pasta, extrair seus metadados via `ffmpeg.probe` em threads e
selecionar vídeos aleatoriamente até cobrir a duração solicitada com margem de
segurança, permitindo repetição ilimitada de fontes elegíveis.

## Decisões de arquitetura

- Manter as APIs públicas assíncronas e executar `ffmpeg.probe` com
  `asyncio.to_thread`.
- Reutilizar `VideoFile` e a hierarquia de exceções existente.
- Isolar o parsing de metadados em um helper interno para tornar o serviço
  simples de testar.
- Usar `pathlib.Path` para filtragem de arquivos e compatibilidade entre
  sistemas operacionais.

## Tarefas

### Fase 1: Fundação do serviço

#### Tarefa 1: Adicionar erro de insuficiência de vídeos

**Descrição:** Criar `InsufficientVideosError` na hierarquia de exceções do
backend para representar a ausência de fontes elegíveis.

**Critérios de aceitação:**

- [ ] A exceção pode ser importada pela camada de serviços.
- [ ] A exceção preserva a hierarquia de erros da aplicação.

**Verificação:**

- [ ] Ruff e teste de importação passam.

**Dependências:** Nenhuma.

**Arquivos prováveis:**

- `backend/app/core/exceptions.py`

**Escopo estimado:** Pequeno.

#### Tarefa 2: Implementar varredura e parsing via ffprobe

**Descrição:** Criar `scan_videos_folder`, filtrando extensões suportadas,
executando probes em threads e convertendo os metadados em `VideoFile`.

**Critérios de aceitação:**

- [ ] Pastas inexistentes, vazias ou sem extensões suportadas retornam lista
      vazia.
- [ ] Duração, largura e altura são extraídas corretamente.
- [ ] Falhas em um arquivo são registradas e não interrompem os demais.

**Verificação:**

- [ ] Testes com `ffmpeg.probe` mockado cobrem sucesso e falha individual.
- [ ] Ruff e Black passam nos arquivos alterados.

**Dependências:** Tarefa 1.

**Arquivos prováveis:**

- `backend/app/services/video/selector.py`
- `backend/tests/test_video_selector.py`

**Escopo estimado:** Médio.

### Checkpoint: Varredura

- [ ] Testes da varredura passam.
- [ ] Metadados inválidos não vazam como objetos `VideoFile`.
- [ ] Não há bloqueio direto do event loop no caminho do probe.

### Fase 2: Seleção de duração

#### Tarefa 3: Implementar seleção aleatória com repetição

**Descrição:** Criar `select_videos_for_duration`, aplicando filtro de seis
segundos, margem, `random.shuffle` e ciclos de seleção até alcançar a meta.

**Critérios de aceitação:**

- [ ] A meta é `required_duration * (1 + safety_margin)`.
- [ ] Vídeos menores que seis segundos são ignorados.
- [ ] A lista é embaralhada antes da seleção e novamente entre ciclos.
- [ ] A seleção pode repetir vídeos elegíveis.
- [ ] Ausência de candidatos lança `InsufficientVideosError` com durações
      disponível e necessária.
- [ ] Duração solicitada não positiva gera `ValueError`.

**Verificação:**

- [ ] Testes cobrem margem, filtro, shuffle, repetição e erros.
- [ ] Toda a suíte backend passa no container de desenvolvimento.

**Dependências:** Tarefa 2.

**Arquivos prováveis:**

- `backend/app/services/video/selector.py`
- `backend/tests/test_video_selector.py`

**Escopo estimado:** Médio.

### Checkpoint: Selector completo

- [ ] Ruff e Black direcionados passam.
- [ ] Suíte backend passa.
- [ ] `git diff --check` passa.
- [ ] Commit separado criado para a implementação do selector.

## Riscos e mitigação

| Risco | Impacto | Mitigação |
|---|---|---|
| Formatos diferentes de saída do ffprobe | Médio | Aceitar duração no formato ou no stream e exigir stream de vídeo para resolução |
| Probe lento bloquear requisições | Alto | Executar cada probe com `asyncio.to_thread` |
| Arquivos corrompidos na pasta | Médio | Registrar falha individual e continuar a varredura |
| Seleção repetitiva pouco variada | Baixo | Embaralhar a lista a cada novo ciclo |

## Questões em aberto

- Nenhuma para esta tarefa. O cutter e a política de diversidade serão
  definidos nas tarefas seguintes.
