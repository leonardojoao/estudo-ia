---
inclusion: auto
name: Padrão de Commit
description: Padrão de mensagens de commit em português brasileiro. Ativado automaticamente quando o usuário solicitar commits, mensagens de commit, ou operações git que envolvam commits.
---

# Padrão de Mensagens de Commit

Todas as mensagens de commit neste projeto devem seguir o padrão abaixo, em **português brasileiro**.

## Formato

```
<tipo>(<escopo>): <descrição curta>

<corpo opcional>

<rodapé opcional>
```

## Tipos Permitidos

| Tipo         | Descrição                                                    |
|--------------|--------------------------------------------------------------|
| `feat`       | Nova funcionalidade                                          |
| `fix`        | Correção de bug                                              |
| `docs`       | Alteração apenas em documentação                             |
| `estilo`     | Formatação, ponto e vírgula, etc. (sem mudança de lógica)    |
| `refat`      | Refatoração de código (sem mudança de funcionalidade)        |
| `teste`      | Adição ou correção de testes                                 |
| `tarefa`     | Tarefas de build, CI, configs, ferramentas auxiliares         |
| `perf`       | Melhoria de performance                                      |
| `ci`         | Alterações em configuração de CI/CD                          |
| `reverter`   | Reversão de commit anterior                                  |

## Regras

1. **Tipo** é obrigatório e deve ser um dos listados acima (em minúsculas)
2. **Escopo** é opcional, mas recomendado — indica a área afetada (ex: `api`, `auth`, `ui`, `banco`)
3. **Descrição curta** é obrigatória:
   - Máximo de 72 caracteres na primeira linha
   - Comece com letra minúscula
   - Sem ponto final
   - Use o imperativo: "adiciona", "corrige", "remove" (não "adicionado", "corrigindo")
4. **Corpo** é opcional — use para explicar o "porquê" da mudança
5. **Rodapé** é opcional — use para referências (ex: `Refs: #123`, `Fecha: #456`)

## Exemplos

### Commit simples
```
feat(auth): adiciona autenticação via OAuth2
```

### Com escopo
```
fix(api): corrige validação de email no cadastro
```

### Com corpo
```
refat(banco): simplifica queries de relatório

Remove joins desnecessários e utiliza CTEs para melhorar
legibilidade e manutenção das queries de relatório mensal.
```

### Com rodapé
```
feat(carrinho): implementa cálculo de frete por região

Adiciona lógica de cálculo baseada em CEP com tabela
de preços por região e peso do pacote.

Refs: #234
Fecha: #198
```

### Documentação
```
docs(readme): atualiza instruções de instalação
```

### Tarefas de infraestrutura
```
tarefa(docker): adiciona multi-stage build no Dockerfile
```

## Anti-padrões (evite)

```
❌ "Correções diversas"
❌ "update"
❌ "WIP"
❌ "fix bugs"
❌ "Adicionado novo componente" (passado em vez de imperativo)
❌ "FEAT: Nova feature" (tipo em maiúsculas)
```
