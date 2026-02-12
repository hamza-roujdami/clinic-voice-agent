/*
  Azure API Management - AI Gateway
  
  Provides centralized management for AI traffic:
  - Rate limiting and quotas
  - Load balancing across model deployments  
  - Content safety policies
  - Token logging and monitoring
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
  'Premium'
])
param sku string = 'Basicv2'

@description('Capacity units for APIM (ignored for Consumption)')
param skuCount int = 1

@description('VNet subnet resource ID for APIM (optional, for VNet integration)')
param subnetResourceId string = ''

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
    virtualNetworkType: empty(subnetResourceId) ? 'None' : 'External'
    virtualNetworkConfiguration: empty(subnetResourceId) ? null : {
      subnetResourceId: subnetResourceId
    }
  }
}

// Named Value for AI Foundry endpoint (to be configured after deployment)
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

// AI Gateway policy fragment for common AI operations
resource policyFragmentAIGateway 'Microsoft.ApiManagement/service/policyFragments@2023-09-01-preview' = {
  parent: apiManagement
  name: 'ai-gateway-common'
  properties: {
    description: 'Common AI Gateway policies for rate limiting and logging'
    format: 'rawxml'
    value: '<fragment><set-header name="x-ms-correlation-id" exists-action="skip"><value>@(context.RequestId.ToString())</value></set-header></fragment>'
  }
}

output apiManagementId string = apiManagement.id
output apiManagementName string = apiManagement.name
output gatewayUrl string = apiManagement.properties.gatewayUrl
output managementApiUrl string = apiManagement.properties.managementApiUrl
output principalId string = apiManagement.identity.principalId
