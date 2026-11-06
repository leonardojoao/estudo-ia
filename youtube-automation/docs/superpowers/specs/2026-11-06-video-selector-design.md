# Design: Selector de vídeos

## Contexto

O pipeline precisa localizar vídeos-fonte, extrair seus metadados e selecionar
arquivos suficientes para cobrir a duração de uma narração. Esta etapa
implementa somente a TASK-023; o corte, o sequenciamento anti-plágio e a
composição serão adicionados em tarefas posteriores.

## Objetivos

- Varrer uma pasta de vídeos com `ffprobe` por meio de `ffmpeg-python`.
- Retornar arquivos válidos como `VideoFile`, incluindo duração e resolução.
- Selecionar vídeos aleatoriamente até atingir a duração solicitada com margem
  de segurança.
- Permitir reutilização de vídeos quando uma única passagem não for suficiente.
- Informar claramente quando não houver vídeos elegíveis ou duração suficiente.

## Arquitetura

O módulo `backend/app/services/video/selector.py` terá duas funções públicas:

```python
async def scan_videos_folder(folder: str) -> list[VideoFile]:
    ...

async def select_videos_for_duration(
    folder: str,
    required_duration: float,
    safety_margin: float = 0.10,
) -> list[VideoFile]:
    ...
```

`ffmpeg.probe` é uma chamada bloqueante. Cada probe será executado com
`asyncio.to_thread`, preservando a natureza assíncrona da camada de serviço sem
bloquear o event loop.

## Varredura e metadados

`scan_videos_folder`:

1. Verifica se o caminho é uma pasta existente.
2. Lista apenas arquivos regulares com extensões `.mp4`, `.mov`, `.avi`,
   `.mkv` ou `.webm`.
3. Executa `ffmpeg.probe` para cada arquivo.
4. Obtém duração do formato ou do stream de vídeo e largura/altura do primeiro
   stream de vídeo.
5. Retorna uma lista vazia para pasta inexistente, vazia ou sem arquivos
   suportados.
6. Registra e ignora falhas de probe individuais, permitindo que outros
   arquivos válidos continuem sendo processados.

## Seleção

`select_videos_for_duration` rejeita duração solicitada não positiva. A meta é
`required_duration * (1 + safety_margin)`. Os vídeos com menos de seis
segundos são descartados. A lista restante é embaralhada com
`random.shuffle`.

Os vídeos são consumidos em ciclos sobre a lista embaralhada. Quando o fim é
alcançado, a lista é embaralhada novamente e o ciclo continua até que a soma
das durações atinja a meta. Essa estratégia mantém a seleção aleatória e
permite repetição ilimitada quando necessário.

Se não houver candidatos elegíveis, a função lança
`InsufficientVideosError`. Como a repetição é ilimitada, a existência de pelo
menos um vídeo elegível é suficiente para cobrir qualquer meta finita. A
mensagem de erro inclui a duração disponível e a duração necessária para
facilitar o diagnóstico de uma pasta sem fontes válidas.

## Tratamento de erros

- Erros de entrada inválida usam `ValueError`.
- Erros de leitura de um arquivo individual são registrados e não impedem a
  leitura dos demais.
- A insuficiência de fontes usa `InsufficientVideosError`, sem fallback
  silencioso.

## Testes

Os testes usarão `ffmpeg.probe` mockado e cobrirão:

- pasta inexistente, vazia e extensões não suportadas;
- extração de duração e resolução;
- arquivos com probe inválido sendo ignorados;
- filtro de vídeos menores que seis segundos;
- aplicação da margem de segurança;
- uso de `random.shuffle`;
- repetição para alcançar a meta;
- erro informativo quando não houver duração elegível.

## Fora do escopo

- Cortar arquivos com FFmpeg.
- Gerar `ClipSpec`.
- Alternar clipes entre vídeos.
- Compor áudio e vídeo.
- Criar endpoints HTTP ou telas no frontend.
