FROM python:3.11-slim

WORKDIR /workspace

# Install dependencies first for cache efficiency.
COPY requirements.txt requirements-dev.txt pyproject.toml setup.py README.md ./
COPY avatarfactory ./avatarfactory
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements-dev.txt \
    && pip install --no-cache-dir -e ".[service]"

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV AVATARFACTORY_KB_PATH=/workspace/knowledges

EXPOSE 8000
