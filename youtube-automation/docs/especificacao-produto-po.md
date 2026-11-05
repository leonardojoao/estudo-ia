> **✅ DOCUMENTO AUTORITATIVO** — versão completa gerada pelo agente Product Owner.
> Contém personas detalhadas, todos os épicos, critérios de aceitação expandidos e mapa de dependências.

# Especificação de Produto — YAutomate
### Sistema de Automação de Criação e Publicação de Vídeos no YouTube

---

## 1. Visão do Produto

### Objetivo
Automatizar o pipeline completo de criação e publicação de vídeos no YouTube — da geração de texto via IA local até o upload — permitindo que criadores de conteúdo produzam vídeos em escala com mínima intervenção manual.

### Proposta de Valor
Reduzir de horas para minutos o tempo de produção de um vídeo publicável, combinando IA generativa local (Ollama), síntese de voz (TTS), edição automática de vídeo com algoritmo anti-plágio e publicação direta via YouTube API — tudo controlado em uma interface única e clara.

### Personas

**Pedro — O Criador de Conteúdo em Escala**
- Opera múltiplos canais temáticos no YouTube
- Precisa publicar 5 a 10 vídeos por dia por canal
- Tem pouco tempo para edição manual
- Valoriza automação, padronização e velocidade de produção

**Ana — A Gestora de Canais**
- Gerencia múltiplos canais do YouTube para clientes
- Precisa de controle sobre qual conta recebe cada vídeo
- Precisa de visibilidade sobre o status de todos os processamentos
- Valoriza confiabilidade, rastreabilidade e separação clara por conta

**Carlos — O Operador Técnico**
- Configura e mantém o sistema em operação
- Precisa debugar falhas no pipeline sem reprocessar tudo do zero
- Configura credenciais, pastas e parâmetros do sistema
- Valoriza logs detalhados, controle por etapa e mensagens de erro claras

---

## 2. Épicos

| ID | Nome | Descrição |
|----|------|-----------|
| E1 | Infraestrutura e Base do Projeto | Configuração do backend Python, banco SQLite, API REST e projeto Vue.js |
| E2 | Configurações do Sistema | Pasta de vídeos fonte, URL do Ollama, credenciais da API Google |
| E3 | Gestão de Contas YouTube | Cadastro via OAuth, listagem, remoção e seleção de contas |
| E4 | Geração de Texto com IA | Integração Ollama, geração em lote, modo manual, edição de texto |
| E5 | Geração de Áudio | TTS em inglês, duração alvo, verificação e regeneração |
| E6 | Processamento de Vídeo | Seleção aleatória, cortes, algoritmo anti-plágio, montagem final |
| E7 | Dimensões e Formato de Vídeo | Suporte 16:9 e 9:16 com opção de crop |
| E8 | Metadados e Upload | Geração de título/descrição, upload, agendamento, status |
| E9 | Interface Vue | Dashboard, abas de contas e configurações, tela de novo processamento |
| E10 | Debug e Controle por Etapa | Execução individual de etapas, visualização de outputs, reexecução |

---

## 3. User Stories

---

### ÉPICO 1 — Infraestrutura e Base do Projeto

---

### US-001 — Setup do Backend Python

**Como** Carlos (operador técnico),
**Eu quero** um backend Python com API REST pronto para uso,
**Para que** os demais módulos do sistema tenham uma base confiável para operar.

**Critérios de Aceitação:**
- [ ] Backend implementado com FastAPI (ou Flask) e rodando na porta configurável
- [ ] Estrutura de pastas organizada por domínio (accounts, pipeline, config, audio, video)
- [ ] Arquivo `requirements.txt` com todas as dependências pinadas em versão exata
- [ ] Rota `GET /health` retorna `200 OK` com status do sistema
- [ ] CORS configurado para aceitar requisições do frontend Vue
- [ ] Variáveis de ambiente carregadas de arquivo `.env` (nunca hardcoded)
- [ ] Logs estruturados com nível configurável (DEBUG, INFO, ERROR)

**Prioridade:** Must
**Estimativa:** M
**Notas:** Fundação de todo o sistema. Nada mais pode ser desenvolvido sem isso.

---

### US-002 — Banco de Dados SQLite

**Como** Carlos,
**Eu quero** um banco SQLite com esquema versionado,
**Para que** contas, configurações e histórico de processamentos sejam persistidos de forma simples sem dependências externas.

**Critérios de Aceitação:**
- [ ] SQLite configurado com migrations versionadas (ex.: Alembic ou scripts numerados)
- [ ] Tabelas criadas: `accounts`, `configurations`, `processings`, `processing_steps`
- [ ] Banco criado automaticamente na primeira execução se não existir
- [ ] Caminho do arquivo `.db` configurável via variável de ambiente
- [ ] Backup automático antes de cada migration executada

**Prioridade:** Must
**Estimativa:** P
**Notas:** Depende de US-001. Schemas detalhados são responsabilidade do Arquiteto.

---

### US-003 — Setup do Projeto Vue.js

**Como** Pedro e Ana,
**Eu quero** uma interface web acessível pelo navegador,
**Para que** eu possa operar o sistema sem precisar usar linha de comando.

**Critérios de Aceitação:**
- [ ] Projeto Vue 3 com Vite configurado e rodando em modo dev
- [ ] Vue Router configurado com as rotas principais definidas
- [ ] Pinia configurado para gerenciamento de estado global
- [ ] Biblioteca de componentes UI definida e instalada (ex.: PrimeVue, Vuetify ou similar)
- [ ] Arquivo de configuração de endpoint da API (`baseURL`) via variável de ambiente
- [ ] Build de produção funcional (`npm run build`)
- [ ] Aplicação acessível em `http://localhost:5173` (dev) e servida pelo backend em produção

**Prioridade:** Must
**Estimativa:** M
**Notas:** Depende de US-001. Definição da biblioteca de UI deve ser alinhada com o Arquiteto.

---

