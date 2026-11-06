# Design: Scheduler persistente e jobs de limpeza

## Objetivo

Adicionar agendamento persistente ao backend para uploads futuros e tarefas de
manutenção, integrando o ciclo de vida do APScheduler ao lifespan da aplicação.

## Decisões

- Usar `AsyncIOScheduler` com `SQLAlchemyJobStore` apontando para o SQLite
  configurado em `Settings.database_path`.
- Manter uma instância singleton por processo, iniciada no startup e parada no
  shutdown.
- Normalizar `scheduled_at` para UTC antes de criar jobs.
- O callback de upload será explícito e não fingirá sucesso enquanto o pipeline
  runner da TASK-036 não existir; o job registrará a limitação para permitir a
  integração posterior.
- Jobs de manutenção serão idempotentes e tolerantes a arquivos/registros já
  removidos.

## API do serviço

- `get_scheduler() -> AsyncIOScheduler`: retorna o singleton configurado.
- `start_scheduler()`: inicia o scheduler uma única vez.
- `shutdown_scheduler()`: encerra o scheduler sem aguardar tarefas indefinidas.
- `schedule_upload_job(job_id, scheduled_at) -> str`: cria job persistente em
  UTC e retorna seu ID.
- `cancel_scheduled_job(scheduler_job_id)`: remove o job se existir.

## Jobs periódicos

- Preview de áudio: a cada hora, remove arquivos em
  `/tmp/audio_preview/` mais antigos que `audio_preview_ttl_hours`.
- OAuth states: a cada 30 minutos, remove registros com `expires_at` anterior ao
  instante atual.
- Outputs: diariamente, remove arquivos em `/app/output/` mais antigos que
  `output_retention_days`, somente quando o output estiver marcado como
  publicado no YouTube. Arquivos sem essa indicação ficam preservados.

Os jobs de manutenção serão registrados com IDs fixos para evitar duplicação
após reinicializações.

## Integração com o lifespan

1. Aplicar migrations.
2. Recuperar jobs zumbis.
3. Iniciar o scheduler e registrar/manter os jobs periódicos.
4. Atender requisições.
5. Parar o scheduler no shutdown.

## Tratamento de erros

- Data ingênua será interpretada como UTC.
- Data no passado será rejeitada com erro de validação.
- Cancelamento de ID inexistente será operação idempotente.
- Falhas de limpeza serão registradas e não interromperão o scheduler.
- O callback placeholder de upload emitirá erro explícito, sem marcar job como
  concluído.

## Testes e critérios de aceite

- Scheduler inicia e encerra uma única vez.
- Upload job usa UTC, persiste no job store e pode ser cancelado.
- Jobs de limpeza usam os TTLs configurados.
- States expirados e previews antigos são removidos.
- Outputs não publicados não são removidos.
- Lifespan integra startup e shutdown.
- Ruff, Black e a suíte backend passam.

## Fora de escopo

- Execução real do pipeline de upload; prevista para TASK-036.
- Endpoint HTTP de agendamento.
- Interface frontend de jobs.
