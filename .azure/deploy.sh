#!/bin/bash
# =============================================================================
# AvatarFactory Azure Deployment Script
# =============================================================================
#
# This script deploys AvatarFactory to Azure Web App for Containers.
#
# Prerequisites:
# - Azure CLI installed and logged in (az login)
# - Docker installed (for local build)
#
# Usage:
#   ./deploy.sh [resource-group] [location] [app-name]
#
# Example:
#   ./deploy.sh avatarfactory-rg eastasia avatarfactory-app
#
# =============================================================================

set -e

# Default values
RESOURCE_GROUP="${1:-avatarfactory-rg}"
LOCATION="${2:-eastasia}"
APP_NAME="${3:-avatarfactory-app}"
SKU="${SKU:-B1}"

# Derived names
ACR_NAME="${APP_NAME//-/}acr"
STORAGE_ACCOUNT="${APP_NAME//-/}storage"
FILE_SHARE="knowledges"
APP_SERVICE_PLAN="${APP_NAME}-plan"

echo "============================================="
echo "AvatarFactory Azure Deployment"
echo "============================================="
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"
echo "App Name: $APP_NAME"
echo "ACR Name: $ACR_NAME"
echo "Storage Account: $STORAGE_ACCOUNT"
echo "App Service Plan: $APP_SERVICE_PLAN"
echo "SKU: $SKU"
echo "============================================="
echo ""

# Confirm
read -p "Proceed with deployment? (y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

echo ""
echo "Step 1: Creating Resource Group..."
az group create \
    --name "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --output none

echo "Step 2: Creating Azure Container Registry..."
az acr create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$ACR_NAME" \
    --sku Basic \
    --admin-enabled true \
    --output none

# Get ACR credentials
ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --query loginServer -o tsv)
ACR_USERNAME=$(az acr credential show --name "$ACR_NAME" --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name "$ACR_NAME" --query "passwords[0].value" -o tsv)

echo "Step 3: Building and pushing Docker image..."
cd "$(dirname "$0")/.."

# Build and push using ACR Build (no local Docker required)
az acr build \
    --registry "$ACR_NAME" \
    --image avatarfactory:latest \
    --file Dockerfile \
    .

echo "Step 4: Creating Storage Account..."
az storage account create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$STORAGE_ACCOUNT" \
    --location "$LOCATION" \
    --sku Standard_LRS \
    --output none

# Get storage key
STORAGE_KEY=$(az storage account keys list \
    --resource-group "$RESOURCE_GROUP" \
    --account-name "$STORAGE_ACCOUNT" \
    --query "[0].value" -o tsv)

echo "Step 5: Creating File Share..."
az storage share create \
    --account-name "$STORAGE_ACCOUNT" \
    --account-key "$STORAGE_KEY" \
    --name "$FILE_SHARE" \
    --quota 5 \
    --output none

echo "Step 6: Creating App Service Plan..."
az appservice plan create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$APP_SERVICE_PLAN" \
    --sku "$SKU" \
    --is-linux \
    --output none

echo "Step 7: Creating Web App..."
az webapp create \
    --resource-group "$RESOURCE_GROUP" \
    --plan "$APP_SERVICE_PLAN" \
    --name "$APP_NAME" \
    --deployment-container-image-name "$ACR_LOGIN_SERVER/avatarfactory:latest" \
    --docker-registry-server-url "https://$ACR_LOGIN_SERVER" \
    --docker-registry-server-user "$ACR_USERNAME" \
    --docker-registry-server-password "$ACR_PASSWORD" \
    --output none

echo "Step 8: Mounting Azure File Share..."
az webapp config storage-account add \
    --resource-group "$RESOURCE_GROUP" \
    --name "$APP_NAME" \
    --custom-id "knowledges" \
    --storage-type AzureFiles \
    --share-name "$FILE_SHARE" \
    --account-name "$STORAGE_ACCOUNT" \
    --access-key "$STORAGE_KEY" \
    --mount-path "/app/knowledges" \
    --output none

echo "Step 9: Configuring App Settings..."
az webapp config appsettings set \
    --resource-group "$RESOURCE_GROUP" \
    --name "$APP_NAME" \
    --settings \
        AVATARFACTORY_KB_PATH="/app/knowledges" \
        WEBSITES_PORT="8000" \
        DOCKER_ENABLE_CI="true" \
    --output none

echo "Step 10: Configuring Health Check..."
az webapp config set \
    --resource-group "$RESOURCE_GROUP" \
    --name "$APP_NAME" \
    --health-check-path "/health" \
    --output none

echo ""
echo "============================================="
echo "Deployment Complete!"
echo "============================================="
echo ""
echo "Web App URL: https://$APP_NAME.azurewebsites.net"
echo "Health Check: https://$APP_NAME.azurewebsites.net/health"
echo "API Docs: https://$APP_NAME.azurewebsites.net/docs"
echo ""
echo "Next Steps:"
echo "1. Configure LLM API keys in App Settings:"
echo "   az webapp config appsettings set -g $RESOURCE_GROUP -n $APP_NAME --settings ANTHROPIC_API_KEY=your_key"
echo ""
echo "2. Configure platform connectors as needed:"
echo "   az webapp config appsettings set -g $RESOURCE_GROUP -n $APP_NAME --settings BLUESKY_USERNAME=... BLUESKY_PASSWORD=..."
echo ""
echo "3. Monitor logs:"
echo "   az webapp log tail -g $RESOURCE_GROUP -n $APP_NAME"
echo ""
