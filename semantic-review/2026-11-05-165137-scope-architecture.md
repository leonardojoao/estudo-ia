# Análise de Escopo e Arquitetura — YAutomate

O YAutomate é um sistema de automação de vídeos para YouTube: dado um prompt, o pipeline gera texto via Ollama local, converte em áudio TTS (edge-tts), seleciona e recorta vídeos de uma biblioteca local, monta o vídeo final com FFmpeg, gera metadados via Ollama e sobe para a conta selecionada via YouTube Data API v3. A stack é FastAPI + SQLite + Vue 3, tudo single-process. A documentação está consistente no geral — especificação de produto, ADRs e plano de testes cobrem a maioria dos cenários. Os riscos mais sérios estão na confiabilidade do serviço externo de TTS, na recuperação de estado após reinício do servidor, e em algumas lacunas de segurança no fluxo OAuth.

**Watch for:** (1) **confirmed** — o SSE bus in-memory perde todo o estado em reinício: jobs ficam presos em `running` para sempre; (2) **confirmed** — o estado CSRF do OAuth não tem local de armazenamento definido na especificação; (3) **confirmed** — a tabela `job_accounts` (M2M) contradiz o fluxo de produto que seleciona uma única conta por job; (4) **confirmed** — erros de mapeamento US/task no `tasks-implementacao.md` (T-10 a T-17 apontam para user stories erradas); (5) **likely** — a rotação do `SECRET_KEY` invalida todos os tokens OAuth armazenados sem aviso.

**Verdict**: NEEDS_CHANGES

---

## Visão geral

O efeito vintage traz um risco concreto no cálculo de progresso: TASK-056 exige que os pesos de `STEP_METADATA` ainda somem 100 após adicionar `VINTAGE_EFFECT` (peso 8), mas não redistribui os pesos das etapas existentes. Jobs sem efeito vintage vão calcular progresso com base em 10 steps enquanto executam apenas 9, fazendo a barra nunca chegar a 100%.

A ambiguidade entre "batch de N textos = N jobs ou 1 job com N iterações" afeta diretamente o modelo de dados e a UX do dashboard. A tabela `job_accounts` (M2M) cria inconsistência com o fluxo de produto que seleciona uma conta por processamento. Ambas precisam ser resolvidas antes da implementação começar, ou haverá retrabalho nas rotas, schemas e frontend.

A dependência de edge-tts como API não-oficial da Microsoft é o risco operacional de maior impacto para Pedro (5-10 vídeos/dia por canal). Sem plano de fallback ativo, rate limiting, ou modo offline, um bloqueio da Microsoft pode parar toda a produção de um canal sem aviso.

---

<details>
<summary>Issues (15)</summary>

1. **Zombie jobs após reinício** — O SSE bus é in-memory e o runner não tem mecanismo de recovery. Jobs com `status=running` no banco ficam nesse estado para sempre após um crash. Adicionar um passo de startup que seta `status=error` em todos os jobs `running` encontrados no banco.

2. **CSRF state sem storage definido** — A especificação testa validação de CSRF (CT-012) mas não define onde o state é armazenado entre a geração da URL OAuth e o callback. Definir explicitamente: tabela `oauth_states` (TTL 10min) ou cookie assinado com o `SECRET_KEY`.

3. **Schema M2M vs. UX de conta única** — `job_accounts` é M2M, mas o produto seleciona uma conta por job. Definir se o campo vira `account_id` no `processing_jobs` ou se a M2M é intencional para suportar upload multicanal futuro. Ambiguidade agora = retrabalho nas rotas.

4. **Mapeamento US errado em tasks-implementacao.md** — T-10 a T-17 na Fase 2 apontam para US-006 (Credenciais Google), US-007 (Conectar OAuth), US-008/009/010 (gestão de contas), quando deveriam apontar para US-013 a US-018 (geração de texto e áudio). Corrigir antes de usar o documento como guia de desenvolvimento.

5. **Peso do efeito vintage não redistribuído** — TASK-056 adiciona `VINTAGE_EFFECT` com peso 8 mas exige que a soma ainda seja 100. Os pesos das 9 etapas existentes precisam ser reduzidos proporcionalmente. Distribuição atual não está documentada — especificar explicitamente.

