# Especificação de Produto — YouTube Automation

## Visão do Produto

**Objetivo**: Sistema de automação para criação e publicação de vídeos no YouTube, utilizando IA local (Ollama) para geração de conteúdo, TTS para narração em inglês, e processamento de vídeo com técnicas anti-plágio.

**Proposta de valor**: Permitir a criação de vídeos para múltiplos canais do YouTube de forma automatizada, escalável e configurável, sem depender de serviços externos de IA.

---

## Personas

- **Pedro (Criador de Conteúdo em Escala)**: quer publicar vídeos em múltiplos canais sem editar manualmente cada um
- **Ana (Gestor de Tráfego)**: quer agendar publicações em horários estratégicos e monitorar o status
- **Carlos (Desenvolvedor / Power User)**: quer depurar cada etapa do pipeline e inspecionar outputs

---

## Épicos e User Stories

### EP-01 — Infraestrutura e Configuração

#### US-001 — Configuração inicial do sistema
**Como** Pedro,
**Eu quero** configurar a URL do Ollama, a pasta de vídeos fonte e credenciais OAuth do YouTube,
**Para que** o sistema esteja pronto para operar antes de criar qualquer processamento.

**Critérios de Aceitação:**
- [ ] Campo para URL do Ollama (default: `http://localhost:11434`)
- [ ] Campo para pasta raiz dos vídeos fonte (com validação de existência)
- [ ] Upload ou path das credenciais OAuth (client_secrets.json)
- [ ] Configurações persistidas no banco de dados
- [ ] Tela de configurações acessível via aba na interface

**Prioridade:** Must | **Estimativa:** M

---

#### US-002 — Listagem de modelos disponíveis no Ollama
**Como** Pedro,
**Eu quero** ver os modelos disponíveis no meu Ollama local,
**Para que** eu possa selecionar o modelo adequado para geração de texto.

**Critérios de Aceitação:**
- [ ] Interface consulta a API do Ollama e lista os modelos instalados
- [ ] Modelo selecionado é persistido nas configurações
- [ ] Exibe mensagem de erro se Ollama não estiver acessível

**Prioridade:** Must | **Estimativa:** P

---

### EP-02 — Gestão de Contas YouTube

#### US-003 — Conectar conta do YouTube via OAuth2
**Como** Pedro,
**Eu quero** conectar uma conta do YouTube ao sistema via autenticação OAuth2,
**Para que** o sistema possa fazer uploads em meu nome.

**Critérios de Aceitação:**
- [ ] Botão "Conectar conta" inicia fluxo OAuth2 no browser
- [ ] Após autorização, tokens são armazenados de forma segura no banco
- [ ] Nome do canal e avatar são exibidos após conexão
- [ ] Suporte a múltiplas contas simultâneas

**Prioridade:** Must | **Estimativa:** G

---

#### US-004 — Gerenciar contas conectadas
**Como** Pedro,
**Eu quero** visualizar, testar e remover contas conectadas,
**Para que** eu mantenha controle sobre quais canais estão autorizados.

**Critérios de Aceitação:**
- [ ] Lista todas as contas com nome, canal e status do token
- [ ] Botão "Testar conexão" valida se o token ainda é válido
- [ ] Botão "Desconectar" revoga e remove os tokens
- [ ] Status visual: ativo (verde), expirado (amarelo), inválido (vermelho)

**Prioridade:** Must | **Estimativa:** M

---

#### US-005 — Selecionar contas para upload
**Como** Pedro,
**Eu quero** selecionar quais contas receberão o upload de um vídeo específico,
**Para que** eu publique no canal certo sem afetar os outros.

**Critérios de Aceitação:**
- [ ] Checkbox por conta no formulário de novo processamento
- [ ] Pelo menos uma conta deve ser selecionada para prosseguir
- [ ] Possível selecionar múltiplas contas (upload para N canais)

**Prioridade:** Must | **Estimativa:** P

---