### ÉPICO 2 — Configurações do Sistema

---

### US-004 — Configurar Pasta de Vídeos Fonte

**Como** Carlos,
**Eu quero** definir o caminho da pasta que contém os vídeos fonte,
**Para que** o sistema saiba onde buscar os arquivos para montar os vídeos finais.

**Critérios de Aceitação:**
- [ ] Campo de configuração aceita caminho absoluto ou relativo
- [ ] Sistema valida se o caminho existe e é uma pasta acessível
- [ ] Sistema lista a quantidade de arquivos de vídeo encontrados na pasta após salvar
- [ ] Formatos suportados: `.mp4`, `.mov`, `.avi`, `.mkv`
- [ ] Configuração persistida no SQLite
- [ ] Mensagem de erro clara se pasta não existir ou estiver vazia
- [ ] Configuração pode ser alterada a qualquer momento sem reiniciar o sistema

**Prioridade:** Must
**Estimativa:** P
**Notas:** Depende de US-002. Sem essa configuração o processamento de vídeo não pode iniciar.

---

### US-005 — Configurar URL do Ollama

**Como** Carlos,
**Eu quero** definir a URL base do serviço Ollama,
**Para que** o sistema saiba como se conectar à instância local de IA.

**Critérios de Aceitação:**
- [ ] Campo aceita URL completa (ex.: `http://localhost:11434`)
- [ ] Botão "Testar conexão" verifica se o Ollama responde
- [ ] Teste de conexão retorna lista de modelos disponíveis em caso de sucesso
- [ ] Mensagem de erro descritiva se URL inválida ou serviço indisponível
- [ ] Configuração persistida no SQLite
- [ ] URL padrão preenchida automaticamente: `http://localhost:11434`

**Prioridade:** Must
**Estimativa:** P
**Notas:** Depende de US-002. Necessário antes de US-011 (geração de texto).

---

### US-006 — Configurar Credenciais da API Google/YouTube

**Como** Carlos,
**Eu quero** inserir as credenciais do projeto Google Cloud (Client ID e Client Secret),
**Para que** o sistema possa autenticar contas YouTube via OAuth.

**Critérios de Aceitação:**
- [ ] Campos para inserir `Client ID` e `Client Secret` do projeto Google Cloud
- [ ] Valores exibidos como campos de senha (ocultados por padrão)
- [ ] Botão para revelar/ocultar os valores
- [ ] Credenciais armazenadas de forma segura (não em texto puro no banco — usar variável de ambiente ou criptografia básica)
- [ ] Mensagem de instrução indicando onde obter as credenciais no Google Cloud Console
- [ ] Sistema valida que os campos não estão vazios antes de salvar
- [ ] Configuração pode ser atualizada sem afetar contas já conectadas

**Prioridade:** Must
**Estimativa:** P
**Notas:** Depende de US-002. Pré-requisito para E3 (gestão de contas).

---

### ÉPICO 3 — Gestão de Contas YouTube

---

### US-007 — Conectar Conta YouTube via OAuth

**Como** Ana (gestora de canais),
**Eu quero** conectar uma conta do YouTube ao sistema via autenticação OAuth,
**Para que** o sistema possa fazer upload de vídeos nessa conta.

**Critérios de Aceitação:**
- [ ] Botão "Conectar conta" abre fluxo OAuth do Google no navegador
- [ ] Após autorização, o sistema armazena o token de acesso e refresh token
- [ ] Nome do canal e avatar são recuperados via YouTube Data API e exibidos na listagem
- [ ] Token é renovado automaticamente via refresh token quando expirado
- [ ] Conta aparece como "Conectada" após fluxo bem-sucedido
- [ ] Erro claro exibido se o usuário cancelar o fluxo de autorização
- [ ] Scopes mínimos solicitados: `youtube.upload` e `youtube.readonly`

**Prioridade:** Must
**Estimativa:** G
**Notas:** Depende de US-006. Maior complexidade técnica do épico. Arquiteto deve definir o fluxo OAuth detalhado.

---

### US-008 — Listar Contas Conectadas

**Como** Ana,
**Eu quero** ver todas as contas YouTube conectadas em uma aba dedicada,
**Para que** eu possa gerenciar quais canais estão disponíveis para upload.

**Critérios de Aceitação:**
- [ ] Listagem exibe: avatar do canal, nome do canal, e-mail da conta e status (Ativa/Token expirado)
- [ ] Status atualizado em tempo real ao carregar a aba
- [ ] Indicador visual diferenciado para contas com token expirado ou com erro
- [ ] Botão "Reconectar" disponível para contas com problema de autenticação
- [ ] Lista vazia exibe mensagem orientando o usuário a conectar a primeira conta

**Prioridade:** Must
**Estimativa:** P
**Notas:** Depende de US-007.

---

### US-009 — Remover Conta Conectada

**Como** Ana,
**Eu quero** remover uma conta YouTube do sistema,
**Para que** ela não apareça mais como opção de upload e seus tokens sejam apagados.

**Critérios de Aceitação:**
- [ ] Botão "Remover" disponível para cada conta na listagem
- [ ] Modal de confirmação exibido antes da remoção (com nome da conta)
- [ ] Tokens (access e refresh) removidos do banco após confirmação
- [ ] Conta removida imediatamente da listagem após exclusão
- [ ] Processamentos futuros que referenciavam essa conta recebem status de erro
- [ ] Ação não revoga o acesso no Google (apenas local) — comportamento documentado na interface

**Prioridade:** Should
**Estimativa:** P
**Notas:** Depende de US-008.

---

### US-010 — Selecionar Conta para Upload em Novo Processamento

**Como** Pedro (criador de conteúdo),
**Eu quero** escolher qual conta YouTube receberá o vídeo ao criar um novo processamento,
**Para que** eu possa direcionar cada vídeo para o canal correto.

