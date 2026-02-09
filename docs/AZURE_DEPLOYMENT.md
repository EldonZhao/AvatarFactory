# Azure Deployment Guide

This guide covers deploying AvatarFactory to Azure Web App for Containers.

## Prerequisites

- Azure CLI installed and logged in (`az login`)
- Azure subscription with sufficient permissions

## Quick Deploy (Existing Infrastructure)

If infrastructure already exists, deploy latest code with:

```powershell
# Build and push image to ACR
az acr build --registry avatarfactoryappacr --image avatarfactory:latest --file Dockerfile .

# Stop and start webapp (cold restart) to force pull latest image
# Note: Simple restart may not pull new image due to caching
az webapp stop --resource-group avatarfactory-rg --name avatarfactory-app
az webapp start --resource-group avatarfactory-rg --name avatarfactory-app

# Wait for container to start (about 30-60 seconds)
# Then verify deployment
curl https://avatarfactory-app.azurewebsites.net/health
```

**Important:** A simple `az webapp restart` may not pull the latest image due to Docker layer caching. Use stop/start for a cold restart that forces a fresh image pull.

## Full Deployment (First Time)

### Option 1: PowerShell Script

```powershell
# Run from project root
.\.azure\deploy.ps1 -Force

# Or with custom parameters
.\.azure\deploy.ps1 -ResourceGroup "my-rg" -Location "eastasia" -AppName "my-app" -Force
```

### Option 2: Bash Script (Linux/WSL)

```bash
# Run from project root
./.azure/deploy.sh avatarfactory-rg eastasia avatarfactory-app
```

### Option 3: Manual Steps

#### 1. Create Resource Group
```bash
az group create --name avatarfactory-rg --location eastasia
```

#### 2. Create Azure Container Registry
```bash
az acr create --resource-group avatarfactory-rg --name avatarfactoryappacr --sku Basic --admin-enabled true
```

#### 3. Build and Push Docker Image
```bash
az acr build --registry avatarfactoryappacr --image avatarfactory:latest --file Dockerfile .
```

#### 4. Create Storage Account and File Share
```bash
# Create storage account
az storage account create --resource-group avatarfactory-rg --name avatarfactoryappstorage --location eastasia --sku Standard_LRS

# Get storage key
STORAGE_KEY=$(az storage account keys list --resource-group avatarfactory-rg --account-name avatarfactoryappstorage --query "[0].value" -o tsv)

# Create file share for knowledges
az storage share create --account-name avatarfactoryappstorage --account-key $STORAGE_KEY --name knowledges --quota 5
```

#### 5. Create App Service Plan
```bash
az appservice plan create --resource-group avatarfactory-rg --name avatarfactory-app-plan --sku B1 --is-linux
```

#### 6. Create Web App
```bash
# Get ACR credentials
ACR_LOGIN_SERVER=$(az acr show --name avatarfactoryappacr --query loginServer -o tsv)
ACR_USERNAME=$(az acr credential show --name avatarfactoryappacr --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name avatarfactoryappacr --query "passwords[0].value" -o tsv)

# Create webapp
az webapp create \
    --resource-group avatarfactory-rg \
    --plan avatarfactory-app-plan \
    --name avatarfactory-app \
    --container-image-name "$ACR_LOGIN_SERVER/avatarfactory:latest" \
    --container-registry-url "https://$ACR_LOGIN_SERVER" \
    --container-registry-user "$ACR_USERNAME" \
    --container-registry-password "$ACR_PASSWORD"
```

#### 7. Mount Azure File Share
```bash
az webapp config storage-account add \
    --resource-group avatarfactory-rg \
    --name avatarfactory-app \
    --custom-id "knowledges" \
    --storage-type AzureFiles \
    --share-name knowledges \
    --account-name avatarfactoryappstorage \
    --access-key "$STORAGE_KEY" \
    --mount-path "/app/knowledges"
```

#### 8. Configure App Settings
```bash
az webapp config appsettings set \
    --resource-group avatarfactory-rg \
    --name avatarfactory-app \
    --settings \
        AVATARFACTORY_KB_PATH="/app/knowledges" \
        WEBSITES_PORT="80" \
        DOCKER_ENABLE_CI="true"
```

#### 9. Configure Health Check
```bash
WEBAPP_ID=$(az webapp show --resource-group avatarfactory-rg --name avatarfactory-app --query id -o tsv)
az resource update --ids "$WEBAPP_ID/config/web" --set properties.healthCheckPath="/health"
```

## Post-Deployment Configuration

### Configure LLM API Keys

```bash
az webapp config appsettings set \
    --resource-group avatarfactory-rg \
    --name avatarfactory-app \
    --settings \
        ANTHROPIC_API_KEY="your_anthropic_key" \
        AVATARFACTORY_LLM_PROVIDER="anthropic" \
        AVATARFACTORY_MODEL="claude-3-5-sonnet-20241022"
```

### Configure Platform Connectors (Optional)

```bash
# Bluesky
az webapp config appsettings set -g avatarfactory-rg -n avatarfactory-app \
    --settings BLUESKY_USERNAME="..." BLUESKY_PASSWORD="..."

# WeChat Work Webhook
az webapp config appsettings set -g avatarfactory-rg -n avatarfactory-app \
    --settings AVATARFACTORY_WEBHOOK_URL="https://qyapi.weixin.qq.com/..."
```

## Verification

```bash
# Health check
curl https://avatarfactory-app.azurewebsites.net/health

# API docs
# Open in browser: https://avatarfactory-app.azurewebsites.net/docs
```

## Monitoring

```bash
# View logs
az webapp log tail --resource-group avatarfactory-rg --name avatarfactory-app

# View deployment logs
az webapp log deployment show --resource-group avatarfactory-rg --name avatarfactory-app
```

## Troubleshooting

### New image not deployed after restart
If the webapp is still running old code after `az webapp restart`:

```bash
# Use stop/start instead of restart for a cold restart
az webapp stop --resource-group avatarfactory-rg --name avatarfactory-app
az webapp start --resource-group avatarfactory-rg --name avatarfactory-app

# Or force update the container image reference
az webapp config container set \
    --resource-group avatarfactory-rg \
    --name avatarfactory-app \
    --container-image-name "avatarfactoryappacr.azurecr.io/avatarfactory:latest"
az webapp restart --resource-group avatarfactory-rg --name avatarfactory-app
```

### Container not starting
```bash
# Check container settings
az webapp config container show --resource-group avatarfactory-rg --name avatarfactory-app

# Check logs
az webapp log tail --resource-group avatarfactory-rg --name avatarfactory-app
```

### Storage mount issues
```bash
# Verify storage mount
az webapp config storage-account list --resource-group avatarfactory-rg --name avatarfactory-app
```

### Azure CLI encoding error on Windows
If you see `'charmap' codec can't encode characters` error, set encoding before running commands:
```powershell
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

## Resource Summary

| Resource | Name | Purpose |
|----------|------|---------|
| Resource Group | avatarfactory-rg | Contains all resources |
| Container Registry | avatarfactoryappacr | Docker image storage |
| Storage Account | avatarfactoryappstorage | Persistent file storage |
| File Share | knowledges | Persona and content data |
| App Service Plan | avatarfactory-app-plan | Hosting plan (B1 SKU) |
| Web App | avatarfactory-app | Application container |

## URLs

- **Web App**: https://avatarfactory-app.azurewebsites.net
- **Health Check**: https://avatarfactory-app.azurewebsites.net/health
- **API Docs**: https://avatarfactory-app.azurewebsites.net/docs
