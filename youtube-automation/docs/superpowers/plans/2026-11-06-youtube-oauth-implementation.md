# Plano de Implementação: OAuth2 do YouTube

## Visão geral

Implementar a TASK-028 para conectar a aplicação ao OAuth2 do YouTube, trocar
códigos por tokens, consultar o canal e renovar credenciais criptografadas.

## Decisões de arquitetura

- Usar `InstalledAppFlow` e `google.oauth2.credentials.Credentials`.
- Ler `client_secret.json` de `oauth_credentials_path`.
- Manter funções públicas assíncronas quando houver chamadas de API.
- Reutilizar `core.crypto` para persistir credentials sem plaintext.
- Adicionar `frontend_url` e `oauth_redirect_uri` em `Settings`.

## Tarefas

### Fase 1: Configuração e autorização

#### Tarefa 1: Adicionar configurações OAuth

**Descrição:** Adicionar URL do frontend e redirect URI configuráveis com
defaults locais.

**Critérios de aceitação:**

- [ ] `frontend_url` possui default local.
- [ ] `oauth_redirect_uri` possui callback local.
- [ ] Valores podem ser sobrescritos pelo ambiente.

**Verificação:**

- [ ] Testes de settings passam.
- [ ] Ruff passa.

**Dependências:** Nenhuma.

**Arquivos prováveis:**

- `backend/app/core/config.py`
- `backend/tests/test_settings.py`

**Escopo estimado:** Pequeno.

#### Tarefa 2: Implementar resolução de client secret e URL OAuth

**Descrição:** Resolver o arquivo de credenciais e gerar URL com escopos,
offline, consent, redirect e state.

**Critérios de aceitação:**

- [ ] Diretório e arquivo direto são aceitos.
- [ ] Arquivo ausente gera erro explícito.
- [ ] URL contém os dois escopos, offline, consent, redirect e state.

**Verificação:**

- [ ] Testes mockam `InstalledAppFlow`.
- [ ] Ruff e Black passam.

**Dependências:** Tarefa 1.

**Arquivos prováveis:**

- `backend/app/services/youtube/auth.py`
- `backend/tests/test_youtube_auth.py`

**Escopo estimado:** Médio.

### Checkpoint: Autorização

- [ ] URL OAuth é gerada sem chamadas de rede.
- [ ] Nenhum secret aparece em logs ou respostas de erro.

### Fase 2: Tokens e canal

#### Tarefa 3: Implementar troca de código e channel info

**Descrição:** Trocar authorization code por dicionário serializável e
normalizar informações do canal via YouTube Data API.

**Critérios de aceitação:**

- [ ] Tokens e metadados necessários são retornados.
- [ ] Channel ID, nome e avatar são normalizados.
- [ ] Falhas de Google API viram erro de domínio apropriado.

**Verificação:**

- [ ] Testes usam mocks das bibliotecas Google.
- [ ] Testes cobrem resposta sem avatar.

**Dependências:** Tarefa 2.

**Arquivos prováveis:**

- `backend/app/services/youtube/auth.py`
- `backend/tests/test_youtube_auth.py`

**Escopo estimado:** Médio.

#### Tarefa 4: Implementar refresh e teste de token

**Descrição:** Descriptografar credentials, renovar quando expiradas, persistir
o JSON criptografado e testar validade do token sem lançar exceção.

**Critérios de aceitação:**

- [ ] Refresh atualiza credentials e `updated_at`.
- [ ] Token válido é retornado como `Credentials`.
- [ ] Token inválido retorna `False`.
- [ ] Credentials corrompidas não são confundidas com token inválido.

**Verificação:**

- [ ] Testes cobrem refresh, token válido, inválido e corrupção.
- [ ] Suíte backend passa no container.

**Dependências:** Tarefa 3.

**Arquivos prováveis:**

- `backend/app/services/youtube/auth.py`
- `backend/tests/test_youtube_auth.py`

**Escopo estimado:** Médio.

### Checkpoint: OAuth completo

- [ ] Ruff e Black direcionados passam.
- [ ] Suíte backend passa.
- [ ] Checklist TASK-028 atualizado.
- [ ] `git diff --check` passa.
- [ ] Commit funcional separado criado.

## Riscos e mitigação

| Risco | Impacto | Mitigação |
|---|---|---|
| Formato de client secret variar | Alto | Aceitar diretório ou arquivo e deixar a biblioteca validar |
| Biblioteca Google bloquear event loop | Médio | Executar chamadas síncronas em `asyncio.to_thread` |
| Refresh token ausente | Alto | Retornar erro explícito e não sobrescrever credenciais |
| State não persistido ainda | Alto | Documentar que validação completa pertence à TASK-029 |

## Questões em aberto

- A persistência de CSRF state será implementada na TASK-029, conforme o
  design aprovado.