**Critérios de Aceitação:**
- [ ] Dropdown ou seletor exibe todas as contas conectadas e ativas
- [ ] Conta selecionada é persistida no processamento
- [ ] Se apenas uma conta estiver conectada, ela é pré-selecionada automaticamente
- [ ] Contas com token inválido aparecem desabilitadas no seletor, com indicação visual
- [ ] Não é possível avançar no processamento sem selecionar uma conta válida

**Prioridade:** Must
**Estimativa:** P
**Notas:** Depende de US-008. Faz parte da tela de novo processamento (US-036).

---

### ÉPICO 4 — Geração de Texto com IA

---

### US-011 — Selecionar Modelo Ollama

**Como** Pedro,
**Eu quero** escolher qual modelo do Ollama será usado para gerar os textos,
**Para que** eu possa usar o modelo mais adequado para o tipo de conteúdo que estou criando.

**Critérios de Aceitação:**
- [ ] Dropdown lista os modelos disponíveis na instância Ollama configurada
- [ ] Lista é carregada dinamicamente via endpoint `/api/tags` do Ollama
- [ ] Modelo selecionado é persistido nas configurações do processamento
- [ ] Mensagem de erro exibida se Ollama estiver indisponível ao tentar carregar modelos
- [ ] Indicador de carregamento durante a busca da lista de modelos
- [ ] Último modelo utilizado é pré-selecionado como padrão

**Prioridade:** Must
**Estimativa:** P
**Notas:** Depende de US-005.

---

### US-012 — Inserir Prompt de Instrução para Geração de Texto

**Como** Pedro,
**Eu quero** inserir um prompt de instrução que guie o modelo de IA,
**Para que** os textos gerados sigam o estilo, tom e tema que eu desejo.

**Critérios de Aceitação:**
- [ ] Campo de texto multilinha com suporte a texto longo (mínimo 2000 caracteres)
- [ ] Contador de caracteres exibido em tempo real
- [ ] Campo permite salvar o prompt como template nomeado para reuso
- [ ] Lista de templates salvos acessível para carregamento rápido
- [ ] Prompt não pode estar vazio ao acionar a geração (validação client-side)
- [ ] Área de preview mostra o prompt completo que será enviado ao modelo

**Prioridade:** Must
**Estimativa:** P
**Notas:** Depende de US-011.

---

### US-013 — Gerar Texto Único via Ollama

**Como** Pedro,
**Eu quero** gerar um único texto a partir do prompt configurado,
**Para que** eu possa visualizar e validar o resultado antes de gerar em lote.

**Critérios de Aceitação:**
- [ ] Botão "Gerar texto" dispara requisição ao Ollama com o prompt configurado
- [ ] Texto gerado exibido em área editável após a geração
- [ ] Indicador de progresso exibido durante a geração (streaming se suportado)
- [ ] Tempo de geração exibido após conclusão
- [ ] Botão "Regenerar" disponível para gerar novo texto com o mesmo prompt
- [ ] Usuário pode editar o texto gerado antes de avançar
- [ ] Erro claro exibido se Ollama retornar falha na geração

**Prioridade:** Must
**Estimativa:** M
**Notas:** Depende de US-012.

---

### US-014 — Gerar Múltiplos Textos em Lote

**Como** Pedro,
**Eu quero** gerar N textos de uma só vez usando o mesmo prompt,
**Para que** eu possa preparar vários vídeos em sequência sem repetir o processo manualmente.

**Critérios de Aceitação:**
- [ ] Campo numérico para definir a quantidade de textos a gerar (mínimo 1, máximo 50)
- [ ] Geração executada sequencialmente com progresso exibido (ex.: "Gerando 3/10...")
- [ ] Cada texto gerado listado individualmente com opção de editar, regenerar ou excluir
- [ ] Geração em lote pode ser cancelada a qualquer momento
- [ ] Textos gerados persistidos no banco associados ao processamento atual
- [ ] Textos com erro de geração marcados individualmente sem interromper o lote
- [ ] Ao final, resumo: X textos gerados com sucesso, Y com falha

**Prioridade:** Must
**Estimativa:** M
**Notas:** Depende de US-013.

---

### US-015 — Inserir Texto Manualmente (Modo sem IA)

**Como** Pedro,
**Eu quero** desativar a geração por IA e inserir o texto manualmente,
**Para que** eu possa usar textos que já possuo ou que prefiro escrever eu mesmo.

**Critérios de Aceitação:**
- [ ] Toggle "Usar IA" / "Inserir manualmente" na tela de geração de texto
- [ ] No modo manual, campos de prompt e seleção de modelo ficam ocultos/desabilitados
- [ ] Área de texto editável exibida para inserção direta do conteúdo
- [ ] Modo manual também suporta múltiplos textos (adicionar/remover manualmente)
- [ ] Texto inserido manualmente passa pelas mesmas validações que textos gerados por IA
- [ ] Alternância entre modos não apaga textos já inseridos (confirmação solicitada antes)

**Prioridade:** Must
**Estimativa:** P
**Notas:** Depende de US-013. Importante para casos onde IA não é necessária.

---

### ÉPICO 5 — Geração de Áudio

---

### US-016 — Configurar Duração Alvo do Áudio

**Como** Pedro,
**Eu quero** definir a duração alvo do áudio em segundos,
**Para que** o sistema saiba qual comprimento de vídeo final devo esperar.

**Critérios de Aceitação:**
- [ ] Campo numérico aceita duração em segundos (mínimo: 10s, máximo: 3600s)
- [ ] Tolerância configurável (ex.: ± 10% da duração alvo)
- [ ] Configuração persistida no processamento atual
- [ ] Valor padrão sugerido: 60 segundos
- [ ] Interface exibe o tempo no formato legível (ex.: "1 minuto e 30 segundos")

**Prioridade:** Must
**Estimativa:** P
**Notas:** Depende de US-002.

---

### US-017 — Gerar Áudio TTS a partir do Texto

**Como** Pedro,
**Eu quero** converter o texto gerado em áudio via TTS,
**Para que** o vídeo final tenha narração em inglês sincronizada.

