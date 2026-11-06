# Design: Geração de metadata com Ollama

## Objetivo

Gerar título e descrição para vídeos a partir do texto narrado, reutilizando a
integração Ollama existente e garantindo limites compatíveis com o YouTube.

## Decisões

- O módulo será `app/services/metadata/generator.py`.
- As funções públicas serão `generate_title` e `generate_description`, ambas
  assíncronas.
- O módulo reutilizará `OllamaGenerator` e `TextGenInput`, preservando timeout,
  normalização e `OllamaUnavailableError`.
- Prompts personalizados serão templates com `{text}` substituído pelo texto
  narrado. Quando o placeholder não estiver presente, o texto narrado será
  anexado ao prompt para evitar geração sem contexto.

## Fluxo

1. Validar que o texto narrado não está vazio.
2. Selecionar prompt padrão ou personalizado.
3. Inserir o texto narrado no template.
4. Chamar `OllamaGenerator.generate` com o modelo recebido e limite de tokens
   adequado.
5. Remover espaços externos e truncar o resultado em 100 caracteres para título
   ou 5000 para descrição.
6. Propagar `OllamaUnavailableError` sem retornar fallback vazio.

## Prompts padrão

- Título: `Based on the following text, create a YouTube video title (max 100 chars): {text}`
- Descrição: `Based on the following text, create a YouTube video description (max 5000 chars): {text}`

## Testes e critérios de aceite

- Título nunca excede 100 caracteres.
- Descrição nunca excede 5000 caracteres.
- Texto vazio é rejeitado antes da chamada ao provedor.
- Template customizado recebe o texto narrado.
- Template sem `{text}` ainda inclui o texto narrado.
- Indisponibilidade do Ollama propaga `OllamaUnavailableError`.
- Ruff, Black e a suíte backend passam.

## Fora de escopo

- Endpoint HTTP de metadata; previsto para TASK-074.
- Geração de tags; prevista para TASK-039.
- Persistência de metadata em jobs.
