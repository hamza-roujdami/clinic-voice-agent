/*
  Network Security Parameters - Sweden Central
  
  Deploy with:
  az deployment group create \
    --resource-group rg-clinic-voice-agent \
    --template-file network-security.bicep \
    --parameters network-security.bicepparam
*/
using 'network-security.bicep'

param location = 'swedencentral'
param namePrefix = 'cvagt'
param vnetName = 'clinic-voice-agent-vnet'
param appGwSubnetName = 'appgw-subnet'
param apimSubnetName = 'apim-subnet'

// Container App FQDN from existing deployment
param containerAppFqdn = '' // Fill after app-hosting.bicep deployment

// APIM Gateway FQDN
param apimGatewayFqdn = '' // Fill after app-hosting.bicep deployment

// WAF Configuration
param enableWaf = true
param wafMode = 'Prevention'
param appGwCapacity = 2

param tags = {
  project: 'clinic-voice-agent'
  environment: 'production'
  component: 'network-security'
}