**Critérios de Aceitação:**
- [ ] Sistema usa biblioteca Python de TTS configurada pelo Arquiteto
- [ ] Geração de áudio disparada por botão na interface após o texto estar confirmado
- [ ] Arquivo de áudio salvo em pasta temporária com nome único (UUID)
- [ ] Formato de saída: `.mp3` ou `.wav` (configurável)
- [ ] Indicador de progresso durante a geração
- [ ] Em lote: gera um áudio por texto, com progresso individual
- [ ] Erro claro exibido com o texto específico que falhou (sem interromper o lote)

**Prioridade:** Must
**Estimativa:** M
**Notas:** Depende de US-013. A escolha da biblioteca TTS é responsabilidade do Arquiteto. Inglês como idioma obrigatório nesta versão.

---

### US-018 — Verificar Duração Real do Áudio Gerado

**Como** Pedro,
**Eu quero** ver a duração real do áudio após a geração,
**Para que** eu saiba se o áudio gerado atende à duração alvo configurada.

**Critérios de Aceitação:**
- [ ] Duração real exibida imediatamente após a geração (em segundos e formato mm:ss)
- [ ] Comparação visual entre duração alvo e real (ex.: barra de progresso ou indicador colorido)
- [ ] Status "✅ Dentro da tolerância" ou "⚠️ Fora da tolerância" exibido claramente
- [ ] Em lote, cada áudio exibe sua duração e status individualmente
- [ ] Duração persistida no banco junto ao registro do áudio gerado

**Prioridade:** Must
**Estimativa:** P
**Notas:** Depende de US-017 e US-016.

---

### US-019 — Regenerar Áudio Fora da Tolerância

**Como** Pedro,
**Eu quero** regenerar um áudio específico que ficou fora da duração alvo,
**Para que** eu não precise reprocessar todo o lote por conta de um único arquivo.

**Critérios de Aceitação:**
- [ ] Botão "Regenerar áudio" disponível individualmente para cada áudio no lote
- [ ] Regeneração usa o mesmo texto mas pode usar parâmetros de velocidade ajustados
- [ ] Parâmetro de velocidade de fala configurável (normal, rápido, lento) para ajuste fino
- [ ] Nova duração exibida após regeneração
- [ ] Histórico das tentativas de geração para o mesmo texto disponível (duração de cada tentativa)

**Prioridade:** Should
**Estimativa:** P
**Notas:** Depende de US-018.

---

### ÉPICO 6 — Processamento de Vídeo

---

### US-020 — Listar e Validar Vídeos da Pasta Fonte

**Como** Carlos,
**Eu quero** ver a listagem de vídeos disponíveis na pasta fonte com informações básicas,
**Para que** eu possa confirmar que os arquivos estão prontos para uso no pipeline.

**Critérios de Aceitação:**
- [ ] Listagem exibe: nome do arquivo, duração total, resolução e tamanho
- [ ] Vídeos corrompidos ou ilegíveis são marcados com status de erro
- [ ] Contagem total de vídeos válidos e duração acumulada exibidas
- [ ] Botão "Atualizar lista" relê a pasta sem precisar alterar configurações
- [ ] Formatos aceitos: `.mp4`, `.mov`, `.avi`, `.mkv`

**Prioridade:** Should
**Estimativa:** P
**Notas:** Depende de US-004. Útil para validação, mas não bloqueia o pipeline.

---

### US-021 — Seleção Aleatória de Vídeos Fonte

**Como** Pedro,
**Eu quero** que o sistema selecione automaticamente vídeos da pasta fonte em quantidade suficiente para cobrir a duração do áudio,
**Para que** eu não precise selecionar manualmente quais vídeos usar.

**Critérios de Aceitação:**
- [ ] Sistema calcula a duração total necessária com base na duração do áudio + margem de segurança (10%)
- [ ] Seleção é aleatória a cada execução (sem repetir a mesma sequência)
- [ ] Vídeos selecionados são registrados no processamento para reprodutibilidade
- [ ] Se não houver vídeos suficientes na pasta, erro claro é exibido com duração disponível vs. necessária
- [ ] Vídeos com duração menor que 6 segundos são ignorados na seleção (não servem para cortes)
- [ ] Log da seleção disponível para debug

**Prioridade:** Must
**Estimativa:** M
**Notas:** Depende de US-017 e US-004.

---

### US-022 — Geração de Cortes de 3-6 Segundos

**Como** Pedro,
**Eu quero** que o sistema gere automaticamente cortes aleatórios de 3 a 6 segundos de cada vídeo selecionado,
**Para que** o vídeo final tenha ritmo dinâmico e visual variado.

**Critérios de Aceitação:**
- [ ] Duração de cada corte gerada aleatoriamente entre 3 e 6 segundos
- [ ] Ponto de início de cada corte selecionado aleatoriamente dentro do vídeo fonte
- [ ] Corte não ultrapassa o final do vídeo (início + duração ≤ duração total do vídeo)
- [ ] Cortes gerados com `ffmpeg` ou biblioteca equivalente
- [ ] Cada corte salvo como arquivo temporário com nome identificável (ex.: `clip_videoX_startY_durZ.mp4`)
- [ ] Log de todos os cortes gerados (arquivo fonte, início, duração) disponível

**Prioridade:** Must
**Estimativa:** M
**Notas:** Depende de US-021. Arquiteto deve especificar a biblioteca de vídeo (ffmpeg-python recomendado).

---

### US-023 — Algoritmo Anti-Plágio na Sequência de Clipes

**Como** Pedro,
**Eu quero** que o sistema organize os clipes de forma que clipes consecutivos nunca sejam do mesmo vídeo fonte,
**Para que** o vídeo final evite detecção de conteúdo duplicado pelo YouTube.

