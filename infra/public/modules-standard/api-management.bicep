/*
  Azure API Management - AI Gateway (Public)
  
  Provides centralized management for AI traffic:
  - Rate limiting and quotas
  - Load balancing across model deployments  
  - Content safety policies
*/

@description('Name of the API Management instance')
param apiManagementName string

@description('Location for the API Management instance')
param location string

@description('Publisher email for APIM')
param publisherEmail string

@description('Publisher name for APIM')
param publisherName string

@description('SKU for API Management')
@allowed([
  'Consumption'
  'Developer'
  'Basic'
  'Basicv2'
  'Standard'
  'Standardv2'
])
param sku string = 'Consumption'

@description('Capacity units for APIM (ignored for Consumption)')
param skuCount int = 1

@description('Tags for the resource')
param tags object = {}

// API Management Service
resource apiManagement 'Microsoft.ApiManagement/service@2023-09-01-preview' = {
  name: apiManagementName
  location: location
  tags: tags
  sku: {
    name: sku
    capacity: sku == 'Consumption' ? 0 : skuCount
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    publisherEmail: publisherEmail
    publisherName: publisherName
    virtualNetworkType: 'None'
  }
}

// Named Value for AI Foundry endpoint
resource namedValueAIEndpoint 'Microsoft.ApiManagement/service/namedValues@2023-09-01-preview' = {
  parent: apiManagement
  name: 'ai-foundry-endpoint'
  properties: {
    displayName: 'ai-foundry-endpoint'
    value: 'https://placeholder.cognitiveservices.azure.com'
    secret: false
    tags: ['ai', 'foundry']
  }
}

output apiManagementName string = apiManagement.name
output apiManagementId string = apiManagement.id
output gatewayUrl string = apiManagement.properties.gatewayUrl
output principalId string = apiManagement.identity.principalId
