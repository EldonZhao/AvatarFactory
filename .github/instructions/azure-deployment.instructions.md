---
applyTo: "**"
---

# Azure Deployment Instructions

When working on Azure deployment tasks for AvatarFactory, follow these conventions.

## Azure Resources

| Resource | Name |
|----------|------|
| Resource Group | `avatarfactory-rg` |
| App Service | `avatarfactory-app` |
| Container Registry | `avatarfactoryappacr` |
| URL | `https://avatarfactory-app.azurewebsites.net` |
| Kudu (SCM) | `https://avatarfactory-app.scm.azurewebsites.net` |

## Build and Deploy

Always build Docker images in ACR (no local Docker required):

```bash
az acr build --registry avatarfactoryappacr --image avatarfactory:latest .
az webapp restart --name avatarfactory-app --resource-group avatarfactory-rg
```

## Container Configuration

When configuring the App Service container:

1. Image source: `avatarfactoryappacr.azurecr.io/avatarfactory:latest`
2. ACR admin credentials must be enabled
3. Use `az webapp config container set` for image and registry config

## Required Environment Variables

| Variable | Value | Notes |
|----------|-------|-------|
| `WEBSITES_ENABLE_APP_SERVICE_STORAGE` | `true` | Persistent storage |
| `AVATARFACTORY_USE_DB` | `true` | Enable SQLite database |
| `AVATARFACTORY_KB_PATH` | `/home/knowledges` | Knowledge base directory |
| `AVATARFACTORY_LLM_PROVIDER` | `anthropic` | LLM provider |
| `AVATARFACTORY_MODEL` | `claude-3-5-sonnet-20241022` | Model name |
| `ANTHROPIC_API_KEY` | (secret) | Anthropic API key |

## Windows Git Bash Path Issue

Windows Git Bash converts Unix paths like `/home/knowledges` to Windows paths. Always prefix with `MSYS_NO_PATHCONV=1` when setting paths:

```bash
MSYS_NO_PATHCONV=1 az webapp config appsettings set \
  --name avatarfactory-app \
  --resource-group avatarfactory-rg \
  --settings AVATARFACTORY_KB_PATH=/home/knowledges
```

Verify: the setting should show `/home/knowledges`, not `C:/Program Files/Git/home/knowledges`.

## Database Management

- The app uses SQLite stored at `/home/knowledges/avatarfactory.db`
- Upload database via Kudu VFS API: `PUT /api/vfs/home/knowledges/avatarfactory.db`
- Migrate from file-based storage: `python -m avatarfactory.core.database.migrations.initial_migration`
- Always restart the app after database changes

## Kudu API Operations

For file operations and commands, use the Kudu SCM site with publishing credentials:

```bash
CREDS=$(az webapp deployment list-publishing-credentials \
  --name avatarfactory-app --resource-group avatarfactory-rg \
  --query "[publishingUserName,publishingPassword]" -o tsv)
```

- Create dirs: `POST /api/command` with `{"command":"mkdir -p /home/knowledges", "dir":"/"}`
- Upload files: `PUT /api/vfs/home/<path>`
- Run commands: `POST /api/command` with `{"command":"...", "dir":"/home/site/wwwroot"}`
- List files: `POST /api/command` with `{"command":"ls -la /home/knowledges/", "dir":"/"}`

## Troubleshooting

- Enable container logging: `az webapp log config --docker-container-logging filesystem`
- Download logs: `az webapp log download --log-file webapp_logs.zip`
- 502 errors: wait 60-90s after restart, then check logs and env vars
- Health check: `GET /health` should return `{"status":"healthy","version":"1.0.0"}`
