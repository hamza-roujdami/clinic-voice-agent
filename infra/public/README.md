# Azure AI Foundry - Standard Agent Setup (Public Networking)

Simplified infrastructure for Clinic Voice Agent with **public networking** (no VNet/private endpoints).

Based on: [microsoft-foundry/foundry-samples - 41-standard-agent-setup](https://github.com/microsoft-foundry/foundry-samples/tree/main/infrastructure/infrastructure-setup-bicep/41-standard-agent-setup)

## What Gets Created

### Phase 1: AI Foundry (main.bicep)

| Resource | Purpose | Access |
|----------|---------|--------|
| AI Services Account | Foundry project host | Public |
| AI Project | Agent workspace | Public |
| Azure AI Search | Policy/FAQ search | Public |
| Cosmos DB | Session storage | Public |
| Storage Account | Agent file storage | Public |
| Model Deployment | gpt-4o-mini | - |

### Phase 2: App Hosting (app-hosting.bicep)

| Resource | Purpose | Access |
|----------|---------|--------|
| Container Apps | Voice Gateway API hosting | Public |
| Container Registry | Docker image storage | Public |
| API Management | AI Gateway | Public |
| Application Insights | Tracing & monitoring | Public |
| Log Analytics | Centralized logs | Public |

## Prerequisites

1. **Azure CLI** with Bicep extension
2. **Permissions**: Azure AI Account Owner + Role Based Access Administrator
3. **jq** installed (for deploy script)

## Quick Deploy (Recommended)

```bash
# One-command deployment
cd infra/public
chmod +x deploy.sh
./deploy.sh rg-clinic-voice-agent swedencentral
```

This will:
1. Create resource group
2. Deploy AI Foundry (main.bicep)
3. Deploy App Hosting (app-hosting.bicep)
4. Generate `.env.azure` with all endpoints

## Manual Deploy

```bash
# 1. Create resource group
az group create --name rg-clinic-voice-agent --location swedencentral

# 2. Deploy AI Foundry infrastructure
az deployment group create \
  --resource-group rg-clinic-voice-agent \
  --template-file main.bicep \
  --parameters location=swedencentral aiServices=cvagt

# 3. Deploy App Hosting (get projectEndpoint from step 2)
az deployment group create \
  --resource-group rg-clinic-voice-agent \
  --template-file app-hosting.bicep \
  --parameters location=swedencentral \
               publisherEmail=you@example.com \
               aiFoundryEndpoint=https://...
```

## Clean Up Existing Resources

Before deploying fresh, remove old resource groups:

```bash
chmod +x cleanup.sh
./cleanup.sh
```

## Deploy Container Image

After infrastructure is deployed:

```bash
# Login to ACR
az acr login --name <registry-name>

# Build and push
docker build -t <registry>.azurecr.io/clinic-voice-agent:latest ..
docker push <registry>.azurecr.io/clinic-voice-agent:latest

# Update Container App
az containerapp update \
  --name <app-name> \
  --resource-group rg-clinic-voice-agent \
  --image <registry>.azurecr.io/clinic-voice-agent:latest
```

## vs Network-Secured Setup

| Feature | Public (this) | Private |
|---------|---------------|---------|
| Setup time | ~10 min | ~30 min |
| Network isolation | ❌ | ✅ |
| Private endpoints | ❌ | ✅ |
| WAF protection | ❌ | ✅ |
| Cost | Lower | Higher |
| Compliance | Demo only | HIPAA/ADHICS ready |

For production with healthcare compliance, use `infra/private/`.
