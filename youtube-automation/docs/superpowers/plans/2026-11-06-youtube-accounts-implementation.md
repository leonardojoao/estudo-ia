# Plano de implementação: Contas YouTube e callback OAuth

## Visão geral

Implementar a integração do OAuth2 com contas persistidas, adicionando state
CSRF de uso único, migration, rotas administrativas e testes de contrato. A
implementação seguirá a especificação aprovada em
`2026-11-06-youtube-accounts-design.md`.

## Decisões

- SQLite será a fonte de persistência do state OAuth, sem Redis ou scheduler.
- O callback reconciliará contas pelo `channel_id`.
- Tokens continuarão passando por `encrypt`/`decrypt`; nenhum schema de saída
  incluirá `credentials`.

## Fase 1: Fundação de state

### Tarefa 1: Persistir e validar OAuth state

**Descrição:** Criar o modelo `OAuthState`, migration correspondente e helpers
de criação/validação no serviço YouTube, incluindo expiração de 10 minutos,
consumo único e limpeza oportunista de registros expirados.

**Critérios de aceite:**
- [ ] State é gerado, persistido e retornado como UUID/token não previsível.
- [ ] State válido é consumido uma única vez.
- [ ] State expirado ou inexistente falha com `OAuthError`.

**Verificação:**
- [ ] Testes unitários para criação, consumo único e expiração.
- [ ] Migration aplica e desfaz corretamente.
- [ ] Ruff e Black passam nos arquivos alterados.

**Dependências:** TASK-028.

**Arquivos prováveis:** `app/models/oauth_state.py`,
`app/services/youtube/auth.py`, `alembic/versions/002_oauth_states.py`,
`tests/test_youtube_auth.py`.

**Escopo:** Médio.

## Checkpoint: Fundação

- [ ] Testes backend passam.
- [ ] A tabela de states pode ser criada em banco limpo.

## Fase 2: Fluxo de contas

### Tarefa 2: Implementar rotas de contas e callback

**Descrição:** Criar o router `/api/accounts`, registrar no entrypoint e
implementar listagem, início OAuth, callback, remoção e teste de token com as
dependências e respostas existentes.

**Critérios de aceite:**
- [ ] Listagem nunca retorna `credentials`.
- [ ] Callback valida state antes de trocar o código e cria/atualiza conta.
- [ ] Remoção exige chave administrativa e apaga a conta.
- [ ] Teste de token retorna `valid` sem 500 para token inválido.

**Verificação:**
- [ ] Testes de rota cobrem autenticação, callback, redirect e reconciliação.
- [ ] Testes confirmam que credenciais não aparecem no JSON.
- [ ] Suíte backend passa.

**Dependências:** Tarefa 1.

**Arquivos prováveis:** `app/api/routes/accounts.py`, `backend/main.py`,
`tests/test_accounts.py`, `app/schemas/account.py` se necessário.

**Escopo:** Grande, dividido em funções pequenas e testadas.

### Tarefa 3: Atualizar backlog e documentação operacional

**Descrição:** Marcar a TASK-029 conforme os critérios implementados e atualizar
as instruções de configuração OAuth se o contrato operacional tiver mudado.

**Critérios de aceite:**
- [ ] Backlog reflete as rotas e o state persistido.
- [ ] README documenta as variáveis/redirects necessários, se ainda ausentes.

**Verificação:**
- [ ] Revisão textual sem placeholders ou instruções conflitantes.

**Dependências:** Tarefa 2.

**Arquivos prováveis:** `docs/tasks-implementacao.md`, `README.md`.

**Escopo:** Pequeno.

## Checkpoint: Completo

- [ ] Testes backend, Ruff e Black passam.
- [ ] Aplicação inicia e registra `/api/accounts`.
- [ ] Commits separados registram fundação e rotas.

## Riscos e mitigação

| Risco | Impacto | Mitigação |
|---|---|---|
| Callback repetido | Médio | State de uso único e expiração transacional |
| Canal já conectado | Médio | Atualizar por `channel_id` com commit único |
| Credencial corrompida | Alto | Preservar `TokenDecryptionError` distinto de token inválido |
| Migration em banco legado | Alto | Usar migration incremental e validar upgrade em banco limpo |

## Questões em aberto

- Nenhuma. O comportamento para `channel_id` duplicado foi definido como
  atualização da conta existente.
