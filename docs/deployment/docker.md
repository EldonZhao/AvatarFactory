# Docker Deployment

Deploy AvatarFactory using Docker and docker-compose.

---

## Quick Start

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
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
curl http://localhost:8000/health
```

## Build from Source

```bash
docker build -t avatarfactory:latest .
docker run -p 8000:80 --env-file .env -v ./knowledges:/app/knowledges avatarfactory:latest
```

## For Azure deployment

See [azure.md](azure.md) for deploying to Azure Web App for Containers with ACR.
