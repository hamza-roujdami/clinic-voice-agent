# Clinic Voice Agent - Infrastructure (Private/Enterprise)

Production-grade Azure AI Foundry infrastructure with **enterprise networking** for the Clinic Voice Scheduling Assistant.

## 🏗️ Architecture

```
                                    Internet
                                       │
                                       ▼
                        ┌──────────────────────────────┐
                        │   Application Gateway + WAF  │
                        │   (cvagt-appgw)              │
                        │   WAF v2: OWASP 3.2 + Bot    │
                        └──────────────┬───────────────┘
                                       │
┌──────────────────────────────────────┼──────────────────────────────────────┐
│                    Virtual Network (192.168.0.0/16)                          │
│                                      │                                       │
│  ┌───────────────────────────────────┼───────────────────────────────────┐  │
│  │  appgw-subnet (192.168.5.0/24)    │                                   │  │
│  └───────────────────────────────────┼───────────────────────────────────┘  │
│                                      │                                       │
│                         ┌────────────┴────────────┐                         │
│                         ▼                         ▼                         │
│  ┌──────────────────────────────┐  ┌──────────────────────────────────┐    │
│  │   API Management (BasicV2)   │  │    Container Apps Env            │    │
│  │   cvagt-apim                 │  │    cvagt-ca-env                  │    │
│  │   AI Gateway Policies        │◄─┤    (Voice Gateway API)           │    │
│  │   apim-subnet (192.168.4.0/27)  │    app-subnet (192.168.2.0/23)  │    │
│  └──────────────────────────────┘  └──────────────────────────────────┘    │
│                                      │                                       │
│  ┌───────────────────────────────────┼───────────────────────────────────┐  │
│  │      Agent Subnet (192.168.0.0/24) - EXCLUSIVE for AI Foundry         │  │
│  │  ┌────────────────────────────────────────────────────────────────┐   │  │
│  │  │   Capability Host (caphostproj) - Agent Runtime                │   │  │
│  │  │   Delegated to: Microsoft.App/environments                     │   │  │
│  │  └────────────────────────────────────────────────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                      │                                       │
│  ┌───────────────────────────────────┼───────────────────────────────────┐  │
│  │      Private Endpoint Subnet (192.168.1.0/24)                         │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐                  │  │
│  │  │AI Foundry│ │ Cosmos DB│ │AI Search │ │ Storage  │                  │  │
│  │  │  (PE)    │ │   (PE)   │ │   (PE)   │ │   (PE)   │                  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘                  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
          ┌────────────────────────────┼────────────────────────────────┐
          ▼                            ▼                                ▼
   ┌─────────────┐            ┌─────────────┐                  ┌─────────────┐
   │  Cosmos DB  │            │  AI Search  │                  │   Storage   │
   │  (Sessions) │            │(Policies/FAQ│                  │   (Files)   │
   │  Serverless │            │  + RAG)     │                  │ Standard_ZRS│
   └─────────────┘            └─────────────┘                  └─────────────┘
```

## 📦 Resources Deployed

### Core AI Infrastructure (main.bicep)

| Resource | Purpose | SKU |
|----------|---------|-----|
| **AI Foundry Account** | AI services hub with model deployments | S0 |
| **AI Foundry Project** | Workspace for agents | - |
| **Capability Host** | Agent runtime (Standard Setup) | Agents |
| **Azure Cosmos DB** | Session/conversation persistence | Serverless |
| **Azure AI Search** | Vector store (policies, FAQs, RAG) | Standard |
| **Azure Storage** | File storage for agent artifacts | Standard_ZRS |

### Application Hosting (app-hosting.bicep)

| Resource | Purpose | SKU |
|----------|---------|-----|
| **API Management** | AI Gateway with policies | BasicV2 |
| **Container Apps Env** | Voice Gateway API hosting | Consumption |
| **Container Registry** | Docker image storage | Basic |
| **Application Insights** | Tracing & telemetry | - |
| **Log Analytics** | Centralized logging | PerGB2018 |

### Networking & Security (network-security.bicep)

| Resource | Purpose |
|----------|---------|
| **Virtual Network** | Network isolation (192.168.0.0/16) |
| **Application Gateway** | Public ingress + WAF |
| **WAF Policy** | OWASP 3.2 + Bot protection |
| **Private Endpoints** | Secure connectivity (4 endpoints) |
| **Private DNS Zones** | Name resolution (7 zones) |
| **NSGs** | Network security |

### Subnet Layout

| Subnet | CIDR | Purpose | Delegation |
|--------|------|---------|------------|
| `agent-subnet` | 192.168.0.0/24 | AI Foundry Agents (EXCLUSIVE) | Microsoft.App/environments |
| `pe-subnet` | 192.168.1.0/24 | Private Endpoints | - |
| `app-subnet` | 192.168.2.0/23 | Container Apps | Microsoft.App/environments |
| `apim-subnet` | 192.168.4.0/27 | API Management | - |
| `appgw-subnet` | 192.168.5.0/24 | Application Gateway | - |

## 🚀 Deployment

### Step 1: Deploy Core AI Infrastructure

```bash
az deployment group create \
  --resource-group rg-clinic-voice-agent \
  --template-file main.bicep \
  --parameters main.bicepparam
```

### Step 2: Deploy Network Security Layer

```bash
az deployment group create \
  --resource-group rg-clinic-voice-agent \
  --template-file network-security.bicep \
  --parameters network-security.bicepparam
```

### Step 3: Deploy App Hosting

```bash
az deployment group create \
  --resource-group rg-clinic-voice-agent \
  --template-file app-hosting.bicep \
  --parameters app-hosting.bicepparam
```

## 🔐 Security Features

- **Private Endpoints**: All Azure services accessed via private endpoints
- **WAF v2**: OWASP 3.2 Core Rule Set + Bot Protection
- **Network Isolation**: Full VNet integration
- **No Public Access**: Cosmos DB, Storage, AI Search all private
- **Healthcare Compliance**: ADHICS/HIPAA-ready architecture

## vs Public Setup

| Feature | Public | Private (this) |
|---------|--------|----------------|
| Setup time | ~10 min | ~30 min |
| Network isolation | ❌ | ✅ |
| Private endpoints | ❌ | ✅ |
| WAF protection | ❌ | ✅ |
| Cost | Lower | Higher |
| Compliance | Demo only | HIPAA/ADHICS ready |
