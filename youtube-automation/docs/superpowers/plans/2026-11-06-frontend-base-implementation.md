# Plano de implementação: frontend base Creator Studio

## Visão geral

Criar a base modular do frontend Vue 3 para o YouTube Automation, seguindo o
design Creator Studio aprovado. A primeira entrega terá Dashboard e
Configurações conectados ao backend existente, sem implementar contas, jobs,
calendário, pipeline, OAuth, upload ou SSE.

## Decisões de arquitetura

- Vue 3 com Composition API e TypeScript estrito.
- Vite como bundler e servidor de desenvolvimento.
- Pinia para estado de sistema e configurações.
- Vue Router para as rotas Dashboard e Settings.
- Axios com cliente centralizado, timeout e normalização de erros.
- Tailwind CSS para tema e responsividade.
- Vitest + Vue Test Utils para testes unitários.
- O frontend usa `VITE_API_URL` em desenvolvimento e URLs relativas quando
  servido atrás do Nginx.
- A chave administrativa não será persistida nem embutida no bundle.

## Fases e tarefas

### Fase 1 — Scaffold executável

#### Tarefa 1: Criar manifestos e configuração Vite

**Descrição:** Criar `package.json`, lockfile, configurações TypeScript,
Vite, Vitest e arquivos mínimos de entrada para que o projeto instale,
compile e execute.

**Critérios de aceitação:**

- [ ] `npm ci` funciona em ambiente limpo.
- [ ] `npm run build` compila TypeScript e gera `dist`.
- [ ] `npm run test:run` executa o runner sem testes quebrados.
- [ ] `npm run lint` e `npm run format:check` possuem comandos definidos.

**Verificação:**

- `npm ci`
- `npm run build`
- `npm run test:run`

**Dependências:** nenhuma.

**Arquivos prováveis:** `frontend/package.json`, `frontend/package-lock.json`,
`frontend/vite.config.ts`, `frontend/tsconfig*.json`, `frontend/index.html`,
`frontend/src/main.ts`.

**Escopo:** médio.

#### Tarefa 2: Criar tema e shell Creator Studio

**Descrição:** Implementar estilos globais, `AppShell`, sidebar, topbar,
layout responsivo e componentes visuais pequenos reutilizáveis.

**Critérios de aceitação:**

- [ ] Sidebar escura e conteúdo claro seguem o visual aprovado.
- [ ] Navegação contém Dashboard e Configurações.
- [ ] O layout não cria rolagem horizontal em viewport de 360px.
- [ ] Os componentes possuem labels e estados acessíveis.

**Verificação:**

- `npm run build`
- Teste de componente do shell.
- Inspeção manual em desktop e viewport móvel.

**Dependências:** Tarefa 1.

**Arquivos prováveis:** `src/App.vue`, `src/layouts/AppShell.vue`,
`src/components/ui/*`, `src/assets/*`, `src/style.css`.

**Escopo:** médio.

#### Tarefa 3: Configurar router e páginas vazias estruturadas

**Descrição:** Adicionar Vue Router e criar as rotas Dashboard e Settings com
estrutura de cabeçalho, conteúdo e estados de carregamento preparados.

**Critérios de aceitação:**

- [ ] `/` renderiza Dashboard.
- [ ] `/settings` renderiza Configurações.
- [ ] Links da sidebar alteram a rota sem recarregar a página.
- [ ] Rotas desconhecidas redirecionam para Dashboard.

**Verificação:**

- Teste do router.
- `npm run build`.

**Dependências:** Tarefas 1 e 2.

**Arquivos prováveis:** `src/router/index.ts`, `src/views/DashboardView.vue`,
`src/views/SettingsView.vue`, `src/App.vue`.

**Escopo:** pequeno.

### Checkpoint 1 — Aplicação navegável

- [ ] Instalação, lint, testes e build passam.
- [ ] Dashboard e Settings são acessíveis pelo navegador.
- [ ] Layout Creator Studio funciona em desktop e mobile.
- [ ] Criar commit de scaffold/shell/router.

### Fase 2 — Integração vertical com backend

#### Tarefa 4: Criar tipos e cliente HTTP

**Descrição:** Definir contratos TypeScript para health, settings e erros e
criar cliente Axios centralizado com URL configurável e timeout.

**Critérios de aceitação:**

- [ ] `VITE_API_URL` é respeitada, com fallback local.
- [ ] Respostas não-2xx geram erro normalizado.
- [ ] Segredos não fazem parte dos tipos ou payloads exibidos.
- [ ] Serviço possui testes de sucesso e falha de rede.

**Verificação:**

- `npm run test:run -- src/services`
- `npm run lint`

**Dependências:** Tarefa 1.

**Arquivos prováveis:** `src/services/api.ts`, `src/services/system.ts`,
`src/types/index.ts`, testes dos serviços.

**Escopo:** médio.

