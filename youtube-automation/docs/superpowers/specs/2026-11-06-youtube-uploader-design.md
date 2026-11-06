# Design: Upload de vídeos para o YouTube

## Objetivo

Adicionar upload resumable para contas YouTube conectadas, com validação de
entrada, renovação automática de credenciais, progresso por chunk, suporte a
agendamento e erros acionáveis para quota e autenticação.

## Decisões de arquitetura

- `UploadInput`, `UploadOutput` e `ScheduleUploadInput` ficarão em
  `app/services/youtube/schemas.py`.
- `upload_video` será assíncrona, mas executará a cadeia síncrona do Google API
  em `asyncio.to_thread` para não bloquear o event loop.
- O upload usará `MediaFileUpload` com `resumable=True` e chunks de
  aproximadamente 1 MiB.
- Credenciais serão descriptografadas e renovadas por
  `refresh_token_if_expired` antes de criar o cliente YouTube.
- Se a renovação falhar, a conta será marcada inativa e o erro será propagado.

## Contrato de entrada e saída

`UploadInput` valida caminho de vídeo existente, título, descrição, tags,
categoria, privacidade (`public`, `private` ou `unlisted`) e data opcional de
publicação. `UploadOutput` retorna `video_id` e URL pública do vídeo.
`ScheduleUploadInput` representa o subconjunto necessário para uploads
agendados.

Quando `publish_at` estiver definido, o `privacyStatus` enviado será sempre
`private` e `status.publishAt` receberá a data em formato RFC 3339. Sem
agendamento, a privacidade solicitada será preservada.

## Fluxo de upload

1. Validar o input e resolver o arquivo local.
2. Renovar o token se expirado, persistindo a alteração.
3. Criar o recurso `videos.insert` com `snippet` e `status`.
4. Enviar o arquivo com `MediaFileUpload(resumable=True, chunksize=1 MiB)`.
5. Repetir `next_chunk()` até a resposta final, chamando o callback com
   percentual inteiro após cada chunk.
6. Retornar o ID e a URL `https://www.youtube.com/watch?v={video_id}`.

## Tratamento de erros

- `HttpError` será convertido em `YouTubeAPIError` com o código HTTP e a
  mensagem retornada pela API.
- `quotaExceeded` terá mensagem específica informando renovação à meia-noite
  PT e sugerindo reagendamento automático para 01:00 PT do dia seguinte.
- Arquivo inexistente, privacidade inválida e dados incompatíveis falharão antes
  da chamada remota.
- Credenciais corrompidas continuam distinguíveis de token inválido.

## Testes e critérios de aceite

- O serviço usa upload resumable e callback por chunk.
- Upload completo retorna `video_id` e URL.
- Agendamento força `private` e envia `publishAt`.
- Token expirado é renovado; falha de renovação marca a conta inativa.
- Erros HTTP comuns e `quotaExceeded` preservam código/mensagem acionáveis.
- Schemas rejeitam entradas inválidas.
- Suíte backend, Ruff e Black passam.

## Fora de escopo

- Fila distribuída, Celery ou RQ.
- Endpoint HTTP de upload.
- Agendamento persistido; isso pertence à TASK-032.
- Geração de metadata; isso pertence à TASK-031.
