# Design: Barramento de eventos para SSE

## Objetivo

Criar um barramento pub/sub em memória para transmitir progresso dos jobs aos
clientes SSE sem bloquear produtores e sem misturar jobs diferentes.

## Decisões

- `EventBus` ficará em `app/core/events.py` e haverá um singleton global
  `event_bus`.
- Cada subscriber terá uma `asyncio.Queue` independente com `maxsize=100`.
- Subscribers de um `job_id` recebem somente aquele job; subscribers com
  `job_id=None` recebem eventos de todos os jobs.
- O contrato público do evento terá exatamente:
  `job_id`, `status`, `current_step`, `progress` e `step_log`.
- Em overflow, o evento mais antigo será descartado antes de inserir o novo.

## API

- `publish(job_id, event)`: valida o `job_id`, injeta o campo no payload e
  entrega uma cópia para cada subscriber elegível.
- `subscribe(job_id)`: registra uma fila e produz eventos até o consumidor
  encerrar o generator.
- `unsubscribe(job_id, queue)`: remove a fila de forma idempotente.

O evento recebido será um dicionário serializável. Campos ausentes receberão
valores seguros (`status`/`current_step`/`step_log` vazios e `progress` zero)
somente quando o contrato permitir estado parcial; `job_id` sempre virá do
argumento de `publish`, evitando divergência entre rota e payload.

## Concorrência e ciclo de vida

O registro de subscribers será protegido por uma estrutura simples no mesmo
event loop; `publish` não aguardará consumidores lentos. O `async generator`
usará `finally` para remover sua própria fila, inclusive em cancelamento de
requisição SSE.

## Testes e critérios de aceite

- Dois subscribers do mesmo job recebem o mesmo evento.
- Subscriber global recebe eventos de jobs distintos.
- Subscriber de um job não recebe eventos de outro job.
- Queue possui limite 100 e descarta o evento mais antigo no overflow.
- Unsubscribe remove a fila e não deixa referências pendentes.
- Ruff, Black e a suíte backend passam.

## Fora de escopo

- Endpoint SSE; previsto nas TASKs de API/SSE posteriores.
- Persistência de eventos.
- Redis ou broker externo.
