# =============================================================================
# Makefile — YouTube Automation
# Atalhos para operações comuns de desenvolvimento e produção.
#
# Pré-requisitos:
#   - Docker 24+ com Compose plugin v2+
#   - GNU Make:
#       Linux/Mac: já incluído no sistema
#       Windows:   choco install make  ou  winget install GnuWin32.Make
#       Alternativa Windows: use scripts/run.ps1
#
# Uso: make <comando>
#      Ex: make dev
# =============================================================================

DOCKER_COMPOSE     := docker compose
DOCKER_COMPOSE_DEV := docker compose -f docker-compose.yml -f docker-compose.dev.yml
ENV_FILE           := .env
ENV_EXAMPLE        := .env.example

# Cor para output
GREEN  := \033[0;32m
YELLOW := \033[1;33m
RESET  := \033[0m

.PHONY: help setup dev prod stop test test-backend test-frontend \
        lint lint-backend lint-frontend build build-backend build-frontend \
        clean clean-volumes logs ps health shell-backend shell-frontend

# Alvo padrão — exibe ajuda
.DEFAULT_GOAL := help

## help: Exibe esta mensagem de ajuda
help:
	@echo ""
	@echo "$(GREEN)YouTube Automation — Comandos disponíveis$(RESET)"
	@echo ""
	@echo "$(YELLOW)Ambiente:$(RESET)"
	@echo "  make setup            Cria .env e diretórios necessários"
	@echo "  make dev              Inicia modo desenvolvimento (hot reload)"
	@echo "  make prod             Inicia modo produção (detached)"
	@echo "  make stop             Para todos os containers"
	@echo ""
	@echo "$(YELLOW)Testes:$(RESET)"
	@echo "  make test             Roda todos os testes (backend + frontend)"
	@echo "  make test-backend     Roda testes do backend (pytest)"
	@echo "  make test-frontend    Roda testes do frontend (vitest)"
	@echo ""
	@echo "$(YELLOW)Qualidade de Código:$(RESET)"
	@echo "  make lint             Roda todos os linters"
	@echo "  make lint-backend     Lint do backend (ruff + black)"
	@echo "  make lint-frontend    Lint do frontend (eslint + prettier)"
	@echo ""
	@echo "$(YELLOW)Build:$(RESET)"
	@echo "  make build            Build das imagens Docker (produção)"
	@echo "  make build-backend    Build apenas do backend"
	@echo "  make build-frontend   Build apenas do frontend"
	@echo ""
	@echo "$(YELLOW)Utilitários:$(RESET)"
	@echo "  make clean            Remove containers e imagens locais"
	@echo "  make clean-volumes    Remove containers, imagens E volumes (dados!)"
	@echo "  make logs             Exibe logs em tempo real"
	@echo "  make ps               Status dos containers"
	@echo "  make health           Verifica saúde do ambiente"
	@echo "  make shell-backend    Abre shell no container backend"
	@echo "  make shell-frontend   Abre shell no container frontend"
	@echo ""

## setup: Cria .env a partir do .env.example e estrutura de diretórios
setup:
	@if [ ! -f $(ENV_FILE) ]; then \
		cp $(ENV_EXAMPLE) $(ENV_FILE); \
		echo "$(GREEN)✓ .env criado$(RESET) — edite com suas configurações antes de iniciar"; \
	else \
		echo "$(YELLOW)⚠ .env já existe$(RESET) — não sobrescrito"; \
	fi
	@mkdir -p data videos output logs
	@touch data/.gitkeep videos/.gitkeep output/.gitkeep logs/.gitkeep
	@echo "$(GREEN)✓ Diretórios criados$(RESET): data/ videos/ output/ logs/"
	@echo ""
	@echo "Próximos passos:"
	@echo "  1. Edite o .env e configure SECRET_KEY e VIDEOS_FOLDER_HOST"
	@echo "  2. Certifique-se que o Ollama está rodando: ollama serve"
	@echo "  3. Execute: make dev"

## dev: Inicia ambiente de desenvolvimento com hot reload
dev: setup
	@echo "$(GREEN)Iniciando modo desenvolvimento...$(RESET)"
	@echo "  Backend:  http://localhost:8000"
	@echo "  Frontend: http://localhost:5173"
	@echo "  API Docs: http://localhost:8000/docs"
	@echo ""
	$(DOCKER_COMPOSE_DEV) up --build

## prod: Inicia em modo produção (background)
prod: setup
	@echo "$(GREEN)Iniciando modo produção...$(RESET)"
	$(DOCKER_COMPOSE) up --build -d
	@echo ""
	@echo "$(GREEN)✓ Aplicação iniciada$(RESET)"
	@echo "  Frontend: http://localhost:${FRONTEND_PORT:-80}"
	@echo "  Backend:  http://localhost:${BACKEND_PORT:-8000}"
	@echo ""
	@echo "Logs: make logs | Status: make ps | Parar: make stop"

## stop: Para e remove todos os containers
stop:
	@echo "Parando containers..."
	$(DOCKER_COMPOSE) down
	$(DOCKER_COMPOSE_DEV) down 2>/dev/null || true

## test: Executa todos os testes (backend + frontend)
test: test-backend test-frontend
	@echo "$(GREEN)✓ Todos os testes concluídos$(RESET)"

## test-backend: Executa testes do backend com relatório de cobertura
test-backend:
	@echo "$(GREEN)Executando testes do backend...$(RESET)"
	$(DOCKER_COMPOSE_DEV) run --rm backend \
		pytest tests/ -v \
		--cov=app \
		--cov-report=term-missing \
		--cov-fail-under=70 \
		--tb=short

## test-frontend: Executa testes do frontend
test-frontend:
	@echo "$(GREEN)Executando testes do frontend...$(RESET)"
	$(DOCKER_COMPOSE_DEV) run --rm frontend \
		npm run test:run -- --coverage

## lint: Executa todos os linters
lint: lint-backend lint-frontend
	@echo "$(GREEN)✓ Lint concluído$(RESET)"

## lint-backend: Lint do backend (ruff + black)
lint-backend:
	@echo "$(GREEN)Lint do backend...$(RESET)"
	$(DOCKER_COMPOSE_DEV) run --rm backend sh -c \
		"ruff check . && black --check --diff ."

## lint-frontend: Lint do frontend (eslint + prettier)
lint-frontend:
	@echo "$(GREEN)Lint do frontend...$(RESET)"
	$(DOCKER_COMPOSE_DEV) run --rm frontend sh -c \
		"npm run lint && npm run format:check"

## build: Build das imagens Docker de produção
build: build-backend build-frontend
	@echo "$(GREEN)✓ Build concluído$(RESET)"

## build-backend: Build apenas da imagem do backend
build-backend:
	@echo "$(GREEN)Build do backend...$(RESET)"
	$(DOCKER_COMPOSE) build --no-cache backend

## build-frontend: Build apenas da imagem do frontend
build-frontend:
	@echo "$(GREEN)Build do frontend...$(RESET)"
	$(DOCKER_COMPOSE) build --no-cache frontend

## clean: Remove containers e imagens locais (preserva volumes de dados)
clean:
	@echo "$(YELLOW)Removendo containers e imagens locais...$(RESET)"
	$(DOCKER_COMPOSE) down --rmi local --remove-orphans
	$(DOCKER_COMPOSE_DEV) down --rmi local --remove-orphans 2>/dev/null || true

## clean-volumes: Remove containers, imagens E volumes (APAGA DADOS!)
clean-volumes:
	@echo "$(YELLOW)ATENÇÃO: Esta operação apaga todos os dados (banco, credenciais, outputs).$(RESET)"
	@read -p "Continuar? [s/N] " confirm && [ "$$confirm" = "s" ] || exit 1
	$(DOCKER_COMPOSE) down --rmi local --volumes --remove-orphans
	$(DOCKER_COMPOSE_DEV) down --rmi local --volumes --remove-orphans 2>/dev/null || true
	@echo "$(GREEN)✓ Limpeza completa$(RESET)"

## logs: Exibe logs de todos os containers em tempo real
logs:
	$(DOCKER_COMPOSE) logs -f

## ps: Exibe status dos containers
ps:
	$(DOCKER_COMPOSE) ps

## health: Verifica saúde do ambiente (backend, DB, Ollama, FFmpeg, vídeos)
health:
	@echo "$(GREEN)Verificando saúde do ambiente...$(RESET)"
	python scripts/healthcheck.py

## shell-backend: Abre um shell interativo no container backend
shell-backend:
	$(DOCKER_COMPOSE_DEV) exec backend sh

## shell-frontend: Abre um shell interativo no container frontend
shell-frontend:
	$(DOCKER_COMPOSE_DEV) exec frontend sh
