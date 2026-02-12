# Infrastructure

Azure infrastructure templates for Clinic Voice Agent. 

## Choose Your Deployment Mode

| Mode | Folder | Use Case |
|------|--------|----------|
| **Public** | `infra/public/` | Demo, development, quick start |
| **Private** | `infra/private/` | Enterprise, production, compliance |

---

## 🌐 Public Infrastructure (Recommended for Demos)

All resources have **public endpoints** - no VNet, no private endpoints, no firewall complexity.

```bash
cd infra/public
./deploy.sh rg-clinic-voice-agent swedencentral
```

**Deployed Resources:**
- Azure AI Foundry (AI Services + Project)
- Azure AI Search (semantic search for policies/FAQs)
- Cosmos DB (session storage)
- Storage Account (Foundry data)
- Container Apps (Voice Gateway API hosting)
- API Management (Consumption tier)
- Application Insights

**When to use:**
- ✅ Demos and POCs
- ✅ Development environments
- ✅ Quick start / learning
- ✅ Cost-conscious deployments

See [public/README.md](public/README.md) for details.

---

## 🔒 Private Infrastructure (Enterprise)

Full **network isolation** with VNet, private endpoints, and App Gateway with WAF.

```bash
cd infra/private

# 1. Deploy core AI resources
az deployment group create \
  --resource-group rg-clinic-voice-agent \
  --template-file main.bicep \
  --parameters main.bicepparam

# 2. Deploy network security layer
az deployment group create \
  --resource-group rg-clinic-voice-agent \
  --template-file network-security.bicep \
  --parameters network-security.bicepparam

# 3. Deploy app hosting
az deployment group create \
  --resource-group rg-clinic-voice-agent \
  --template-file app-hosting.bicep \
  --parameters app-hosting.bicepparam
```

**Deployed Resources:**
- Everything in Public, PLUS:
- Virtual Network with subnets
- Private Endpoints for all services
- App Gateway with WAF v2
- Private DNS Zones
- Network Security Groups

**When to use:**
- ✅ Production workloads
- ✅ Compliance requirements (HIPAA, ADHICS, etc.)
- ✅ Enterprise security policies
- ✅ Data residency requirements (UAE North for production)

See [private/README.md](private/README.md) for details.

---

## Comparison

| Feature | Public | Private |
|---------|--------|---------|
| Deployment time | ~10 min | ~30 min |
| Monthly cost | ~$50-100 | ~$200-500 |
| Network isolation | ❌ | ✅ |
| Private endpoints | ❌ | ✅ |
| WAF protection | ❌ | ✅ |
| VNet integration | ❌ | ✅ |
| Complexity | Low | High |

---

## Architecture Context

This infrastructure supports the **Clinic Voice Scheduling Assistant**:

```
Telephony (PSTN) → Voice Gateway API → Azure Speech STT/TTS → MAF Orchestrator → Tools
```

**Multi-Agent Design (MAF):**
- Triage Agent: entry point, intent routing, tool execution
- Identity/OTP Agent: patient lookup, OTP verification
- Scheduling Agent: book/reschedule/cancel, doctor search
- RAG/Policy Agent: FAQs with citations (planned)
- Handoff Agent: warm transfer to human agent (planned)

---

## Post-Deployment

After infrastructure is deployed:

1. **Configure `.env`** with endpoints from deployment output
2. **Create search indexes** for policies/FAQs
3. **Deploy container image** to Container Apps
4. **Configure telephony platform** with Voice Gateway endpoint