#### Tarefa 5: Implementar stores de sistema e configurações

**Descrição:** Criar stores Pinia para health e settings, incluindo loading,
erro, retry, edição local e atualização administrativa sem persistir a chave.

**Critérios de aceitação:**

- [ ] Health possui estados `idle`, `loading`, `success` e `error`.
- [ ] Settings carrega o payload do backend e mantém cópia editável.
- [ ] Salvamento envia apenas campos alterados e trata erro.
- [ ] Nenhum segredo recebido é exibido ou salvo no storage do navegador.

**Verificação:**

- Testes das stores com mocks do serviço.
- `npm run test:run -- src/stores`.

**Dependências:** Tarefa 4.

**Arquivos prováveis:** `src/stores/system.ts`, `src/stores/settings.ts`,
testes das stores.

**Escopo:** médio.

#### Tarefa 6: Conectar Dashboard ao health check

**Descrição:** Exibir estado real do backend no Dashboard, com cards
preparatórios para métricas futuras e ação de nova tentativa.

**Critérios de aceitação:**

- [ ] Dashboard chama `GET /health` ao montar.
- [ ] Estado saudável é visível por texto e indicador.
- [ ] Falha mostra mensagem e botão de retry.
- [ ] Loading não apresenta métricas como se fossem dados reais.

**Verificação:**

- Testes de componente para sucesso, loading e erro.
- `npm run build`.

**Dependências:** Tarefas 3 e 5.

**Arquivos prováveis:** `src/views/DashboardView.vue`,
`src/components/ui/StatusBadge.vue`, testes da view.

**Escopo:** médio.

### Checkpoint 2 — Dashboard funcional

- [ ] Dashboard consome o backend real.
- [ ] Sucesso, loading e erro estão cobertos por testes.
- [ ] Commit de integração do Dashboard.

### Fase 3 — Configurações funcionais

#### Tarefa 7: Implementar formulário de Settings

**Descrição:** Construir formulário por seções para os campos públicos
suportados pela API, com validação local, dirty state e feedback.

**Critérios de aceitação:**

- [ ] Settings carrega dados reais de `GET /api/settings`.
- [ ] O formulário não renderiza `secret_key` ou credenciais.
- [ ] Valida URL, dimensão e limites antes do envio.
- [ ] Exibe sucesso sem perder dados após salvar.
- [ ] Informa claramente quando a API exige `X-Admin-Key`.

**Verificação:**

- Testes de componente para load, alteração, validação, sucesso e erro.
- Teste manual usando backend Docker.

**Dependências:** Tarefas 3 e 5.

**Arquivos prováveis:** `src/views/SettingsView.vue`,
`src/components/ui/FormField.vue`, `src/components/ui/AlertMessage.vue`,
testes da view.

**Escopo:** grande, mas limitado a uma tela.

#### Tarefa 8: Ajustar Docker, documentação e validação final

**Descrição:** Fazer o Dockerfile de frontend funcionar com o novo scaffold,
atualizar README com o frontend disponível e validar o fluxo completo.

**Critérios de aceitação:**

- [ ] `docker compose build frontend` passa.
- [ ] Compose de desenvolvimento inicia Vite na porta 5173.
- [ ] Compose de produção serve o build pelo Nginx.
- [ ] README não afirma que o frontend está ausente.
- [ ] Backend continua funcionando e `/health` retorna 200.

**Verificação:**

- `npm ci`
- `npm run lint`
- `npm run format:check`
- `npm run test:run`
- `npm run build`
- `docker compose build frontend`
- `docker compose up -d backend`
- `curl http://localhost:8000/health`

**Dependências:** Tarefa 7.

**Arquivos prováveis:** `frontend/Dockerfile`, `frontend/Dockerfile.dev`,
`frontend/nginx.conf`, `README.md`.

**Escopo:** médio.

### Checkpoint 3 — Entrega completa

- [ ] Todos os critérios da especificação foram verificados.
- [ ] Testes, lint, formatação e build passam.
- [ ] Backend e frontend iniciam com Docker.
- [ ] Commits incrementais estão presentes.
- [ ] Branch está limpa.

## Riscos e mitigação

| Risco | Impacto | Mitigação |
|---|---|---|
| Backend exige chave administrativa para PUT | Alto | Mostrar requisito na UI e não persistir a chave |
| Payload de settings pode evoluir | Médio | Tipos tolerantes e whitelist de campos editáveis |
| Frontend ausente quebra Compose atual | Alto | Criar scaffold antes de usar build completo |
| Dependências npm incompatíveis | Médio | Fixar versões e validar com `npm ci` |
| CORS em desenvolvimento | Médio | Configurar `VITE_API_URL` e origem no README |

## Questões abertas

Nenhuma para este bloco. Contas, jobs e calendário serão definidos nas próximas
especificações quando suas APIs estiverem implementadas.
