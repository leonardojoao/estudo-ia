# Plano de implementação: Scheduler persistente

## Visão geral

Implementar APScheduler persistente em SQLite, integrar seu ciclo de vida ao
FastAPI e adicionar jobs periódicos de manutenção.

## Fase 1: Serviço scheduler

### Tarefa 1: Criar singleton e jobs de upload

**Descrição:** Configurar `AsyncIOScheduler` com `SQLAlchemyJobStore`, expor
start/shutdown, agendar uploads em UTC e permitir cancelamento idempotente.

**Critérios de aceite:**
- [ ] Scheduler usa o banco configurado.
- [ ] Datas ingênuas são UTC e datas passadas são rejeitadas.
- [ ] Jobs retornam IDs estáveis e podem ser cancelados.
- [ ] Callback placeholder falha explicitamente sem sucesso falso.

**Verificação:** Testes com scheduler isolado e job store SQLite temporário.

**Dependências:** TASK-002, TASK-004, TASK-036 para execução real.

**Arquivos prováveis:** `app/core/scheduler.py`,
`tests/test_scheduler.py`.

**Escopo:** Médio.

## Checkpoint: Serviço

- [ ] Jobs são persistidos e recuperáveis.
- [ ] Testes unitários passam.

## Fase 2: Manutenção

### Tarefa 2: Implementar jobs de limpeza

**Descrição:** Adicionar limpeza de previews, OAuth states e outputs antigos
publicados, com intervalos fixos e tratamento de falhas.

**Critérios de aceite:**
- [ ] Preview usa TTL configurado e roda a cada hora.
- [ ] OAuth states expirados são removidos a cada 30 minutos.
- [ ] Outputs antigos só são removidos quando marcados como publicados.

**Verificação:** Testes criam arquivos/registros temporários e verificam
remoção/preservação.

**Dependências:** Tarefa 1.

**Arquivos prováveis:** `app/core/scheduler.py`,
`tests/test_scheduler.py`, `app/core/config.py` se necessário.

**Escopo:** Médio.

## Fase 3: Lifespan e documentação

### Tarefa 3: Integrar startup/shutdown

**Descrição:** Iniciar scheduler após migrations/recovery e encerrá-lo no
shutdown, sem duplicar jobs periódicos.

**Critérios de aceite:**
- [ ] Lifespan inicia e para o singleton.
- [ ] Jobs periódicos têm IDs fixos.
- [ ] Falhas de manutenção não derrubam a aplicação.

**Verificação:** Testes do lifespan e suíte backend completa.

**Dependências:** Tarefa 2.

**Arquivos prováveis:** `main.py`, `tests/test_health.py`,
`docs/tasks-implementacao.md`.

**Escopo:** Pequeno.

## Checkpoint final

- [ ] Suíte backend, Ruff e Black passam.
- [ ] Scheduler persiste jobs no SQLite.
- [ ] TASK-032 marcada como concluída.

## Riscos

| Risco | Impacto | Mitigação |
|---|---|---|
| SQLite concorrente com scheduler | Alto | Job store no mesmo banco e jobs curtos/idempotentes |
| Jobs duplicados após restart | Médio | IDs fixos e replace_existing |
| Runner ainda inexistente | Médio | Callback placeholder explícito até TASK-036 |