**Critérios de Aceitação:**
- [ ] Algoritmo analisa a quantidade de cortes disponíveis por vídeo fonte
- [ ] Sequência final nunca coloca dois clipes do mesmo vídeo fonte em posições adjacentes
- [ ] Se não for possível evitar adjacência (ex.: apenas 1 vídeo fonte), erro claro é exibido
- [ ] Algoritmo distribui os clipes de forma equilibrada (vídeos com mais cortes distribuídos ao longo da sequência)
- [ ] Sequência final registrada no processamento (com ordem e origem de cada clipe)
- [ ] Log da sequência disponível para verificação no modo debug

**Prioridade:** Must
**Estimativa:** M
**Notas:** Depende de US-022. Requisito central de negócio — sem ele o vídeo pode ser penalizado pelo YouTube.

---

### US-024 — Montagem Final do Vídeo com Áudio

**Como** Pedro,
**Eu quero** que o sistema monte o vídeo final concatenando os clipes e adicionando o áudio gerado,
**Para que** eu tenha um arquivo de vídeo completo pronto para upload.

**Critérios de Aceitação:**
- [ ] Clipes concatenados na ordem definida pelo algoritmo anti-plágio
- [ ] Áudio TTS adicionado ao vídeo (sincronizado ao início)
- [ ] Vídeo final tem a mesma duração do áudio (cortes truncados/ajustados se necessário)
- [ ] Arquivo de saída em formato `.mp4` com codec H.264 e AAC
- [ ] Arquivo de saída salvo em pasta de saída configurável
- [ ] Nome do arquivo gerado incluindo ID do processamento e timestamp
- [ ] Duração do vídeo final verificada e registrada
- [ ] Arquivos temporários (clipes intermediários) removidos após montagem bem-sucedida

**Prioridade:** Must
**Estimativa:** G
**Notas:** Depende de US-022 e US-023. Etapa mais pesada computacionalmente do pipeline.

---

### ÉPICO 7 — Dimensões e Formato de Vídeo

---

### US-025 — Suporte ao Formato 16:9 (Padrão)

**Como** Pedro,
**Eu quero** que o vídeo final seja gerado no formato padrão 16:9,
**Para que** ele seja exibido corretamente no YouTube em modo paisagem.

**Critérios de Aceitação:**
- [ ] Resolução padrão: 1920x1080 (Full HD)
- [ ] Clipes de outras resoluções são redimensionados/ajustados para 1920x1080
- [ ] Barras pretas adicionadas (letterbox) se proporção original for diferente, sem distorção
- [ ] Resolução de saída configurável (opções: 1280x720, 1920x1080)
- [ ] Formato 16:9 selecionado por padrão na tela de novo processamento

**Prioridade:** Must
**Estimativa:** P
**Notas:** Depende de US-024.

---

### US-026 — Suporte ao Formato 9:16 (Vertical/Shorts)

**Como** Pedro,
**Eu quero** gerar vídeos no formato 9:16 para YouTube Shorts,
**Para que** o conteúdo seja adequado para consumo mobile e para a aba Shorts.

**Critérios de Aceitação:**
- [ ] Opção "9:16 (Vertical)" selecionável na tela de novo processamento
- [ ] Resolução de saída: 1080x1920
- [ ] Ao selecionar 9:16, duas opções de tratamento são exibidas:
  - **Com crop:** recorta o centro do vídeo original para preencher o frame vertical
  - **Sem crop (letterbox):** adiciona barras laterais pretas, mantendo o vídeo original sem corte
- [ ] Usuário escolhe entre as duas opções antes de processar
- [ ] Preview do resultado esperado exibido (thumbnail ilustrativa)

**Prioridade:** Should
**Estimativa:** M
**Notas:** Depende de US-025. Importante para estratégia de Shorts, mas não bloqueia o lançamento inicial.

---

### ÉPICO 8 — Metadados e Upload

---

### US-027 — Gerar Título via Ollama

**Como** Pedro,
**Eu quero** que o sistema gere um título para o vídeo usando o Ollama,
**Para que** o vídeo tenha um título relevante e otimizado sem esforço manual.

**Critérios de Aceitação:**
- [ ] Título gerado com base no texto do vídeo e em um prompt de instrução específico para títulos
- [ ] Prompt de título configurável separadamente do prompt de texto
- [ ] Título gerado exibido em campo editável
- [ ] Botão "Regenerar título" disponível
- [ ] Comprimento máximo do título validado (100 caracteres, limite do YouTube)
- [ ] Modo manual disponível: usuário pode digitar o título diretamente

**Prioridade:** Must
**Estimativa:** P
**Notas:** Depende de US-013 e US-011.

---

### US-028 — Gerar Descrição via Ollama

**Como** Pedro,
**Eu quero** que o sistema gere uma descrição para o vídeo usando o Ollama,
**Para que** o vídeo tenha metadados ricos para SEO sem esforço manual.

**Critérios de Aceitação:**
- [ ] Descrição gerada com base no texto do vídeo e em um prompt específico para descrições
- [ ] Prompt de descrição configurável separadamente
- [ ] Descrição gerada exibida em área de texto editável (multilinha)
- [ ] Botão "Regenerar descrição" disponível
- [ ] Comprimento máximo validado (5000 caracteres, limite do YouTube)
- [ ] Modo manual disponível

**Prioridade:** Must
**Estimativa:** P
**Notas:** Depende de US-027.

---

### US-029 — Upload do Vídeo para YouTube

**Como** Pedro,
**Eu quero** que o sistema faça o upload do vídeo montado para a conta YouTube selecionada,
**Para que** o vídeo seja publicado sem que eu precise abrir o YouTube Studio manualmente.

**Critérios de Aceitação:**
- [ ] Upload realizado via YouTube Data API v3
- [ ] Metadados enviados: título, descrição, categoria (configurável), privacidade (pública, não listada, privada)
- [ ] Barra de progresso do upload exibida em tempo real (percentual e velocidade estimada)
- [ ] ID do vídeo do YouTube retornado e armazenado no banco após upload bem-sucedido
- [ ] Link direto para o vídeo no YouTube exibido após conclusão
- [ ] Erro claro com código de erro da API em caso de falha no upload
- [ ] Upload retomável: em caso de interrupção, deve ser possível retomar (usar upload resumable da API)

