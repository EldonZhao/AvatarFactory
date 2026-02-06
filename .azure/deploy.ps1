# =============================================================================
# AvatarFactory Azure Deployment Script (PowerShell)
# =============================================================================
#
# This script deploys AvatarFactory to Azure Web App for Containers.
#
# Prerequisites:
# - Azure CLI installed and logged in (az login)
# - Docker installed (for local build)
#
# Usage:
#   .\deploy.ps1 [-ResourceGroup <name>] [-Location <region>] [-AppName <name>]
#
# Example:
#   .\deploy.ps1 -ResourceGroup avatarfactory-rg -Location eastasia -AppName avatarfactory-app
#
# =============================================================================

param(
    [string]$ResourceGroup = "avatarfactory-rg",
    [string]$Location = "eastasia",
    [string]$AppName = "avatarfactory-app",
    [string]$Sku = "B1",
    [switch]$Force = $false
)

$ErrorActionPreference = "Stop"

# Set UTF-8 encoding to avoid Azure CLI output encoding issues
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Derived names (remove hyphens for Azure naming requirements)
$AcrName = ($AppName -replace '-', '') + "acr"
$StorageAccount = ($AppName -replace '-', '') + "storage"
$FileShare = "knowledges"
$AppServicePlan = "$AppName-plan"

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "AvatarFactory Azure Deployment" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "Resource Group: $ResourceGroup"
Write-Host "Location: $Location"
Write-Host "App Name: $AppName"
Write-Host "ACR Name: $AcrName"
Write-Host "Storage Account: $StorageAccount"
Write-Host "App Service Plan: $AppServicePlan"
Write-Host "SKU: $Sku"
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Confirm (skip with -Force)
if (-not $Force) {
    $confirm = Read-Host "Proceed with deployment? (y/N)"
    if ($confirm -ne "y" -and $confirm -ne "Y") {
        Write-Host "Deployment cancelled."
        exit 0
    }
}

Write-Host ""
Write-Host "Step 1: Creating Resource Group..." -ForegroundColor Green
az group create `
    --name $ResourceGroup `
    --location $Location `
    --output none

Write-Host "Step 2: Creating Azure Container Registry..." -ForegroundColor Green
az acr create `
    --resource-group $ResourceGroup `
    --name $AcrName `
    --sku Basic `
    --admin-enabled true `
    --output none

# Get ACR credentials
$AcrLoginServer = az acr show --name $AcrName --query loginServer -o tsv
$AcrUsername = az acr credential show --name $AcrName --query username -o tsv
$AcrPassword = az acr credential show --name $AcrName --query "passwords[0].value" -o tsv

Write-Host "Step 3: Building and pushing Docker image..." -ForegroundColor Green
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Push-Location $projectRoot

# Build and push using ACR Build (no local Docker required)
az acr build `
    --registry $AcrName `
    --image avatarfactory:latest `
    --file Dockerfile `
    .

Pop-Location

Write-Host "Step 4: Creating Storage Account..." -ForegroundColor Green
az storage account create `
    --resource-group $ResourceGroup `
    --name $StorageAccount `
    --location $Location `
    --sku Standard_LRS `
    --output none

# Get storage key
$StorageKey = az storage account keys list `
    --resource-group $ResourceGroup `
    --account-name $StorageAccount `
    --query "[0].value" -o tsv

Write-Host "Step 5: Creating File Share..." -ForegroundColor Green
az storage share create `
    --account-name $StorageAccount `
    --account-key $StorageKey `
    --name $FileShare `
    --quota 5 `
    --output none

Write-Host "Step 6: Creating App Service Plan..." -ForegroundColor Green
az appservice plan create `
    --resource-group $ResourceGroup `
    --name $AppServicePlan `
    --sku $Sku `
    --is-linux `
    --output none

Write-Host "Step 7: Creating Web App..." -ForegroundColor Green
az webapp create `
    --resource-group $ResourceGroup `
    --plan $AppServicePlan `
    --name $AppName `
    --container-image-name "$AcrLoginServer/avatarfactory:latest" `
    --container-registry-url "https://$AcrLoginServer" `
    --container-registry-user $AcrUsername `
    --container-registry-password $AcrPassword `
    --output none

Write-Host "Step 8: Mounting Azure File Share..." -ForegroundColor Green
az webapp config storage-account add `
    --resource-group $ResourceGroup `
    --name $AppName `
    --custom-id "knowledges" `
    --storage-type AzureFiles `
    --share-name $FileShare `
    --account-name $StorageAccount `
    --access-key $StorageKey `
    --mount-path "/app/knowledges" `
    --output none

Write-Host "Step 9: Configuring App Settings..." -ForegroundColor Green
az webapp config appsettings set `
    --resource-group $ResourceGroup `
    --name $AppName `
    --settings `
        AVATARFACTORY_KB_PATH="/app/knowledges" `
        WEBSITES_PORT="8000" `
        DOCKER_ENABLE_CI="true" `
    --output none

Write-Host "Step 10: Configuring Health Check..." -ForegroundColor Green
# Use az resource update for health check path (az webapp config set --health-check-path is deprecated)
$webappResourceId = az webapp show --resource-group $ResourceGroup --name $AppName --query id -o tsv
az resource update `
    --ids $webappResourceId/config/web `
    --set properties.healthCheckPath="/health" `
    --output none

Write-Host ""
Write-Host "=============================================" -ForegroundColor Green
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Web App URL: https://$AppName.azurewebsites.net" -ForegroundColor Yellow
Write-Host "Health Check: https://$AppName.azurewebsites.net/health" -ForegroundColor Yellow
Write-Host "API Docs: https://$AppName.azurewebsites.net/docs" -ForegroundColor Yellow
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "1. Configure LLM API keys in App Settings:"
Write-Host "   az webapp config appsettings set -g $ResourceGroup -n $AppName --settings ANTHROPIC_API_KEY=your_key"
Write-Host ""
Write-Host "2. Configure platform connectors as needed:"
Write-Host "   az webapp config appsettings set -g $ResourceGroup -n $AppName --settings BLUESKY_USERNAME=... BLUESKY_PASSWORD=..."
Write-Host ""
Write-Host "3. Monitor logs:"
Write-Host "   az webapp log tail -g $ResourceGroup -n $AppName"
Write-Host ""
