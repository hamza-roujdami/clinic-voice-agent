using './main.bicep'

// Clinic Voice Agent - Standard Agent Setup (Sweden Central)
// Full network isolation with private endpoints

param location = 'swedencentral'
param aiServices = 'cvagt'
param modelName = 'gpt-4o-mini'
param modelFormat = 'OpenAI'
param modelVersion = '2024-07-18'
param modelSkuName = 'GlobalStandard'
param modelCapacity = 40

// Embedding model for vector search
param deployEmbeddingModel = true
param embeddingModelName = 'text-embedding-3-small'
param embeddingModelVersion = '1'
param embeddingModelSkuName = 'Standard'
param embeddingModelCapacity = 120

param firstProjectName = 'cvproj'
param projectDescription = 'Clinic Voice Agent - Voice Scheduling Assistant with MAF'
param displayName = 'Clinic Voice Agent'
param peSubnetName = 'pe-subnet'

// Resource IDs for existing resources
// Leave empty to create new resources
param existingVnetResourceId = ''
param vnetName = 'clinic-voice-agent-vnet'
param agentSubnetName = 'agent-subnet'
param aiSearchResourceId = ''
param azureStorageAccountResourceId = ''
param azureCosmosDBAccountResourceId = ''

// API Management configuration (optional)
param apiManagementResourceId = ''

// Pass the DNS zone map here
// Leave empty to create new DNS zone, add the resource group of existing DNS zone to use it
param existingDnsZones = {
  'privatelink.services.ai.azure.com': ''
  'privatelink.openai.azure.com': ''
  'privatelink.cognitiveservices.azure.com': ''               
  'privatelink.search.windows.net': ''           
  'privatelink.blob.core.windows.net': ''                            
  'privatelink.documents.azure.com': ''
  'privatelink.azure-api.net': ''                       
}

//DNSZones names for validating if they exist
param dnsZoneNames = [
  'privatelink.services.ai.azure.com'
  'privatelink.openai.azure.com'
  'privatelink.cognitiveservices.azure.com'
  'privatelink.search.windows.net'
  'privatelink.blob.core.windows.net'
  'privatelink.documents.azure.com'
  'privatelink.azure-api.net'
]


// Network configuration: only used when existingVnetResourceId is not provided
// These addresses are only used when creating a new VNet and subnets
// If you provide existingVnetResourceId, these values will be ignored
param vnetAddressPrefix = ''
param agentSubnetPrefix = ''
param peSubnetPrefix = ''