### EP-03 — Geração de Texto

#### US-006 — Gerar texto via Ollama com prompt customizado
**Como** Pedro,
**Eu quero** gerar textos para narração usando meu Ollama local com um prompt de instrução customizado,
**Para que** o conteúdo seja relevante ao nicho do meu canal.

**Critérios de Aceitação:**
- [ ] Campo de texto para inserir o prompt de instrução
- [ ] Seletor do modelo Ollama a ser usado
- [ ] Geração de texto dispara request à API local do Ollama
- [ ] Texto gerado é exibido e editável antes de prosseguir
- [ ] Indicador de carregamento durante a geração

**Prioridade:** Must | **Estimativa:** M

---

#### US-007 — Inserir texto manualmente (sem IA)
**Como** Ana,
**Eu quero** desativar a geração por IA e inserir o texto de narração manualmente,
**Para que** eu tenha controle total sobre o conteúdo quando necessário.

**Critérios de Aceitação:**
- [ ] Toggle "Usar IA / Texto manual" no formulário
- [ ] Quando manual, campo de textarea para input do texto
- [ ] Texto manual segue o mesmo pipeline de TTS normalmente

**Prioridade:** Must | **Estimativa:** P

---

#### US-008 — Gerar múltiplos textos em lote
**Como** Pedro,
**Eu quero** gerar N textos de uma vez usando Ollama,
**Para que** eu prepare um lote de vídeos para publicação futura.

**Critérios de Aceitação:**
- [ ] Campo numérico para quantidade de textos desejados
- [ ] Cada texto é gerado sequencialmente e salvo
- [ ] Progress bar mostrando N/total gerados
- [ ] Possível cancelar a geração em lote

**Prioridade:** Should | **Estimativa:** M

---

### EP-04 — Geração de Áudio (TTS)

#### US-009 — Gerar áudio em inglês com duração alvo
**Como** Pedro,
**Eu quero** gerar um áudio narrado em inglês a partir do texto, com uma duração aproximada configurável,
**Para que** o vídeo final tenha a duração desejada.

**Critérios de Aceitação:**
- [ ] Campo para definir duração alvo em segundos (ex: 60s)
- [ ] Sistema ajusta o texto (trunca ou expande) para atingir a duração alvo
- [ ] Áudio gerado em inglês com voz configurável
- [ ] Arquivo de áudio salvo com nome único por processamento
- [ ] Duração real do áudio gerado é verificada e exibida

**Prioridade:** Must | **Estimativa:** M

---

#### US-010 — Selecionar voz para TTS
**Como** Pedro,
**Eu quero** selecionar a voz que será usada para a narração,
**Para que** eu varie o estilo entre diferentes vídeos.

**Critérios de Aceitação:**
- [ ] Lista de vozes disponíveis em inglês (pelo menos 5 opções)
- [ ] Voz selecionada persistida nas configurações
- [ ] Preview de voz disponível (gera 5s de teste)

**Prioridade:** Should | **Estimativa:** P

---

### EP-05 — Processamento de Vídeo

#### US-011 — Configurar pasta de vídeos fonte
**Como** Pedro,
**Eu quero** configurar uma pasta onde ficam meus vídeos fonte para corte,
**Para que** o sistema saiba onde buscar o material bruto.

**Critérios de Aceitação:**
- [ ] Campo de path da pasta nas configurações
- [ ] Sistema valida existência da pasta e lista os vídeos suportados (.mp4, .mov, .avi)
- [ ] Quantidade de vídeos disponíveis é exibida

**Prioridade:** Must | **Estimativa:** P

---

#### US-012 — Selecionar vídeos aleatoriamente por duração necessária
**Como** Pedro,
**Eu quero** que o sistema selecione vídeos aleatoriamente da pasta de forma a cobrir a duração do áudio,
**Para que** o vídeo final tenha a mesma duração que o áudio.

