using './app-hosting.bicep'

// Clinic Voice Agent - App Hosting Parameters (Sweden Central)
// Deploys APIM (AI Gateway) + Container Apps

param location = 'swedencentral'
param environment = 'prod'
param namePrefix = 'cvagt'

// API Management configuration
param publisherEmail = 'admin@clinic-voice-agent.ai'
param publisherName = 'Clinic Voice Agent'
param apimSku = 'Basicv2'  // Basicv2 for production, Developer for dev/test

// VNet integration - Use the dedicated app-subnet (NOT agent-subnet!)
// The agent-subnet is exclusively for AI Foundry's internal Container Apps
// Our Voice Gateway API needs its own subnet delegated to Microsoft.App/environments
param containerAppsSubnetId = '' // Fill with: /subscriptions/.../subnets/app-subnet

// AI Foundry endpoint (from main.bicep deployment)
// Get with: az cognitiveservices account show -g rg-clinic-voice-agent -n cvagt... --query properties.endpoint -o tsv
param aiFoundryEndpoint = '' // Fill after main.bicep deployment

param tags = {
  project: 'clinic-voice-agent'
  environment: 'prod'
  component: 'app-hosting'
}
