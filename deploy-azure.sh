#!/bin/bash

# Azure Container Registry name (must be globally unique)
ACR_NAME="ragapp16052004"
RESOURCE_GROUP="ragapp16052004"
LOCATION="australiaeast"
APP_NAME="ragapp16052004"

# Create Resource Group
echo "Creating resource group..."
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create Azure Container Registry
echo "Creating Azure Container Registry..."
az acr create --resource-group $RESOURCE_GROUP --name $ACR_NAME --sku Basic

# Enable admin user for ACR
echo "Enabling admin user for ACR..."
az acr update -n $ACR_NAME --admin-enabled true

# Get ACR credentials
ACR_USERNAME=$(az acr credential show -n $ACR_NAME --query "username" -o tsv)
ACR_PASSWORD=$(az acr credential show -n $ACR_NAME --query "passwords[0].value" -o tsv)

# Login to ACR
echo "Logging in to ACR..."
docker login $ACR_NAME.azurecr.io -u $ACR_USERNAME -p $ACR_PASSWORD

# Build and tag the Docker image
echo "Building and tagging Docker image..."
docker build -t $ACR_NAME.azurecr.io/$APP_NAME:latest .

# Push the image to ACR
echo "Pushing image to ACR..."
docker push $ACR_NAME.azurecr.io/$APP_NAME:latest

# Create App Service Plan (using F1 SKU - Free tier)
echo "Creating App Service Plan..."
az appservice plan create --name "${APP_NAME}-plan" \
    --resource-group $RESOURCE_GROUP \
    --sku F1 \
    --is-linux

# Create Web App for Containers
echo "Creating Web App for Containers..."
az webapp create --resource-group $RESOURCE_GROUP \
    --plan "${APP_NAME}-plan" \
    --name $APP_NAME \
    --deployment-container-image-name $ACR_NAME.azurecr.io/$APP_NAME:latest

# Configure Web App to use ACR (using updated commands)
echo "Configuring Web App to use ACR..."
az webapp config container set --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --container-image-name $ACR_NAME.azurecr.io/$APP_NAME:latest \
    --container-registry-url https://$ACR_NAME.azurecr.io \
    --container-registry-user $ACR_USERNAME \
    --container-registry-password $ACR_PASSWORD

# Configure environment variables
echo "Configuring environment variables..."
az webapp config appsettings set --resource-group $RESOURCE_GROUP \
    --name $APP_NAME \
    --settings \
    MYSQL_HOST="mysql.mysql.database.azure.com" \
    MYSQL_USER="root" \
    MYSQL_PASSWORD="16052004" \
    MYSQL_DATABASE="chathistory" \
    REDIS_HOST="redis.redis.cache.windows.net" \
    REDIS_PASSWORD="" \
    WEBSITES_PORT=5000

echo "Deployment completed! Your app should be available at https://$APP_NAME.azurewebsites.net" 