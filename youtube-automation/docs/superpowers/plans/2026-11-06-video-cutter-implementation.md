# Plano de Implementação: Cutter de vídeos

## Visão geral

Implementar a TASK-024 do pipeline de vídeo. O serviço irá gerar cortes curtos
e válidos a partir dos vídeos selecionados e executar cada corte com FFmpeg em
um processo separado, sem bloquear a API assíncrona.

## Decisões de arquitetura

- Manter `generate_clip_specs` e `cut_clip` como funções assíncronas.
- Usar `ProcessPoolExecutor` para a execução síncrona do FFmpeg.
- Reutilizar `ClipSpec`, `VideoFile` e `FFmpegError`.
- Gerar nomes determinísticos baseados no índice do clipe e no nome do vídeo.
- Sobrescrever arquivos existentes explicitamente com `-y`.

## Tarefas

### Fase 1: Geração de especificações

#### Tarefa 1: Implementar geração segura de ClipSpec

**Descrição:** Criar `generate_clip_specs` com validação de parâmetros,
seleção aleatória de duração e início, ajuste do último corte e cobertura da
duração solicitada.

**Critérios de aceitação:**

- [ ] Rejeita lista vazia, duração não positiva e limites inválidos.
- [ ] Cada duração fica entre `min_clip` e `max_clip`, salvo redução necessária
      do último corte.
- [ ] Nenhum spec ultrapassa a duração do vídeo-fonte.
- [ ] A soma dos cortes cobre a duração solicitada.
- [ ] Índices são globais e sequenciais.

**Verificação:**

- [ ] Testes unitários cobrem parâmetros inválidos, limites e múltiplas fontes.
- [ ] Ruff e Black passam.

**Dependências:** Nenhuma.

**Arquivos prováveis:**

- `backend/app/services/video/cutter.py`
- `backend/tests/test_video_cutter.py`

**Escopo estimado:** Médio.

### Checkpoint: Specs

- [ ] Todos os `ClipSpec` são válidos.
- [ ] A soma dos cortes cobre a duração pedida.
- [ ] Nenhum corte excede o vídeo-fonte.

### Fase 2: Execução FFmpeg

#### Tarefa 2: Implementar corte em processo separado

**Descrição:** Criar `cut_clip`, criar o diretório de saída, montar o nome do
arquivo e executar FFmpeg com seek antecipado, cópia de codecs e sobrescrita.

**Critérios de aceitação:**

- [ ] O arquivo segue `clip_{index:04d}_{stem}.mp4`.
- [ ] O comando usa `-ss` antes do input, `-t`, `-c:v copy`, `-c:a copy` e `-y`.
- [ ] A execução ocorre via `ProcessPoolExecutor`.
- [ ] Falhas do FFmpeg viram `FFmpegError` com stderr.

**Verificação:**

- [ ] Testes mockam a função síncrona e verificam argumentos.
- [ ] Teste específico confirma conversão de stderr.

**Dependências:** Tarefa 1.

**Arquivos prováveis:**

- `backend/app/services/video/cutter.py`
- `backend/tests/test_video_cutter.py`

**Escopo estimado:** Médio.

### Checkpoint: Cutter

- [ ] Testes direcionados passam.
- [ ] Suíte backend passa no container.
- [ ] `git diff --check` passa.
- [ ] Commit separado criado para o cutter.

## Riscos e mitigação

| Risco | Impacto | Mitigação |
|---|---|---|
| Processo filho não conseguir importar o helper | Alto | Manter worker síncrono em função de módulo, sem closure |
| Arquivo muito curto para o corte escolhido | Médio | Limitar duração e início pela duração do `VideoFile` |
| `-c copy` produzir corte impreciso | Baixo | Aceitar conforme requisito e manter cortes de 3-6 segundos |
| FFmpeg retornar erro sem stderr útil | Médio | Usar mensagem padrão e preservar qualquer stderr disponível |

## Questões em aberto

- Nenhuma para esta tarefa. O sequenciamento será definido na TASK-025.