6. **Rotação de SECRET_KEY invalida todos os tokens** — Fernet é simétrico com chave única. Se o `SECRET_KEY` mudar, todos os `credentials` criptografados no banco ficam irrecuperáveis. Documentar essa limitação e adicionar aviso na interface quando tokens falham por erro de descriptografia (`InvalidToken`).

7. **Sem limpeza de temporários em caso de falha** — TASK-024/026 removem temporários apenas após sucesso. Um job com erro em `video_composition` deixa dezenas de arquivos de clip no disco. Adicionar cleanup no bloco de erro do runner, ou um job de manutenção periódico.

8. **Sem verificação de espaço em disco antes do job** — Jobs de vídeo podem gerar GBs de temporários. Sem verificação de espaço disponível antes de iniciar, o pipeline pode falhar no meio com erro de I/O genérico. Adicionar verificação mínima (ex.: estimar tamanho da saída e verificar 2× de margem).

9. **Sem tratamento de quota da YouTube Data API** — O risco está documentado mas não tratado. Uploads falhos por quota retornam HTTP 403 com código `quotaExceeded`. Sem tratamento específico, o job vai para `error` sem informar o usuário sobre quando a quota renova (meia-noite PT). Adicionar handling do código `quotaExceeded` com mensagem orientada ao usuário.

10. **edge-tts sem rate limiting ou fallback** — Para Pedro (5-10 vídeos/dia), múltiplas chamadas simultâneas ao edge-tts podem resultar em rate limiting da Microsoft. Não há retry com backoff, nem fallback para modo offline. Documentar limite de chamadas recomendado e adicionar retry com exponential backoff (2-3 tentativas).

11. **Sem modo de produção para debug endpoints** — `POST /api/jobs/{id}/steps/{step}` (execução de etapa isolada) é um endpoint de debug que pode criar arquivos temporários e corromper estado de job se usado fora de sequência. Sem autenticação no sistema, está acessível a qualquer origem permitida pelo CORS. Considerar flag de configuração `debug_mode` que habilita esses endpoints.

12. **batch_size — 1 job ou N jobs?** — US-014 descreve geração de N textos, mas o modelo de dados tem um único `config` JSON por job. CT-023 nota a ambiguidade ("3 jobs ou 1 job com 3 iterações"). Definir antes de implementar: afeta schema do banco, endpoints, dashboard e UX.

13. **Sem template/clone de job** — Pedro precisa criar 5-10 vídeos/dia com configurações similares. O wizard de 6 etapas sem possibilidade de clonar um job bem-sucedido ou salvar uma configuração como template vai gerar fricção operacional significativa. Adicionar "Clonar job" e "Salvar como template" ao backlog.

14. **Sem verificação de disk path no runner** — O runner passa `output_path` e caminhos de clipes do `job_config` para os serviços de vídeo sem revalidar que os paths estão dentro de diretórios permitidos. Embora `ffmpeg-python` previna command injection, path traversal via `../` em nomes de arquivo ainda é possível se o filename vier de um vídeo fonte com nome manipulado.

15. **Ausência de política de retenção de outputs** — Vídeos finais em `/output` crescem indefinidamente. Para 10 vídeos/dia, são ~300 vídeos/mês. Sem retenção automática ou aviso de espaço, o servidor vai encher silenciosamente. Definir política: manter N dias, ou apenas referência ao YouTube ID após upload bem-sucedido.

</details>

<details>
<summary>Detalhes</summary>

## Zombie jobs e recuperação de estado pós-reinício

O `EventBus` é in-memory (`asyncio.Queue`). O `run_pipeline` executa como background task. Se o servidor reiniciar enquanto um job está em `running`, o banco tem `status=running` mas não há task em execução. Nenhum evento SSE virá mais. O frontend fica mostrando o job como "em andamento" indefinidamente.

A correção é um passo de startup no lifespan que faz:

```python
db.query(ProcessingJob).filter(
    ProcessingJob.status == "running"
).update({"status": "error", "error_message": "Job interrompido por reinício do servidor"})
```

Isso não é recovery automático (o job não recomeça), mas evita o estado zumbi. Recovery automático (retomar da última etapa completa) seria ideal mas exige que cada etapa seja idempotente — o que não está especificado atualmente.

---

## Estado CSRF no fluxo OAuth

O fluxo OAuth precisa de um `state` parameter para prevenir CSRF (CT-012 testa exatamente isso). Mas o fluxo é:

```
Frontend → GET /api/accounts/oauth/url → gera state → retorna URL
Browser redireciona para Google → Google redireciona para /api/accounts/oauth/callback?code=...&state=...
Backend valida state
```

Entre a geração do state e o callback, o backend não tem sessão HTTP. O state precisa ser armazenado em algum lugar. A especificação não define onde. As opções são:

- **Tabela `oauth_states`** com TTL de 10 minutos: mais simples de implementar e testar.
- **Cookie assinado** enviado junto com a URL: não funciona facilmente porque o callback volta ao backend, não ao frontend.

Sem essa decisão documentada, a implementação de TASK-028 vai inventar uma solução, e CT-012 pode passar ou falhar dependendo do que foi inventado.

---

## Inconsistência no modelo M2M de contas por job

A tabela `job_accounts` permite N contas por job (`PRIMARY KEY (job_id, account_id)`). O `JobConfig` tem `account_ids: list[int]`. Mas US-010 diz "selecionar qual conta o vídeo receberá" — singular, com dropdown. O frontend de upload (TASK-034) tem "seleção de contas" (plural?) e o schema de accounts no job é M2M.

Se a intenção é suportar upload do mesmo vídeo para múltiplos canais simultaneamente, isso é uma feature significativa que não está descrita em nenhuma user story e que tem implicações de UX (qual conta aparece no dashboard? o job aparece N vezes?). Se a intenção é uma conta por job, o schema deve ser `account_id INTEGER` em `processing_jobs`, não uma tabela M2M.

---

## Erros de mapeamento na coluna US do tasks-implementacao.md

Na Fase 2, as tasks estão mapeadas para as user stories erradas:

| Task | US atribuída (errada) | US correta |
|------|----------------------|------------|
| T-10 (serviço text generation) | US-006 (Credenciais Google) | US-013 (Gerar Texto) |
| T-11 (API text generation) | US-006 | US-013 |
| T-12 (frontend text form) | US-006, US-007 | US-013, US-015 |
| T-13 (serviço TTS) | US-009 (Remover Conta) | US-017 (Gerar Áudio) |
| T-14 (API áudio) | US-009 | US-017 |
| T-15 (listar vozes) | US-010 (Selecionar Conta) | US-019 (Voz TTS) |
| T-16 (frontend áudio) | US-009, US-010 | US-017, US-019 |
| T-17 (geração em lote) | US-008 (Listar Contas) | US-014 (Gerar em Lote) |

Isso não quebra a implementação (a descrição das tasks está correta), mas invalida qualquer rastreabilidade US → task → teste.

---

## Efeito vintage e o problema dos pesos de progresso

TASK-056 adiciona `VINTAGE_EFFECT` com `weight=8` e exige que a soma dos pesos ainda seja 100. Os 9 steps existentes mais o novo totalizam 10 steps. Se o step vintage tem peso 8, os demais precisam redistribuir 8 pontos entre si. Mas os pesos das etapas existentes não estão documentados em nenhum lugar da especificação — a TASK-034 diz apenas "pesos somam 100".

Isso cria dois problemas concretos:
1. Um job sem vintage mostra progresso com base em pesos que incluem o weight do vintage (que está como `skipped`). O progresso pode nunca chegar a 100% se o cálculo não descontar steps opcionais.
2. Um job com vintage tem uma etapa extra de peso 8 — a barra vai a 108% antes da redistribuição.

A solução é calcular o progresso com base apenas nos steps que serão executados (filtrando `skipped` antes de somar pesos), independentemente dos pesos absolutos.

---

## Dependência edge-tts e risco de disponibilidade

`edge-tts` chama uma API não-oficial da Microsoft que imita o serviço do Microsoft Edge. Não há SLA, documentação pública de rate limiting, ou garantia de continuidade. Para Pedro com 5-10 vídeos/dia, é o elo mais fraco do pipeline.

O ADR-001 reconhece o risco mas propõe apenas migração para Coqui TTS como saída — que requer GPU (ou é muito lento em CPU) e tem qualidade inferior. Uma abordagem mais robusta seria:

- Retry com exponential backoff (3 tentativas, 2s/4s/8s) antes de falhar a etapa.
- Timeout explícito de 30s por requisição.
- Documentação de limite recomendado de chamadas paralelas (máximo 2-3 simultâneas).

O plano de testes não tem cenário para rate limiting do edge-tts (HTTP 429 ou connection reset) — apenas para "sem internet". Adicionar CT para `httpx.RemoteProtocolError` e HTTP 429.

