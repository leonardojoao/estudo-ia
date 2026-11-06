# Design: frontend base Creator Studio

## Contexto

O backend já possui o endpoint `/health` e as rotas de configurações em
`/api/settings`, mas o diretório `frontend/` ainda contém somente os arquivos
de container e Nginx. Esta entrega cria a base modular do frontend para
consumir essas APIs sem antecipar as telas e integrações das próximas fases.

## Objetivo e escopo

Entregar um frontend Vue 3 executável com:

- Vite, TypeScript, Pinia, Vue Router e Axios;
- visual Creator Studio, com sidebar escura, área principal clara e foco em
  conteúdo e métricas;
- `AppShell`, navegação e páginas Dashboard e Settings;
- Dashboard consumindo `GET /health`;
- Settings consumindo `GET /api/settings` e `PUT /api/settings`;
- estados de carregamento, erro e sucesso;
- responsividade básica para desktop e telas menores;
- testes unitários dos serviços/stores e componentes críticos;
- lint, formatação e build reproduzíveis no Docker.

Ficam fora deste bloco contas YouTube, jobs, calendário, pipeline, OAuth,
upload, SSE e telas que dependem dessas APIs.

## Arquitetura

```text
src/
├── components/
│   └── ui/                 # Componentes visuais reutilizáveis
├── layouts/
│   └── AppShell.vue        # Sidebar, topbar e área de conteúdo
├── router/
│   └── index.ts            # Rotas Dashboard e Settings
├── services/
│   ├── api.ts              # Cliente Axios e tratamento comum
│   └── system.ts           # Health check e settings API
├── stores/
│   ├── system.ts           # Estado de saúde do backend/Ollama
│   └── settings.ts         # Estado e atualização de configurações
├── types/
│   └── index.ts            # Contratos compartilhados
├── views/
│   ├── DashboardView.vue
│   └── SettingsView.vue
├── App.vue
└── main.ts
```

O cliente HTTP usará `VITE_API_URL`, com fallback para
`http://localhost:8000`. Rotas relativas serão usadas quando a aplicação for
servida pelo Nginx, preservando o proxy `/api`.

## Fluxo de dados

1. `main.ts` cria a aplicação Vue, registra Pinia e Vue Router e monta `App`.
2. `AppShell` renderiza a navegação e o conteúdo da rota ativa.
3. `DashboardView` chama a store de sistema ao entrar na página e exibe o
   resultado de `/health`.
4. `SettingsView` carrega `/api/settings`, converte o payload para um
   formulário tipado e envia somente alterações válidas.
5. Erros de rede e respostas não-2xx são convertidos em mensagens úteis sem
   esconder a falha.

O backend atual exige `X-Admin-Key` para atualizações administrativas. O
frontend não armazenará a chave em código nem a enviará automaticamente sem
um mecanismo explícito de entrada/configuração. A tela deve informar quando a
atualização exige essa chave.

## Visual e interação

- Tema Creator Studio: fundo neutro claro, sidebar escura, acentos roxo/azul,
  cartões com bordas suaves e hierarquia visual forte.
- Navegação inicial: Dashboard e Configurações; itens futuros podem aparecer
  como não disponíveis somente se isso não sugerir funcionalidade existente.
- Dashboard: saudação, resumo de saúde, cards de métricas preparatórios e
  ação para abrir configurações.
- Settings: seções agrupadas, labels acessíveis, valores editáveis somente
  para campos suportados e feedback após salvar.
- Todos os estados devem possuir texto visível; não depender apenas de cor ou
  spinner.
- O layout deve funcionar sem rolagem horizontal em viewport de 360px.

## Contratos de dados

O frontend tipará os dados realmente usados:

```ts
type HealthResponse = { status: string }

type SettingsResponse = {
  data: Record<string, string | number | boolean | null>
}
```

O payload de atualização será um `Partial<SettingsForm>`, limitado às chaves
aceitas pelo backend. Segredos e credenciais não serão exibidos.

## Erros e segurança

- Axios terá timeout e erro normalizado para a camada de UI.
- Erros de carregamento terão ação de tentar novamente.
- Erros de atualização terão mensagem sem apagar os valores atuais do
  formulário.
- A chave administrativa nunca será persistida em localStorage.
- A aplicação não exibirá `secret_key` ou credenciais OAuth.
- O frontend dependerá do CORS já configurado no backend durante o
  desenvolvimento.

## Testes e critérios de aceitação

- `npm ci` funciona em ambiente limpo.
- `npm run build` gera o bundle de produção.
- `npm run lint` e `npm run format:check` passam.
- O router renderiza Dashboard e Settings.
- O serviço de health interpreta resposta válida e falha de rede.
- A store de settings carrega e atualiza dados sem expor campos sensíveis.
- Estados de loading, sucesso e erro são renderizados nos componentes.
- O Dockerfile de produção consegue construir o frontend.

## Entregas e commits

As alterações serão agrupadas em commits pequenos e independentes:

1. scaffold Vue/Vite/TypeScript e dependências;
2. tema, shell, router e componentes base;
3. serviços, stores e integração com health/settings;
4. testes, Docker e documentação de execução.
