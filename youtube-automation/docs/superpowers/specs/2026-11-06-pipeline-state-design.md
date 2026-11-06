# Especificação: Estado e etapas do pipeline

## Contexto

A TASK-034 cria os contratos compartilhados que serão usados pelo executor do
pipeline na TASK-035. Esta etapa não executa serviços, não altera o banco e não
integra o EventBus; ela somente modela a ordem das etapas, seus metadados e o
estado acumulado de um job.

## Objetivos

- Representar as nove etapas do pipeline com um enum tipado e ordenado.
- Definir pesos de progresso global que somem 100.
- Manter os resultados produzidos por cada etapa em um `JobState` serializável.
- Expor para cada etapa somente os dados que ela precisa consumir.
- Rejeitar explicitamente outputs incompatíveis com a etapa informada.

## Design

### `pipeline/steps.py`

`PipelineStep` será um `str, Enum` com estes valores, nesta ordem:

1. `text_generation`
2. `audio_generation`
3. `audio_verification`
4. `video_selection`
5. `video_cutting`
6. `video_sequencing`
7. `video_composition`
8. `metadata_generation`
9. `upload`

`StepMeta` será um modelo Pydantic imutável com `name` e `weight`. O mapa
`STEP_METADATA` usará os pesos `10, 10, 5, 15, 15, 10, 15, 10, 10`,
respectivamente, totalizando 100.

### `pipeline/state.py`

`JobState` será um modelo Pydantic com:

- `job_id: int`
- `config: JobConfig`
- `generated_text: str | None`
- `audio_path: str | None`
- `audio_duration: float | None`
- `selected_videos: list[VideoFile] | None`
- `clip_specs: list[ClipSpec] | None`
- `sequenced_clips: list[SequencedClip] | None`
- `composed_video_path: str | None`
- `video_title: str | None`
- `video_description: str | None`

Todos os outputs serão opcionais para permitir a construção incremental do
estado. O modelo usará a serialização Pydantic padrão, incluindo nested models,
para que `model_dump_json()` produza JSON persistível.

`to_step_input(step)` retornará dicionários mínimos e serializáveis:

- geração de texto: `config`
- geração de áudio: `generated_text` e configurações de voz/duração
- verificação de áudio: `audio_path` e `audio_duration`
- seleção de vídeo: `audio_duration` e `config`
- corte: `selected_videos`, `audio_duration` e `config`
- sequenciamento: `clip_specs`
- composição: `sequenced_clips`, `audio_path` e `config`
- metadata: `generated_text`
- upload: `composed_video_path`, `video_title` e `video_description`

Os valores serão omitidos quando ainda não estiverem disponíveis; a validação
de pré-condições e o erro HTTP 422 pertencem ao runner da TASK-035.

`save_step_output(step, output)` atualizará somente os campos de estado
correspondentes à etapa:

- texto: `generated_text`
- geração/verificação de áudio: `audio_path` e `audio_duration`
- seleção: `selected_videos`
- corte: `clip_specs`
- sequenciamento: `sequenced_clips`
- composição: `composed_video_path`
- metadata: `video_title` e `video_description`
- upload: não adiciona output ao estado local

Outputs desconhecidos ou incompatíveis serão rejeitados com `ValueError`, sem
silenciar dados inválidos. Os valores recebidos serão validados pelos tipos
Pydantic existentes sempre que forem convertidos para o estado.

## Testes

Os testes da TASK-034 verificarão:

- valores e ordem do enum;
- nomes e soma dos pesos;
- validação de `job_id` e serialização JSON do estado;
- conteúdo mínimo produzido por `to_step_input`;
- atualização correta de cada output;
- rejeição de etapa desconhecida e de output incompatível.

## Fora do escopo

- execução de serviços;
- persistência em `JobStep`;
- atualização de progresso ou publicação de eventos;
- pré-condições do runner;
- novos campos de configuração;
- integração com scheduler ou endpoints HTTP.
