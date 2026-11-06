# Plano de Implementação: Sequenciador anti-plágio

## Visão geral

Implementar a TASK-025 para reordenar `ClipSpec` e evitar que clipes da mesma
fonte apareçam consecutivamente. O serviço será síncrono, determinístico na
regra de seleção do heap e não modificará os clipes originais.

## Decisões de arquitetura

- Usar `heapq` com quantidades negativas para representar um max-heap.
- Preservar a ordem original dos clipes dentro de cada fonte.
- Retornar `SequencedClip` com posições zero-based.
- Usar `AntiPlagiarismError` para uma fonte única e distribuições impossíveis.
- Validar a propriedade anti-adjacência com `raise`, nunca `assert`.

## Tarefas

### Fase 1: Algoritmo

#### Tarefa 1: Implementar agrupamento e interleaving

**Descrição:** Criar `sequence_clips_anti_plagiarism`, agrupando clipes,
intercalando os grupos via max-heap e construindo a saída tipada.

**Critérios de aceitação:**

- [ ] Lista vazia retorna `[]`.
- [ ] Uma fonte lança `AntiPlagiarismError` orientando adicionar vídeos.
- [ ] Dois grupos uniformes alternam perfeitamente.
- [ ] Todos os clipes são preservados exatamente uma vez.
- [ ] Posições de saída são sequenciais.

**Verificação:**

- [ ] Testes unitários cobrem fontes uniformes e múltiplas fontes.
- [ ] Ruff e Black passam.

**Dependências:** Nenhuma.

**Arquivos prováveis:**

- `backend/app/services/video/sequencer.py`
- `backend/tests/test_video_sequencer.py`

**Escopo estimado:** Médio.

### Fase 2: Validação de impossibilidade

#### Tarefa 2: Rejeitar adjacência inevitável

**Descrição:** Detectar quando nenhum grupo diferente da última fonte está
disponível e lançar erro de domínio, além de validar a saída completa.

**Critérios de aceitação:**

- [ ] Distribuições desbalanceadas não retornam sequência inválida.
- [ ] A validação final usa `AntiPlagiarismError`, não `assert`.
- [ ] A mensagem explica a necessidade de mais fontes ou distribuição.

**Verificação:**

- [ ] Testes cobrem distribuição impossível e garantem a mensagem.
- [ ] Suíte backend passa no container.

**Dependências:** Tarefa 1.

**Arquivos prováveis:**

- `backend/app/services/video/sequencer.py`
- `backend/tests/test_video_sequencer.py`

**Escopo estimado:** Pequeno.

### Checkpoint: Sequenciador completo

- [ ] Ruff e Black direcionados passam.
- [ ] Suíte backend passa.
- [ ] `git diff --check` passa.
- [ ] Checklist TASK-025 atualizado.
- [ ] Commit separado criado.

## Riscos e mitigação

| Risco | Impacto | Mitigação |
|---|---|---|
| Heap escolher o mesmo grupo da última fonte | Alto | Guardar grupo temporariamente e escolher o próximo elegível |
| Distribuição impossível gerar loop | Alto | Falhar quando não houver grupo diferente disponível |
| Empates alterarem ordem entre execuções | Baixo | Usar `source_video` como segundo critério do heap |

## Questões em aberto

- Nenhuma para esta tarefa. A composição será implementada na TASK-026.
