# Plano de Implementação: Estado e etapas do pipeline

## Visão geral

Implementar os contratos da TASK-034 em dois módulos pequenos e independentes:
metadados das etapas em `pipeline/steps.py` e estado acumulado em
`pipeline/state.py`. A validação será feita com testes unitários focados, sem
alterar serviços existentes, banco, scheduler ou endpoints.

## Decisões de arquitetura

- Usar `PipelineStep(str, Enum)` para manter valores compatíveis com o banco e
  JSON, além de preservar uma ordem explícita de execução.
- Usar `StepMeta` como modelo Pydantic congelado para impedir mutações
  acidentais dos pesos em runtime.
- Usar `JobState` como modelo Pydantic e converter modelos aninhados com
  `model_dump`, garantindo serialização JSON sem objetos não serializáveis.
- Centralizar a associação etapa → inputs e etapa → outputs em `JobState`,
  rejeitando nomes de campos desconhecidos em vez de ignorá-los.
- Não adicionar campos de configuração ou comportamento pertencente ao runner.

## Tarefas

### Fase 1: Fundação dos steps

#### Tarefa 1: Criar enum e metadados das etapas

**Descrição:** Criar o pacote `app.pipeline` e implementar `PipelineStep`,
`StepMeta` e `STEP_METADATA` com a ordem e os pesos definidos na especificação.

**Critérios de aceitação:**

- [ ] As nove etapas existem com os valores documentados e na ordem correta.
- [ ] Cada etapa tem nome legível e peso positivo.
- [ ] A soma dos pesos é exatamente 100.
- [ ] `StepMeta` não permite alteração após criação.

**Verificação:**

- [ ] Testes unitários verificam enum, metadados e soma dos pesos.
- [ ] Ruff e Black passam nos arquivos alterados.

**Dependências:** Nenhuma.

**Arquivos prováveis:**

- `backend/app/pipeline/__init__.py`
- `backend/app/pipeline/steps.py`
- `backend/tests/test_pipeline_steps.py`

**Escopo estimado:** Pequeno.

### Fase 2: Estado acumulado

#### Tarefa 2: Criar `JobState` e mapeamentos de entrada/saída

**Descrição:** Implementar o modelo Pydantic do estado do job, com os schemas
existentes como tipos dos outputs, serialização JSON e os métodos
`to_step_input` e `save_step_output`.

**Critérios de aceitação:**

- [ ] Estado inicial é válido com apenas `job_id` e `JobConfig`.
- [ ] `model_dump_json()` serializa configuração e modelos aninhados.
- [ ] Cada etapa recebe somente os inputs definidos na especificação.
- [ ] Cada output válido atualiza o campo correspondente.
- [ ] Outputs desconhecidos ou incompatíveis geram `ValueError`.

**Verificação:**

- [ ] Testes unitários cobrem estado inicial, serialização, inputs e outputs.
- [ ] Suíte backend continua passando.
- [ ] Ruff, Black e `git diff --check` passam.

**Dependências:** Tarefa 1.

**Arquivos prováveis:**

- `backend/app/pipeline/state.py`
- `backend/tests/test_pipeline_state.py`

**Escopo estimado:** Médio.

### Checkpoint: TASK-034 completa

- [ ] Todos os testes direcionados passam.
- [ ] Suíte backend completa passa.
- [ ] Lint e formatação passam.
- [ ] Não há alterações fora do escopo.
- [ ] Código e documentação são commitados separadamente quando aplicável.

## Riscos e mitigação

| Risco | Impacto | Mitigação |
|---|---|---|
| Inputs conterem modelos Pydantic não serializáveis | Médio | Usar `model_dump(mode="json")` ao montar payloads |
| Outputs variarem entre serviços futuros | Médio | Validar chaves por etapa e manter adaptação no runner |
| Campos opcionais serem confundidos com pré-condições | Baixo | Deixar validação de disponibilidade para a TASK-035 |

## Questões em aberto

- Nenhuma. A especificação aprovada define o escopo e os contratos necessários.