**Prioridade:** Must
**Estimativa:** G
**Notas:** Depende de US-024, US-028 e US-010. Uma das funcionalidades de maior risco técnico (quota da API, tamanho do arquivo).

---

### US-030 — Agendar Publicação do Vídeo

**Como** Ana,
**Eu quero** agendar a data e hora de publicação de um vídeo,
**Para que** os vídeos sejam publicados em horários estratégicos sem que eu precise estar online.

**Critérios de Aceitação:**
- [ ] Seletor de data e hora disponível na tela de upload
- [ ] Agendamento enviado para o YouTube via API (vídeo criado como privado com `publishAt` definido)
- [ ] Data/hora de agendamento deve ser no futuro (validação client e server-side)
- [ ] Vídeo agendado exibido no dashboard com status "Agendado" e a data/hora prevista
- [ ] Opção de publicação imediata mantida como padrão
- [ ] Fuso horário do usuário considerado na seleção (exibido explicitamente)

**Prioridade:** Should
**Estimativa:** M
**Notas:** Depende de US-029.

---

### ÉPICO 9 — Interface Vue

---

### US-031 — Dashboard de Processamentos (Tela Inicial)

**Como** Ana,
**Eu quero** ver na tela inicial o status de todos os processamentos em andamento e concluídos,
**Para que** eu tenha visibilidade sobre o trabalho em execução sem precisar perguntar ao sistema.

**Critérios de Aceitação:**
- [ ] Listagem de processamentos com: ID, status atual, etapa atual, conta de destino, data de criação e duração total
- [ ] Status com indicação visual colorida: 🔵 Em andamento | ✅ Concluído | ❌ Erro | ⏰ Agendado
- [ ] Atualização automática do status a cada 5 segundos (polling ou WebSocket)
- [ ] Botão "Ver detalhes" para cada processamento abre modal/página com histórico de etapas
- [ ] Filtros por status e conta de destino
- [ ] Processamentos concluídos exibem link direto para o vídeo no YouTube
- [ ] Botão "Novo Processamento" destacado na tela inicial

**Prioridade:** Must
**Estimativa:** M
**Notas:** Depende de US-003. Estrutura central da interface.

---

### US-032 — Aba de Contas Conectadas

**Como** Ana,
**Eu quero** uma aba dedicada para gerenciar as contas YouTube,
**Para que** eu possa adicionar, visualizar e remover contas sem navegar por múltiplas telas.

**Critérios de Aceitação:**
- [ ] Aba "Contas" acessível pelo menu de navegação principal
- [ ] Exibe a listagem de contas (US-008)
- [ ] Botão "Conectar nova conta" presente na aba
- [ ] Ação de remover conta (US-009) acessível por aqui
- [ ] Indicador de quantidade de contas ativas exibido na aba do menu

**Prioridade:** Must
**Estimativa:** P
**Notas:** Depende de US-008. Agrupa US-008 e US-009 na interface.

---

### US-033 — Aba de Configurações do Sistema

**Como** Carlos,
**Eu quero** uma aba de configurações com todos os parâmetros do sistema agrupados,
**Para que** eu possa ajustar o sistema sem precisar procurar onde cada configuração está.

**Critérios de Aceitação:**
- [ ] Aba "Configurações" acessível pelo menu de navegação principal
- [ ] Seções organizadas: "Vídeos Fonte" (US-004), "Ollama" (US-005), "API Google" (US-006)
- [ ] Cada seção com botão "Salvar" independente
- [ ] Feedback visual após salvar (toast de confirmação ou erro)
- [ ] Configurações carregadas do banco ao abrir a aba
- [ ] Botão "Testar conexão Ollama" na seção correspondente

**Prioridade:** Must
**Estimativa:** P
**Notas:** Depende de US-004, US-005 e US-006.

---

### US-034 — Tela de Novo Processamento

**Como** Pedro,
**Eu quero** uma tela guiada para configurar e iniciar um novo processamento de vídeo,
**Para que** eu possa configurar todas as opções em um fluxo claro e sem ambiguidade.

**Critérios de Aceitação:**
- [ ] Tela organizada em seções (ou steps/wizard): Conta, Texto, Áudio, Vídeo, Metadados, Publicação
- [ ] Cada seção exibe as configurações relevantes para aquela etapa do pipeline
- [ ] Validações impedem avançar sem dados obrigatórios preenchidos
- [ ] Resumo das configurações exibido antes de iniciar o processamento
- [ ] Botão "Iniciar Processamento" inicia o pipeline e redireciona para o dashboard
- [ ] Suporte a múltiplos processamentos simultâneos (cada um em paralelo no backend)
- [ ] Estado da tela não é perdido ao navegar para outras abas (usar estado Pinia)

**Prioridade:** Must
**Estimativa:** G
**Notas:** Depende de US-010, US-011, US-016, US-025 e US-027. Tela mais complexa da aplicação.

---

### US-035 — Visualização de Progresso em Tempo Real

**Como** Pedro,
**Eu quero** acompanhar o progresso de cada etapa do processamento em tempo real,
**Para que** eu saiba o que está acontecendo sem precisar aguardar o término.

**Critérios de Aceitação:**
- [ ] Cada etapa do pipeline exibida com status: Pendente | Em execução | Concluída | Erro
- [ ] Barra de progresso global do processamento
- [ ] Log de output de cada etapa acessível ao clicar na etapa
- [ ] Atualização via polling (5s) ou WebSocket (preferível)
- [ ] Estimativa de tempo restante exibida quando possível
- [ ] Notificação browser (se permitido) ao concluir ou falhar

**Prioridade:** Should
**Estimativa:** M
**Notas:** Depende de US-031. WebSocket vs polling a ser decidido pelo Arquiteto.

---

### ÉPICO 10 — Debug e Controle por Etapa

