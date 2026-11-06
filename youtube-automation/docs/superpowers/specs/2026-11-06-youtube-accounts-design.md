# Design: Contas YouTube e callback OAuth

## Objetivo

Conectar o fluxo OAuth2 já implementado às contas persistidas da aplicação,
permitindo iniciar autorização, concluir o callback, listar contas sem expor
credenciais, testar tokens e remover contas com segurança.

## Decisões de arquitetura

- O state CSRF será persistido em SQLite na tabela `oauth_states`, com validade
  de 10 minutos e uso único.
- As rotas ficarão em `app/api/routes/accounts.py` e delegarão operações OAuth
  para `app/services/youtube/auth.py`.
- O `channel_id` será a chave de reconciliação: uma autorização repetida para o
  mesmo canal atualizará os dados públicos e as credenciais da conta existente.
- O callback redirecionará para `settings.frontend_url` e nunca incluirá tokens
  na URL.
- As respostas de conta usarão `AccountResponse`, que não possui o campo
  `credentials`.

## Fluxo de dados

1. `GET /api/accounts/oauth/url` cria e persiste um state e retorna a URL OAuth.
2. O provedor redireciona para o callback com `code` e `state`.
3. O callback valida e remove o state; states inexistentes ou expirados falham.
4. O código é trocado por credenciais, o canal autenticado é consultado e as
   credenciais são criptografadas antes da persistência.
5. O registro existente pelo `channel_id` é atualizado ou um novo registro é
   criado.
6. O usuário é redirecionado para `/accounts?connected=true`.

## API

- `GET /api/accounts`: lista contas ativas e inativas sem credenciais.
- `GET /api/accounts/oauth/url`: retorna `{ "url": "..." }`.
- `GET /api/accounts/oauth/callback`: valida state, conecta a conta e redireciona
  para o frontend.
- `DELETE /api/accounts/{id}`: remove a conta e suas credenciais criptografadas.
- `POST /api/accounts/{id}/test`: retorna `{ "valid": true|false, "error": ... }`
  sem transformar token inválido em erro 500.

Operações que alteram estado exigem `X-Admin-Key`, seguindo o padrão
administrativo existente. O callback é a exceção necessária para o redirect
OAuth e é protegido pelo state de uso único.

## Persistência e segurança

A migration criará:

```sql
CREATE TABLE oauth_states (
    state_token TEXT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    expires_at DATETIME NOT NULL
);
```

`validate_oauth_state` só retorna sucesso quando o state existe e não expirou;
em ambos os casos o registro é removido. A limpeza de states expirados será
feita durante a criação/validação, sem introduzir um scheduler nesta tarefa.
Credenciais continuam armazenadas somente pelo helper Fernet existente.

## Tratamento de erros

- State ausente, inválido ou expirado: `OAuthError`.
- Código OAuth inválido ou falha da API: erros de domínio já existentes.
- Conta inexistente: `NotFoundError`.
- Credenciais corrompidas: `TokenDecryptionError`, distinguível de token
  simplesmente inválido.
- Falhas de banco fazem rollback antes de serem propagadas.

## Testes e critérios de aceite

- State válido é consumido uma única vez e state expirado é rejeitado.
- Callback cria conta e atualiza conta existente pelo `channel_id`.
- Listagem e schemas nunca retornam `credentials`.
- Remoção apaga o registro da conta.
- Teste de token válido/inválido retorna o contrato booleano sem 500.
- A suíte backend, Ruff e Black passam.

## Fora de escopo

- Interface frontend de gerenciamento de contas.
- Upload de vídeos.
- Scheduler separado para limpeza de states.
- Redis ou outro armazenamento externo para OAuth state.
