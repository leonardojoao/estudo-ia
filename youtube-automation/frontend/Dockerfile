# syntax=docker/dockerfile:1.6
# =============================================================================
# Frontend Dockerfile — YouTube Automation (Produção)
# Estágios: builder (Node 20) → runtime (Nginx Alpine)
# =============================================================================

# =============================================================================
# Stage 1: builder — compila o Vue 3 com Vite
# =============================================================================
FROM node:20-alpine AS builder

WORKDIR /app

# Instala dependências em camada separada (cache eficiente no CI)
COPY package*.json ./
RUN npm ci --prefer-offline

# Copia código-fonte e gera o build de produção
COPY . .
RUN npm run build

# =============================================================================
# Stage 2: runtime — Nginx servindo o build estático
# Imagem Alpine mínima (~25MB)
# =============================================================================
FROM nginx:1.25-alpine AS runtime

LABEL maintainer="youtube-automation" \
      description="Frontend Vue 3 — YouTube Automation" \
      version="1.0"

# Remove configuração padrão do Nginx
RUN rm /etc/nginx/conf.d/default.conf

# Configuração customizada: SPA (Vue Router history mode) + proxy para API + SSE
COPY nginx.conf /etc/nginx/conf.d/app.conf

# Artefatos do build Vue (arquivos estáticos com hashes de cache-busting)
COPY --from=builder /app/dist /usr/share/nginx/html

# Permissões corretas para o Nginx
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html

EXPOSE 80

# Health check via endpoint de status do Nginx
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost/health-frontend || exit 1

CMD ["nginx", "-g", "daemon off;"]
