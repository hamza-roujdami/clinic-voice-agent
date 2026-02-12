// Bicep template to deploy Grounding with Bing Search resource
// Run: az deployment group create -g rg-clinic-voice-agent -f infra/bing-custom-search.bicep
// Note: This uses Bing Grounding (Bing Search APIs are retired)

@description('Name of the Bing Grounding resource')
param bingResourceName string = 'cvagt-bing-grounding'

@description('Location for the resource (must be global for Bing)')
param location string = 'global'

// Bing Grounding Resource (replacement for retired Bing Search APIs)
resource bingGrounding 'Microsoft.Bing/accounts@2020-06-10' = {
  name: bingResourceName
  location: location
  kind: 'Bing.Grounding'
  sku: {
    name: 'G1'
  }
  properties: {}
}

output bingResourceId string = bingGrounding.id
output bingResourceName string = bingGrounding.name
