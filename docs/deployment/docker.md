# Docker Deployment

Deploy AvatarFactory using Docker Compose.

---

## Quick Start

```bash
# Development stack (API + admin + journal, hot-reload)
docker compose -f docker-compose.dev.yml up -d

# Production-like single container stack
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

## Configuration

Set environment variables in `docker-compose.yml` or pass a `.env` file:

```yaml
services:
  avatarfactory:
    env_file:
      - .env
```

Required variables:
- `AVATARFACTORY_LLM_PROVIDER` — anthropic | azure_openai | openai
- Your provider's API key (e.g., `ANTHROPIC_API_KEY`)

See [configuration.md](../configuration.md) for all options.

## Persistent Storage

The `knowledges/` directory stores all personas, content, and experiment data. Mount it as a volume to persist data:

```yaml
volumes:
  - ./knowledges:/app/knowledges
```

## Health Check

```bash
curl http://localhost/health
```

## Build from Source

```bash
docker build -t avatarfactory:latest .
docker run -p 80:80 --env-file .env -v ./knowledges:/app/knowledges avatarfactory:latest
```

## For Azure deployment

See [azure.md](azure.md) for deploying to Azure Web App for Containers with ACR.