**Critérios de Aceitação:**
- [ ] Sistema calcula quantos segundos de vídeo são necessários
- [ ] Seleciona vídeos aleatoriamente até cobrir a duração
- [ ] Mesmo vídeo pode ser usado mais de uma vez se necessário
- [ ] Log mostra quais vídeos foram selecionados

**Prioridade:** Must | **Estimativa:** M

---

#### US-013 — Realizar cortes anti-plágio nos vídeos
**Como** Pedro,
**Eu quero** que o sistema corte os vídeos selecionados em clipes de 3-6 segundos de forma aleatória,
**Para que** o vídeo final não seja detectado como cópia.

**Critérios de Aceitação:**
- [ ] Cada clipe tem entre 3 e 6 segundos de duração (aleatório)
- [ ] Ponto de início de cada corte é aleatório dentro do vídeo fonte
- [ ] Total de segundos cortados cobre a duração do áudio

**Prioridade:** Must | **Estimativa:** M

---

#### US-014 — Sequenciamento anti-plágio (sem clipes consecutivos do mesmo vídeo)
**Como** Pedro,
**Eu quero** que a sequência dos clipes alterne entre diferentes vídeos fonte,
**Para que** o padrão de cortes não seja detectado como plágio.

**Critérios de Aceitação:**
- [ ] Nenhum clipe do mesmo vídeo aparece consecutivamente na sequência
- [ ] Algoritmo distribui os clipes de forma equilibrada
- [ ] Se apenas um vídeo foi selecionado, aplica variações de corte
- [ ] Log exibe a sequência final de clipes

**Prioridade:** Must | **Estimativa:** G

---

#### US-015 — Montar vídeo final com áudio
**Como** Pedro,
**Eu quero** que o sistema monte os clipes na sequência definida e aplique o áudio gerado,
**Para que** o resultado seja um vídeo final pronto para upload.

**Critérios de Aceitação:**
- [ ] Clipes são concatenados na sequência definida pelo algoritmo
- [ ] Áudio TTS é aplicado ao vídeo concatenado
- [ ] Vídeo final exportado em MP4 (H.264 + AAC)
- [ ] Arquivo salvo com nome único por processamento

**Prioridade:** Must | **Estimativa:** G

---

#### US-016 — Suporte a dimensões 16:9 e 9:16
**Como** Pedro,
**Eu quero** escolher entre os formatos horizontal (16:9) e vertical (9:16) para o vídeo final,
**Para que** eu publique no formato adequado para YouTube Shorts ou vídeos normais.

**Critérios de Aceitação:**
- [ ] Seletor de dimensão (16:9 padrão / 9:16)
- [ ] Para 9:16, opção de fazer crop centralizado ou barras pretas
- [ ] Dimensão aplicada durante a montagem do vídeo

**Prioridade:** Must | **Estimativa:** M

---

### EP-06 — Metadados e Upload

#### US-017 — Gerar título e descrição via Ollama
**Como** Pedro,
**Eu quero** que o sistema gere automaticamente título e descrição para o vídeo usando Ollama,
**Para que** eu não precise escrever metadados manualmente.

**Critérios de Aceitação:**
- [ ] Título gerado com base no texto de narração (máx. 100 caracteres)
- [ ] Descrição gerada com base no texto (máx. 5000 caracteres)
- [ ] Ambos editáveis antes do upload
- [ ] Opção de regenerar título/descrição separadamente

**Prioridade:** Must | **Estimativa:** M

---

#### US-018 — Upload do vídeo para YouTube
**Como** Pedro,
**Eu quero** que o sistema realize o upload do vídeo final para as contas selecionadas,
**Para que** o vídeo seja publicado sem intervenção manual.

**Critérios de Aceitação:**
- [ ] Upload usa a YouTube Data API v3
- [ ] Progress de upload exibido em tempo real
- [ ] URL do vídeo publicado salva no banco após sucesso
- [ ] Tratamento de erro com mensagem clara em caso de falha
- [ ] Suporte a upload para múltiplas contas sequencialmente

