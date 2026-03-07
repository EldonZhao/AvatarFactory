# AvatarFactory Dockerfile - Full Version with Monitor + Journal + Admin SSR
# For Azure deployment

# Stage 1: Build the Monitor SSR website
FROM node:20-alpine AS monitor-builder

WORKDIR /web

# Copy package files
COPY web/package*.json ./

# Install dependencies
RUN npm ci --silent

# Copy source
COPY web/ ./

# Fix permissions and build SSR with /monitor base path
ENV ASTRO_BASE=/monitor
RUN chmod -R +x node_modules/.bin && npm run build

# Stage 2: Build the Journal SSR website
FROM node:20-alpine AS journal-builder

WORKDIR /web-journal

# Copy package files
COPY web-journal/package*.json ./

# Install dependencies
RUN npm ci --silent

# Copy source
COPY web-journal/ ./

# Fix permissions and build SSR with /journal base path
ENV ASTRO_BASE=/journal
RUN chmod -R +x node_modules/.bin && npm run build

# Stage 3: Build the Admin SSR website
FROM node:20-alpine AS admin-builder

WORKDIR /web-admin

# Copy package files
COPY web-admin/package*.json ./

# Install dependencies
RUN npm ci --silent

# Copy source
COPY web-admin/ ./

# Fix permissions and build SSR with /admin base path
ENV ASTRO_BASE=/admin
RUN chmod -R +x node_modules/.bin && npm run build

# Stage 4: Main application
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies + build tools for pip packages + nginx + playwright deps + fonts + locales
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libffi-dev \
    nginx \
    supervisor \
    gnupg \
    locales \
    # Playwright dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    # Chinese fonts and emoji for screenshot rendering
    fonts-noto-cjk \
    fonts-noto-color-emoji \
    fonts-wqy-zenhei \
    fonts-symbola \
    fontconfig \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -fv

# Generate zh_CN locale for Chinese date formatting
RUN sed -i '/zh_CN.UTF-8/s/^# //g' /etc/locale.gen && locale-gen

# Install Node.js 20 from NodeSource
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies directly (no build stage)
COPY requirements-deploy.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install playwright browsers (chromium only to save space)
RUN playwright install chromium

# Copy application code
COPY avatarfactory/ ./avatarfactory/
COPY scripts/ ./scripts/
COPY pyproject.toml setup.py README.md ./

# Install package
RUN pip install --no-cache-dir -e .

# Copy Monitor SSR build from builder (dist + node_modules for runtime deps)
COPY --from=monitor-builder /web/dist /app/monitor
COPY --from=monitor-builder /web/node_modules /app/monitor/node_modules

# Copy Journal SSR build from builder (dist + node_modules for runtime deps)
COPY --from=journal-builder /web-journal/dist /app/journal
COPY --from=journal-builder /web-journal/node_modules /app/journal/node_modules

# Copy Admin SSR build from builder (dist + node_modules for runtime deps)
COPY --from=admin-builder /web-admin/dist /app/admin
COPY --from=admin-builder /web-admin/node_modules /app/admin/node_modules

# Create knowledge directory
RUN mkdir -p /app/knowledges

# Copy supervisor config
COPY scripts/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Make start script executable
RUN chmod +x /app/scripts/start_services.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV AVATARFACTORY_KB_PATH=/app/knowledges
ENV API_BASE_URL=http://127.0.0.1:8000
ENV MONITOR_PORT=4321
ENV JOURNAL_PORT=4322
ENV ADMIN_PORT=4323
ENV LANG=zh_CN.UTF-8
ENV LC_ALL=zh_CN.UTF-8

# Expose port 80 (nginx reverse proxy)
EXPOSE 80

# Health check - check API through nginx
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Start all services via supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
