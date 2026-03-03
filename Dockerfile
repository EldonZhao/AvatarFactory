# AvatarFactory Dockerfile - Full Version with Dashboard + Chronicle SSR
# For Azure deployment

# Stage 1: Build the Chronicle SSR website
FROM node:20-alpine AS web-builder

WORKDIR /web

# Copy package files
COPY web/package*.json ./

# Install dependencies
RUN npm ci --silent

# Copy source
COPY web/ ./

# Fix permissions and build SSR with /chronicle base path
ENV ASTRO_BASE=/chronicle
RUN chmod -R +x node_modules/.bin && npm run build

# Stage 2: Main application
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies + build tools for pip packages + nginx + playwright deps + fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libffi-dev \
    nginx \
    supervisor \
    gnupg \
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

# Copy Chronicle SSR build from builder
COPY --from=web-builder /web/dist /app/chronicle

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
ENV CHRONICLE_PORT=4321

# Expose port 80 (nginx reverse proxy)
EXPOSE 80

# Health check - check API through nginx
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Start all services via supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