---

### US-036 — Executar Etapas Individuais do Pipeline

**Como** Carlos,
**Eu quero** poder executar cada etapa do pipeline de forma isolada,
**Para que** eu possa testar e debugar cada parte sem reprocessar o pipeline inteiro.

**Critérios de Aceitação:**
- [ ] Etapas disponíveis individualmente: Geração de Texto | Geração de Áudio | Seleção de Vídeos | Geração de Cortes | Sequenciamento | Montagem | Upload
- [ ] Cada etapa pode ser executada se suas entradas estiverem disponíveis
- [ ] Pré-condições de cada etapa verificadas antes da execução (erro descritivo se não atendidas)
- [ ] Resultado de cada execução salvo e disponível para a próxima etapa
- [ ] Interface de debug mostra claramente quais etapas estão disponíveis, bloqueadas ou concluídas

**Prioridade:** Should
**Estimativa:** M
**Notas:** Depende de US-034. Essencial para Carlos mas não para Pedro e Ana no uso regular.

---

### US-037 — Visualizar Output de Cada Etapa

**Como** Carlos,
**Eu quero** visualizar o output detalhado de cada etapa do pipeline,
**Para que** eu possa identificar exatamente onde e por que uma etapa falhou.

**Critérios de Aceitação:**
- [ ] Output de cada etapa disponível em área de texto com scroll (estilo terminal)
- [ ] Log inclui: timestamp, nível (INFO/DEBUG/ERROR), mensagem e dados relevantes
- [ ] Output de erros exibido em vermelho com stack trace
- [ ] Botão "Copiar log" para facilitar compartilhamento
- [ ] Logs persistidos no banco (tabela `processing_steps`) por no mínimo 7 dias
- [ ] Filtro por nível de log (mostrar só erros, só info, etc.)

**Prioridade:** Should
**Estimativa:** M
**Notas:** Depende de US-036.

---

### US-038 — Reexecutar Etapa com Falha

**Como** Carlos,
**Eu quero** reexecutar uma etapa específica que falhou sem reiniciar o processamento do zero,
**Para que** eu economize tempo ao corrigir falhas pontuais no pipeline.

**Critérios de Aceitação:**
- [ ] Botão "Reexecutar" disponível para etapas com status de erro
- [ ] Reexecução usa os mesmos parâmetros da tentativa original (com opção de ajustar)
- [ ] Histórico de tentativas exibido (tentativa 1, tentativa 2, etc.)
- [ ] Etapas subsequentes à reexecutada são marcadas como "pendente de re-execução"
- [ ] Limite de 3 tentativas automáticas configurável antes de exigir intervenção manual

**Prioridade:** Could
**Estimativa:** M
**Notas:** Depende de US-037. Melhora a experiência operacional, mas não é crítico para o lançamento.

---

## 4. Backlog Priorizado (Ordem Recomendada de Desenvolvimento)

A ordem abaixo considera: dependências técnicas, valor de negócio e redução de risco.

| Ordem | ID | Título | Prioridade | Épico |
|-------|----|--------|------------|-------|
| 1 | US-001 | Setup do Backend Python | Must | E1 |
| 2 | US-002 | Banco de Dados SQLite | Must | E1 |
| 3 | US-003 | Setup do Projeto Vue.js | Must | E1 |
| 4 | US-004 | Configurar Pasta de Vídeos Fonte | Must | E2 |
| 5 | US-005 | Configurar URL do Ollama | Must | E2 |
| 6 | US-006 | Configurar Credenciais API Google | Must | E2 |
| 7 | US-033 | Aba de Configurações do Sistema | Must | E9 |
| 8 | US-007 | Conectar Conta YouTube via OAuth | Must | E3 |
| 9 | US-008 | Listar Contas Conectadas | Must | E3 |
| 10 | US-032 | Aba de Contas Conectadas | Must | E9 |
| 11 | US-011 | Selecionar Modelo Ollama | Must | E4 |
| 12 | US-012 | Inserir Prompt de Instrução | Must | E4 |
| 13 | US-013 | Gerar Texto Único via Ollama | Must | E4 |
| 14 | US-015 | Inserir Texto Manualmente | Must | E4 |
| 15 | US-014 | Gerar Múltiplos Textos em Lote | Must | E4 |
| 16 | US-016 | Configurar Duração Alvo do Áudio | Must | E5 |
| 17 | US-017 | Gerar Áudio TTS | Must | E5 |
| 18 | US-018 | Verificar Duração Real do Áudio | Must | E5 |
| 19 | US-021 | Seleção Aleatória de Vídeos Fonte | Must | E6 |
| 20 | US-022 | Geração de Cortes 3-6 Segundos | Must | E6 |
| 21 | US-023 | Algoritmo Anti-Plágio | Must | E6 |
| 22 | US-024 | Montagem Final do Vídeo | Must | E6 |
| 23 | US-025 | Suporte Formato 16:9 | Must | E7 |
| 24 | US-027 | Gerar Título via Ollama | Must | E8 |
| 25 | US-028 | Gerar Descrição via Ollama | Must | E8 |
| 26 | US-010 | Selecionar Conta para Upload | Must | E3 |
| 27 | US-029 | Upload do Vídeo para YouTube | Must | E8 |
| 28 | US-031 | Dashboard de Processamentos | Must | E9 |
| 29 | US-034 | Tela de Novo Processamento | Must | E9 |
| 30 | US-009 | Remover Conta Conectada | Should | E3 |
| 31 | US-019 | Regenerar Áudio Fora da Tolerância | Should | E5 |
| 32 | US-020 | Listar e Validar Vídeos da Pasta | Should | E6 |
| 33 | US-026 | Suporte Formato 9:16 | Should | E7 |
| 34 | US-030 | Agendar Publicação | Should | E8 |
| 35 | US-035 | Visualização de Progresso em Tempo Real | Should | E9 |
| 36 | US-036 | Executar Etapas Individuais | Should | E10 |
| 37 | US-037 | Visualizar Output de Cada Etapa | Should | E10 |
| 38 | US-038 | Reexecutar Etapa com Falha | Could | E10 |

