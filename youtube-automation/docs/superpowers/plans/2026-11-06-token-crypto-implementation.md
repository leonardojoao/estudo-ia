# Plano de Implementação: Criptografia de tokens

## Visão geral

Implementar a TASK-027 para proteger tokens OAuth com Fernet e derivar chaves
válidas de `SECRET_KEY` curta usando PBKDF2HMAC.

## Decisões de arquitetura

- Usar `cryptography.fernet.Fernet` como cifra autenticada.
- Aceitar diretamente chaves Fernet URL-safe válidas.
- Derivar outras chaves com PBKDF2HMAC-SHA256, 390000 iterações e salt fixo
  versionado.
- Converter falhas criptográficas em `TokenDecryptionError`.
- Não persistir nem registrar dados sensíveis fora do token retornado.

## Tarefas

### Fase 1: Fundação

#### Tarefa 1: Adicionar erro de descriptografia

**Descrição:** Criar `TokenDecryptionError` na hierarquia de erros da aplicação.

**Critérios de aceitação:**

- [ ] A exceção herda de `AppError`.
- [ ] Possui código estável e status HTTP apropriado.
- [ ] Não inclui plaintext ou chave na mensagem.

**Verificação:**

- [ ] Teste de importação e instanciação passa.
- [ ] Ruff passa.

**Dependências:** Nenhuma.

**Arquivos prováveis:**

- `backend/app/core/exceptions.py`

**Escopo estimado:** Pequeno.

### Fase 2: Criptografia

#### Tarefa 2: Implementar derivação e operações Fernet

**Descrição:** Criar `get_fernet`, `encrypt` e `decrypt`, incluindo caminho
direto para chaves Fernet e derivação PBKDF2 para segredos comuns.

**Critérios de aceitação:**

- [ ] Chave curta gera Fernet válido.
- [ ] Chave Fernet válida é aceita diretamente.
- [ ] Derivação é determinística.
- [ ] Round-trip preserva o texto original.
- [ ] Token inválido gera `TokenDecryptionError`.

**Verificação:**

- [ ] Testes cobrem chave curta, chave válida, segredo diferente e corrupção.
- [ ] Ruff e Black passam.
- [ ] Suíte backend passa no container.

**Dependências:** Tarefa 1.

**Arquivos prováveis:**

- `backend/app/core/crypto.py`
- `backend/tests/test_crypto.py`

**Escopo estimado:** Médio.

### Checkpoint: Criptografia completa

- [ ] Critérios da TASK-027 marcados como concluídos.
- [ ] `git diff --check` passa.
- [ ] Suíte backend passa.
- [ ] Commit funcional separado criado.

## Riscos e mitigação

| Risco | Impacto | Mitigação |
|---|---|---|
| Troca acidental de chave Fernet válida por derivação | Alto | Detectar e preservar formato Fernet antes da derivação |
| Exposição de dados em exceções | Alto | Mensagem genérica sem token, chave ou plaintext |
| Mudança de parâmetros quebrar tokens | Alto | Centralizar salt e iterações em constantes versionadas |

## Questões em aberto

- Nenhuma para esta tarefa. Rotação de chave será tratada separadamente.
