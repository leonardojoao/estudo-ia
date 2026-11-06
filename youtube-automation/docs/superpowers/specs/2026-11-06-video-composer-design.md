# Design: Composição final de vídeo

## Contexto

O pipeline já seleciona fontes, gera cortes e organiza clipes. Esta etapa
implementa a TASK-026: concatenar os clipes, aplicar a dimensão escolhida,
mesclar a narração e retornar metadados do arquivo final.

## Objetivos

- Compor clipes na ordem de `sequence_position`.
- Produzir saída 16:9 em 1920x1080.
- Produzir saída 9:16 em 1080x1920, com crop opcional.
- Mesclar áudio e encerrar pelo menor entre áudio e vídeo.
- Executar FFmpeg em processo separado.
- Remover temporários em sucesso e falha.
- Retornar duração, resolução e tamanho do arquivo final.

## Contrato

```python
async def compose_video(
    input: VideoCompositionInput,
) -> VideoCompositionOutput:
    ...
```

Os clipes serão ordenados por `sequence_position`. A entrada deve conter pelo
menos um clipe e paths utilizáveis para clipes, áudio e saída.

## Fluxo de processamento

1. Criar um diretório temporário seguro com `TemporaryDirectory` no diretório
   pai do output.
2. Gerar `list.txt` para o concat demuxer. Cada linha terá o formato
   `file 'caminho escapado'`.
3. Concatenar os clipes com `-f concat -safe 0 -c copy`.
4. Aplicar o filtro de dimensão:
   - **16:9:** reduzir mantendo proporção e adicionar letterbox até 1920x1080.
   - **9:16 com crop:** ampliar para cobrir 1080x1920 e recortar o centro.
   - **9:16 sem crop:** reduzir mantendo proporção e adicionar padding até
     1080x1920.
5. Mesclar o áudio com vídeo H.264, áudio AAC e `-shortest`.
6. Usar `ffprobe` para ler duração, resolução e tamanho do output.
7. Limpar o diretório temporário em `finally`.

## Execução e erros

O fluxo será implementado em uma função síncrona de módulo chamada por
`ProcessPoolExecutor`. A API pública assíncrona delegará o trabalho ao
processo e converterá falhas de FFmpeg ou probe em `FFmpegError`, preservando o
stderr decodificado na mensagem.

O output será sobrescrito explicitamente. Temporários serão removidos mesmo
quando concatenação, filtragem, merge ou probe falhar.

## Testes

Os testes usarão mocks para validar:

- ordenação dos clipes e conteúdo do `list.txt`;
- comandos de concatenação, filtros de 16:9 e 9:16;
- diferença entre crop e padding vertical;
- codecs H.264/AAC e `-shortest`;
- execução via `ProcessPoolExecutor`;
- leitura dos metadados de saída;
- conversão de stderr em `FFmpegError`;
- limpeza dos temporários em sucesso e erro.

## Fora do escopo

- Efeito vintage.
- Execução do pipeline completo.
- Endpoints HTTP.
- Alterações no frontend.