---

## 5. Definition of Done (DoD) Geral do Projeto

Uma user story só é considerada **Done** quando todos os critérios abaixo forem atendidos:

### Código
- [ ] Todos os critérios de aceitação da história foram implementados e verificados
- [ ] Código revisado por pelo menos um membro do time (code review)
- [ ] Nenhum `TODO`, `FIXME` ou código comentado deixado para depois sem issue registrada
- [ ] Nomes de variáveis, funções e classes em inglês; comentários e docs em português
- [ ] Tratamento de erros implementado com mensagens úteis ao usuário
- [ ] Sem secrets, tokens ou senhas no código-fonte ou commits

### Testes
- [ ] Testes unitários escritos para lógica de negócio crítica (cobertura mínima: 70% para módulos de backend)
- [ ] Testes de integração para endpoints de API novos ou modificados
- [ ] Cenários de erro e casos de borda cobertos
- [ ] Todos os testes passando no ambiente de CI

### Documentação
- [ ] Endpoints de API documentados (docstring ou OpenAPI/Swagger)
- [ ] README atualizado se a configuração do ambiente foi alterada
- [ ] Decisões arquiteturais relevantes registradas em ADR (se aplicável)

### Interface
- [ ] Interface funciona nos navegadores: Chrome (última versão), Firefox (última versão)
- [ ] Interface responsiva para telas ≥ 1280px de largura
- [ ] Estados de loading, erro e vazio implementados para todas as interações assíncronas
- [ ] Ações destrutivas (remoção, cancelamento) têm confirmação antes de executar

### Deploy
- [ ] Feature funciona no ambiente de desenvolvimento sem configuração manual extra
- [ ] Migrations de banco executadas sem erros

---

## 6. Mapa de Dependências

```
US-001 (Backend)
  └─► US-002 (SQLite)
        └─► US-004 (Pasta Vídeos)
        └─► US-005 (URL Ollama)
              └─► US-011 (Selecionar Modelo)
                    └─► US-012 (Prompt Instrução)
                          └─► US-013 (Gerar Texto Único)
                                └─► US-014 (Gerar Textos em Lote)
                                └─► US-015 (Modo Manual)
                                └─► US-027 (Gerar Título)
                                      └─► US-028 (Gerar Descrição)
        └─► US-006 (Credenciais Google)
              └─► US-007 (Conectar Conta OAuth)
                    └─► US-008 (Listar Contas)
                          └─► US-009 (Remover Conta)
                          └─► US-010 (Selecionar Conta)

US-001 + US-002 + US-016 (Duração Alvo)
  └─► US-017 (Gerar Áudio TTS)
        └─► US-018 (Verificar Duração)
              └─► US-019 (Regenerar Áudio)

US-004 + US-017
  └─► US-021 (Seleção Aleatória de Vídeos)
        └─► US-022 (Geração de Cortes)
              └─► US-023 (Algoritmo Anti-Plágio)
                    └─► US-024 (Montagem Final do Vídeo)
                          └─► US-025 (Formato 16:9)
                          └─► US-026 (Formato 9:16) [depende de US-025]

US-024 + US-028 + US-010
  └─► US-029 (Upload YouTube)
        └─► US-030 (Agendar Publicação)

US-003 (Vue)
  └─► US-033 (Aba Configurações) [agrupa US-004, US-005, US-006]
  └─► US-032 (Aba Contas) [agrupa US-007, US-008, US-009]
  └─► US-031 (Dashboard)
        └─► US-035 (Progresso Tempo Real)
  └─► US-034 (Tela Novo Processamento) [orquestra todo o pipeline]
        └─► US-036 (Executar Etapas Individuais)
              └─► US-037 (Visualizar Output)
                    └─► US-038 (Reexecutar Etapa)
```

### Caminho Crítico (MVP Mínimo Funcional)

```
US-001 → US-002 → US-006 → US-007 → US-008 → US-010
US-001 → US-002 → US-005 → US-011 → US-012 → US-013 → US-027 → US-028
US-001 → US-002 → US-016 → US-017 → US-021 → US-022 → US-023 → US-024 → US-025
                                                                              ↓
                                                                   US-029 (Upload)
```

O MVP funcional requer aproximadamente **27 stories** (todas as Must) antes de estar operacional de ponta a ponta.

---

## 7. Notas para o Arquiteto e Desenvolvedor

### Decisões a serem tomadas pelo Arquiteto
1. **Biblioteca TTS**: `pyttsx3` (offline, mais rápido), `gTTS` (qualidade superior, requer internet) ou `edge-tts` (Microsoft, alta qualidade). Avaliar conforme requisito de qualidade de voz.
2. **Biblioteca de vídeo**: `ffmpeg-python` (wrapper para ffmpeg) ou `moviepy`. Considerar performance na montagem.
3. **Comunicação em tempo real**: polling simples (5s) ou WebSocket para atualizações de status.
4. **Estrutura de pastas do projeto**: monorepo (backend + frontend na mesma pasta) ou repositórios separados.
5. **Execução do pipeline**: síncrona (bloqueia a API) ou assíncrona com fila de tarefas (Celery, RQ ou asyncio tasks).

### Riscos Técnicos Identificados
- **Quota da YouTube Data API**: uploads têm custo de quota alto. Monitorar limites diários.
- **Tamanho dos arquivos de vídeo**: arquivos grandes podem causar timeout no upload — usar upload resumable obrigatoriamente.
- **Performance da montagem de vídeo**: `ffmpeg` pode consumir muita CPU/memória. Considerar fila de processamento.
- **OAuth token refresh**: tokens do Google expiram; o fluxo de refresh deve ser robusto e testado.
- **Anti-plágio**: o algoritmo precisa lidar com edge cases (ex.: apenas 1 vídeo fonte disponível).
