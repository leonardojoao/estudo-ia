# Design: Cutter de vídeos

## Contexto

O pipeline já seleciona vídeos-fonte e precisa transformá-los em clipes curtos
para cobrir a duração da narração. Esta etapa implementa somente a TASK-024:
geração de especificações de cortes e execução individual via FFmpeg. O
sequenciamento anti-plágio e a composição final ficam para tarefas posteriores.

## Objetivos

- Gerar `ClipSpec` suficientes para cobrir uma duração solicitada.
- Manter cada corte dentro dos limites do vídeo-fonte.
- Usar cortes aleatórios de três a seis segundos por padrão.
- Executar o FFmpeg sem bloquear o event loop.
- Reutilizar `FFmpegError` com o stderr para diagnóstico.
- Tornar reexecuções idempotentes sobrescrevendo o arquivo de saída.

## API do serviço

```python
async def generate_clip_specs(
    videos: list[VideoFile],
    total_duration_needed: float,
    min_clip: int = 3,
    max_clip: int = 6,
) -> list[ClipSpec]:
    ...

async def cut_clip(spec: ClipSpec, output_dir: str) -> str:
    ...
```

## Geração de especificações

`generate_clip_specs` valida que a lista não está vazia, que a duração total é
positiva e que `min_clip` e `max_clip` são positivos, inteiros e estão em
ordem válida. A cada iteração, escolhe um vídeo da lista e uma duração aleatória
entre os limites configurados. O último corte é reduzido quando necessário para
não exceder a duração solicitada.

Para cada corte, o início é escolhido no intervalo `[0, duração do vídeo -
duração do corte]`. Assim, `start_seconds + duration_seconds` nunca ultrapassa
a duração do vídeo. O índice do clipe é global e sequencial.

## Execução do corte

`cut_clip` cria `output_dir` quando necessário e gera o nome
`clip_{clip_index:04d}_{source_stem}.mp4`. Uma função síncrona interna executa:

```text
ffmpeg -ss <start> -i <source> -t <duration>
        -c:v copy -c:a copy -y <output>
```

O comando será executado em `ProcessPoolExecutor` com um worker por chamada,
mantendo o comportamento assíncrono da API. O uso de `-ss` antes do input
prioriza velocidade e `-c copy` evita re-encode quando possível.

Se o FFmpeg falhar, o stderr será decodificado e incluído na mensagem de
`FFmpegError`. Nenhum erro de execução será convertido em sucesso silencioso.

## Tratamento de erros

- Entradas inválidas geram `ValueError`.
- Vídeo sem espaço suficiente para um corte válido gera `ValueError`.
- Falhas do processo FFmpeg geram `FFmpegError` com stderr.
- O arquivo existente é sobrescrito explicitamente com `-y`.

## Testes

Os testes cobrirão:

- duração total, faixa de duração e índices dos specs;
- limite `start + duration` dentro de cada fonte;
- lista vazia e parâmetros inválidos;
- nome do arquivo, criação do diretório e argumentos do FFmpeg;
- ordem de `-ss` antes do input, codecs e overwrite;
- conversão de stderr em `FFmpegError`.

## Fora do escopo

- Sequenciamento entre vídeos diferentes.
- Variação de velocidade ou efeitos anti-plágio.
- Composição de clipes com áudio.
- Endpoints HTTP e telas no frontend.
