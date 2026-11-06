# Plano de implementação: Gerador de metadata

## Visão geral

Adicionar geração de título e descrição baseada no texto narrado usando o
adaptador Ollama existente, com limites rígidos e prompts configuráveis.

## Tarefa 1: Criar módulo de metadata

**Descrição:** Implementar helpers privados para montar prompts e normalizar
respostas, além das funções assíncronas públicas de título e descrição.

**Critérios de aceite:**
- [ ] Reutiliza `OllamaGenerator`.
- [ ] Prompts padrão e customizados incluem o texto narrado.
- [ ] Limita título a 100 e descrição a 5000 caracteres.
- [ ] Propaga indisponibilidade do Ollama.

**Verificação:** Testes unitários com provider mockado e erro offline.

**Dependências:** TASK-018.

**Arquivos prováveis:** `app/services/metadata/generator.py`,
`app/services/metadata/__init__.py`.

**Escopo:** Pequeno.

## Tarefa 2: Atualizar backlog e documentação

**Descrição:** Marcar os critérios da TASK-031 como concluídos e registrar o
contrato do gerador na documentação técnica se necessário.

**Critérios de aceite:**
- [ ] Backlog reflete a implementação.
- [ ] Nenhuma instrução conflitante é introduzida.

**Verificação:** Revisão textual e `git diff --check`.

**Dependências:** Tarefa 1.

**Arquivos prováveis:** `docs/tasks-implementacao.md`.

**Escopo:** Pequeno.

## Checkpoint

- [ ] Testes backend passam.
- [ ] Ruff e Black passam.
- [ ] Commits separados registram código/testes e documentação.
