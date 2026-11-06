# Plano de implementação: EventBus para SSE

## Visão geral

Implementar um barramento pub/sub em memória para eventos de progresso de jobs,
com filtragem por job e subscribers globais.

## Tarefa 1: Criar EventBus

**Descrição:** Implementar `EventBus`, singleton global, contrato de evento,
filtragem, fan-out e filas limitadas.

**Critérios de aceite:**
- [ ] Subscribers do mesmo job recebem o mesmo evento.
- [ ] Subscriber global recebe todos os jobs.
- [ ] Subscriber por job ignora outros jobs.
- [ ] Queue tem maxsize 100 e descarta o evento mais antigo.
- [ ] Unsubscribe é idempotente e limpa referências.

**Verificação:** Testes assíncronos de fan-out, filtro, overflow e cancelamento.

**Dependências:** Nenhuma.

**Arquivos prováveis:** `app/core/events.py`, `tests/test_events.py`.

**Escopo:** Médio.

## Tarefa 2: Atualizar backlog

**Descrição:** Marcar os critérios da TASK-033 como concluídos.

**Critérios de aceite:**
- [ ] Backlog reflete o contrato implementado.

**Verificação:** `git diff --check` e suíte backend.

**Dependências:** Tarefa 1.

**Arquivos prováveis:** `docs/tasks-implementacao.md`.

**Escopo:** Pequeno.

## Checkpoint final

- [ ] Suíte backend passa.
- [ ] Ruff e Black passam.
- [ ] Commits separados de código e documentação.
