# AvatarFactory Dockerfile - Full Version with Dashboard
# For Azure deployment

FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies + build tools for pip packages + nginx + playwright deps + fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libffi-dev \
    nginx \
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
    # Chinese fonts for screenshot rendering
    fonts-noto-cjk \
    fonts-wqy-zenhei \
    fontconfig \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -fv

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

# Create knowledge directory
RUN mkdir -p /app/knowledges

# Make start script executable
RUN chmod +x /app/scripts/start_services.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV AVATARFACTORY_KB_PATH=/app/knowledges

# Expose port 80 (nginx reverse proxy)
EXPOSE 80

# Health check - check API through nginx
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Start all services via script
CMD ["/bin/bash", "/app/scripts/start_services.sh"]