**Prioridade:** Must | **Estimativa:** G

---

#### US-019 — Agendamento de publicação
**Como** Ana,
**Eu quero** configurar data e hora para que o vídeo seja publicado automaticamente,
**Para que** eu publique em horários estratégicos sem estar online.

**Critérios de Aceitação:**
- [ ] Datepicker + timepicker para data/hora de publicação
- [ ] Vídeo enviado ao YouTube como "privado" e agendado para a data configurada
- [ ] Status "agendado" visível na tela de processamentos
- [ ] Opção "publicar imediatamente" (padrão)

**Prioridade:** Must | **Estimativa:** M

---

### EP-07 — Monitoramento e Debug

#### US-020 — Dashboard de status dos processamentos
**Como** Ana,
**Eu quero** visualizar o status de todos os processamentos em andamento e concluídos,
**Para que** eu saiba o que está acontecendo no sistema a qualquer momento.

**Critérios de Aceitação:**
- [ ] Lista de processamentos com: nome, status, progresso, data
- [ ] Status: pendente, em andamento, concluído, erro
- [ ] Atualização em tempo real via SSE
- [ ] Filtro por status

**Prioridade:** Must | **Estimativa:** M

---

#### US-021 — Executar etapas individuais do pipeline
**Como** Carlos,
**Eu quero** executar cada etapa do pipeline de forma isolada,
**Para que** eu depure problemas sem precisar rodar o pipeline completo.

**Critérios de Aceitação:**
- [ ] Cada etapa tem um botão "Executar apenas esta etapa"
- [ ] Etapas podem ser executadas fora de ordem (modo debug)
- [ ] Input de cada etapa pode ser configurado manualmente

**Prioridade:** Must | **Estimativa:** G

---

#### US-022 — Inspecionar output de cada etapa
**Como** Carlos,
**Eu quero** visualizar o output de cada etapa do pipeline,
**Para que** eu valide os resultados intermediários antes de prosseguir.

**Critérios de Aceitação:**
- [ ] Output de cada etapa exibido na interface (texto, áudio player, vídeo preview)
- [ ] Log detalhado de cada etapa com timestamps
- [ ] Opção de baixar o output de cada etapa

**Prioridade:** Must | **Estimativa:** M

---

## Backlog Priorizado (Ordem de Desenvolvimento)

### Fase 1 — Fundação (Must, sem dependências)
1. US-001 — Configuração inicial
2. US-002 — Listagem de modelos Ollama
3. US-011 — Configurar pasta de vídeos

### Fase 2 — Core de IA e Áudio
4. US-006 — Gerar texto via Ollama
5. US-007 — Texto manual
6. US-009 — Gerar áudio TTS
7. US-010 — Selecionar voz TTS

### Fase 3 — Pipeline de Vídeo
8. US-012 — Selecionar vídeos por duração
9. US-013 — Cortes anti-plágio
10. US-014 — Sequenciamento anti-plágio
11. US-015 — Montar vídeo final
12. US-016 — Dimensões 16:9 / 9:16

### Fase 4 — YouTube
13. US-003 — Conectar conta OAuth2
14. US-004 — Gerenciar contas
15. US-005 — Selecionar contas para upload
16. US-017 — Gerar título e descrição
17. US-018 — Upload para YouTube
18. US-019 — Agendamento

### Fase 5 — Monitoramento e Debug
19. US-020 — Dashboard de status
20. US-021 — Executar etapas isoladas
21. US-022 — Inspecionar outputs

### Fase 6 — Features Secundárias (Should)
22. US-008 — Geração em lote

---

## Definition of Done

- [ ] Código implementado e revisado
- [ ] Endpoint ou funcionalidade documentada
- [ ] Critérios de aceitação validados manualmente
- [ ] Sem erros no console (frontend e backend)
- [ ] Módulo é independente e testável em isolamento
- [ ] Variáveis sensíveis em variáveis de ambiente (nunca hardcode)
