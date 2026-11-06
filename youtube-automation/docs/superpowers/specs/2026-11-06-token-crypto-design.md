# Design: Criptografia de tokens

## Contexto

As integrações OAuth precisarão armazenar tokens no banco sem manter credenciais
em texto puro. Esta etapa implementa a TASK-027, fornecendo um helper Fernet
determinístico baseado em `Settings.secret_key`.

## Objetivos

- Criptografar e descriptografar strings com Fernet.
- Aceitar `SECRET_KEY` curta derivando uma chave válida com PBKDF2HMAC.
- Manter a derivação estável entre reinícios da aplicação.
- Expor erro de domínio descritivo para tokens corrompidos ou chaves incorretas.
- Nunca registrar plaintext, chaves ou tokens.

## Contrato

```python
def get_fernet(settings: Settings) -> Fernet:
    ...

def encrypt(data: str, settings: Settings) -> str:
    ...

def decrypt(data: str, settings: Settings) -> str:
    ...
```

`encrypt` retorna o token Fernet em texto ASCII. `decrypt` retorna o plaintext
original somente quando a autenticação do token for válida.

## Derivação e compatibilidade

Quando `secret_key` for uma chave Fernet URL-safe válida, ela será usada
diretamente. Isso permite interoperabilidade com configurações que já tenham
uma chave Fernet.

Para outros valores, serão derivados 32 bytes com PBKDF2HMAC-SHA256, 390000
iterações e um salt constante versionado no módulo. O resultado será codificado
em base64 URL-safe para formar a chave Fernet. O salt fixo não é um segredo; a
confidencialidade depende da `SECRET_KEY`.

## Erros e segurança

Será criada `TokenDecryptionError`, derivada de `AppError`, com código
`TOKEN_DECRYPTION_ERROR`. Falhas de formato, autenticação ou chave serão
convertidas para esse erro sem expor o motivo criptográfico detalhado nem os
dados sensíveis.

## Testes

- Round-trip com segredo curto.
- Round-trip com chave Fernet válida.
- Estabilidade da derivação entre instâncias equivalentes.
- Falha com segredo diferente.
- Token corrompido gerando `TokenDecryptionError`, nunca `InvalidToken`.

## Fora do escopo

- Rotação automática de chaves.
- Migração de tokens já armazenados.
- Fluxo OAuth, banco de contas ou endpoints.
