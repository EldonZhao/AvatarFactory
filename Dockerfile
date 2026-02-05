# AvatarFactory Dockerfile
# Multi-stage build for production deployment

# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy package files
COPY pyproject.toml setup.py ./
COPY avatarfactory/ ./avatarfactory/

# Install package
RUN pip install --no-cache-dir --user -e .

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts are in PATH
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY avatarfactory/ ./avatarfactory/
COPY pyproject.toml setup.py ./

# Create knowledge directory
RUN mkdir -p /app/knowledges

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV AVATARFACTORY_KB_PATH=/app/knowledges

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["python", "-m", "avatarfactory.daemon_runner", "--mode", "full", "--host", "0.0.0.0", "--port", "8000"]
