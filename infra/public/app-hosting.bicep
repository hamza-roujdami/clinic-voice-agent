/*
  Clinic Voice Agent - App Hosting Infrastructure (Public)
  
  Deploys:
  1. Application Insights + Log Analytics - for tracing
  2. Azure API Management (AI Gateway) - for traffic control
  3. Azure Container Apps - for hosting Voice Gateway API
  
  Deploy AFTER main.bicep (AI Foundry infrastructure).
*/

targetScope = 'resourceGroup'

@description('Location for all resources')
param location string = resourceGroup().location

@description('Base name prefix for resources')
param namePrefix string = 'cvagt'

@description('Publisher email for API Management')
param publisherEmail string

@description('Publisher name for API Management')
param publisherName string = 'Clinic Voice Agent'

@description('API Management SKU (Consumption is cheapest)')
@allowed(['Consumption', 'Developer', 'Basicv2', 'Standardv2'])
param apimSku string = 'Consumption'

@description('AI Foundry project endpoint (from main.bicep output)')
param aiFoundryEndpoint string = ''

@description('Tags for all resources')
param tags object = {
  project: 'clinic-voice-agent'
  environment: 'demo'
}

// Variables
var uniqueSuffix = substring(uniqueString(resourceGroup().id), 0, 4)
var apimName = '${namePrefix}-apim-${uniqueSuffix}'

// 1. Application Insights + Log Analytics
module appInsights 'modules-standard/application-insights.bicep' = {
  name: 'applicationInsights-deployment'
  params: {
    namePrefix: namePrefix
    location: location
    retentionInDays: 30
    tags: tags
  }
}

// 2. API Management
module apiManagement 'modules-standard/api-management.bicep' = {
  name: 'apiManagement-deployment'
  params: {
    apiManagementName: apimName
    location: location
    publisherEmail: publisherEmail
    publisherName: publisherName
    sku: apimSku
    tags: tags
  }
}

// 3. Container Apps
module containerApps 'modules-standard/container-apps.bicep' = {
  name: 'containerApps-deployment'
  params: {
    namePrefix: '${namePrefix}-ca'
    location: location
    logAnalyticsWorkspaceId: appInsights.outputs.logAnalyticsId
    containerImage: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
    containerPort: 8000
    tags: tags
    environmentVariables: [
      {
        name: 'PROJECT_ENDPOINT'
        value: aiFoundryEndpoint
      }
      {
        name: 'APIM_GATEWAY_URL'
        value: apiManagement.outputs.gatewayUrl
      }
      {
        name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
        value: appInsights.outputs.appInsightsConnectionString
      }
    ]
  }
}

// Outputs
output apiManagementGatewayUrl string = apiManagement.outputs.gatewayUrl
output apiManagementName string = apiManagement.outputs.apiManagementName
output containerAppUrl string = containerApps.outputs.containerAppUrl
output containerAppFqdn string = containerApps.outputs.containerAppFqdn
output containerRegistryLoginServer string = containerApps.outputs.containerRegistryLoginServer
output managedIdentityClientId string = containerApps.outputs.managedIdentityClientId
output appInsightsConnectionString string = appInsights.outputs.appInsightsConnectionString
output logAnalyticsWorkspaceId string = appInsights.outputs.logAnalyticsId