---

## Limpeza de temporários e gerenciamento de disco

TASK-024 e TASK-026 especificam limpeza de temporários "após sucesso". Em caso de erro em `video_composition`, os clipes ficam no disco. Para 10 jobs/dia com falhas ocasionais, isso acumula rapidamente.

O runner deveria registrar todos os paths temporários criados no `JobState` e limpar no bloco `finally`, independentemente do resultado. Uma alternativa é um diretório temporário por job (`/tmp/job_{id}/`) que pode ser removido com `shutil.rmtree` no finally.

---

## Segurança do fluxo de credenciais

O risco da criptografia Fernet é chave única sem rotação: se o `SECRET_KEY` mudar (ex.: ao redeployar sem preservar o `.env`), todos os tokens armazenados geram `cryptography.fernet.InvalidToken` ao serem descriptografados. O `refresh_token_if_expired` vai falhar silenciosamente se não tratar esse erro especificamente, potencialmente mostrando a conta como "ativa" mas falhando no upload.

A especificação de `test_token` diz retornar `False` (não exceção) se o token for inválido — mas um `InvalidToken` de Fernet não é o mesmo que um token OAuth inválido. O handler precisa tratar os dois casos separadamente e expor na UI um status "credenciais corrompidas / reconectar" distinto de "token expirado".

---

## Sem autenticação no sistema

O sistema não tem autenticação de usuário. Qualquer pessoa com acesso à rede pode ver todos os jobs e seus outputs, executar etapas de debug, modificar configurações do sistema e deletar contas OAuth. O CORS está configurado para origens específicas, mas CORS não é autenticação — protege apenas o browser, não clientes diretos.

O backlog não tem nenhuma user story de autenticação. Para Ana (gestora de canais em servidor compartilhado), isso é um risco real. Autenticação básica (usuário/senha com JWT) deveria estar no backlog como Should.

---

## Produtividade operacional para Pedro

Para Pedro criando 50-70 vídeos/semana, o wizard de 6 etapas sem atalhos vai ser o principal gargalo operacional. Funcionalidades de alto valor ausentes do backlog:

- **Clone de job**: recriar um job bem-sucedido com o mesmo config, substituindo apenas o texto.
- **Templates de configuração**: salvar um preset completo (voz, dimensão, modelo, prompt de título) com nome, carregar com 1 clique.
- **Bulk create a partir de lista de tópicos**: Pedro fornece 10 tópicos em um textarea, o sistema cria 10 jobs agendados automaticamente.

Essas features não exigem arquitetura nova — o `job_config` JSON já suporta ser copiado. Faltam os endpoints e a UX.

---

## Cobertura de testes

**Não testados:**
- Rate limiting do edge-tts (HTTP 429 e connection reset após muitas chamadas)
- Restart do servidor com jobs em `running` (zombie job scenario)
- Rotação de `SECRET_KEY` e comportamento dos tokens armazenados
- Arquivos temporários deixados no disco após falha do pipeline
- Disco cheio durante processamento de vídeo
- Upload de vídeo com quota da YouTube API esgotada (`quotaExceeded`)
- Path traversal em nomes de arquivo de vídeo fonte (CT-005 cobre o path da pasta, não nomes de arquivo)
- Comportamento do cliente SSE quando eventos são perdidos durante reconexão

A cobertura mínima de 95% para `sequencer.py` está correta — o mesmo nível deveria ser aplicado ao `runner.py` (atualmente 85%), dado que qualquer falha no orquestrador corrompe o estado do job inteiro.

</details>

---

<details>
<summary>Mapa de arquivos analisados</summary>

| Arquivo | O que foi analisado |
|---------|---------------------|
| `docs/especificacao-produto-po.md` | 10 épicos, 38 user stories, critérios de aceitação, backlog priorizado, mapa de dependências |
| `docs/especificacao-tecnica.md` | ADRs, modelo de dados SQL, contratos REST, diagrama de arquitetura, algoritmo anti-plágio, efeito vintage |
| `docs/tasks-implementacao.md` | 57 tasks em 6 fases, dependências entre tasks, critérios de conclusão, pontos de atenção |
| `docs/plano-de-testes.md` | 79 cenários de teste, estratégia de pirâmide, cobertura por módulo, priorização por risco |

Não há código implementado — a análise é inteiramente baseada nos documentos de especificação.

</details>
