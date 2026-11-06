# Design: Fluxo OAuth2 do YouTube

## Contexto

A criptografia de tokens já está disponível. Esta etapa implementa a TASK-028:
adaptar a biblioteca Google OAuth2 para gerar autorização, trocar o código,
consultar o canal, renovar credenciais e testar tokens.

## Objetivos

- Usar `client_secret.json` configurável.
- Solicitar escopos de upload e leitura do YouTube.
- Obter refresh token com `access_type=offline` e `prompt=consent`.
- Retornar dados serializáveis para persistência criptografada.
- Renovar tokens expirados e persistir a atualização.
- Tratar token inválido como resultado `False` no teste.

## Configuração

Adicionar configurações:

- `frontend_url`, default `http://localhost:5173`.
- `oauth_redirect_uri`, default
  `http://localhost:8000/api/accounts/oauth/callback`.

`oauth_credentials_path` apontará para um diretório ou diretamente para
`client_secret.json`. O serviço resolverá o arquivo sem assumir um caminho
adicional.

## Componentes

Criar `backend/app/services/youtube/auth.py` com:

```python
def get_oauth_authorization_url(settings: Settings) -> str:
    ...

async def exchange_code_for_tokens(code: str, settings: Settings) -> dict:
    ...

async def get_channel_info(credentials: dict) -> dict:
    ...

async def refresh_token_if_expired(
    account: YouTubeAccount,
    db: Session,
    settings: Settings,
) -> Credentials:
    ...

async def test_token(account: YouTubeAccount, settings: Settings) -> bool:
    ...
```

O flow usará `InstalledAppFlow` e os escopos
`https://www.googleapis.com/auth/youtube.upload` e
`https://www.googleapis.com/auth/youtube.readonly`.

## CSRF state

`get_oauth_authorization_url` gerará um state aleatório e o incluirá na URL.
Esta tarefa não possui contexto de banco para persistir o state; a persistência,
TTL, validação e remoção serão implementadas na TASK-029 junto ao callback.
Até essa integração, a função não deve afirmar que o state foi validado.

## Tokens e refresh

`exchange_code_for_tokens` retornará campos necessários para construir
`google.oauth2.credentials.Credentials`, incluindo token, refresh token,
client ID, client secret, token URI, scopes e expiração.

`refresh_token_if_expired` descriptografará `account.credentials`, criará
`Credentials`, renovará somente quando necessário e gravará o JSON atualizado
com `core.crypto.encrypt`, atualizando `updated_at`.

Falhas de descriptografia serão preservadas como erro de credencial corrompida.
Falhas de API ou token inválido não exporão secrets.

## Testes

- Arquivo de credenciais ausente ou inválido.
- URL com scopes, offline, consent, redirect e state.
- Troca de código mockada e saída serializável.
- Resposta do canal normalizada.
- Refresh atualizando credentials e timestamp.
- Token inválido retornando `False`.

## Fora do escopo

- Persistência da tabela `oauth_states`.
- Rotas HTTP de contas.
- Upload de vídeos.
- Interface frontend para conexão de contas.
