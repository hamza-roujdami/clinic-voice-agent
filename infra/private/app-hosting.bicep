/*
  Clinic Voice Agent - App Hosting Infrastructure
  
  Deploys:
  1. Application Insights + Log Analytics - for AI Foundry tracing
  2. Azure API Management (AI Gateway) - for traffic control and governance
  3. Azure Container Apps - for hosting Voice Gateway API
  
  This is a separate deployment from the core AI infrastructure (main.bicep).
  Deploy after the AI Foundry + Storage infrastructure is ready.

  Prerequisites (from main.bicep):
  - VNet with agent-subnet (delegated to Microsoft.App/environments)
  - AI Foundry endpoint
*/

targetScope = 'resourceGroup'

@description('Location for all resources')
param location string = resourceGroup().location

@description('Environment name (dev, staging, prod)')
@allowed(['dev', 'staging', 'prod'])
param environment string = 'dev'

@description('Base name prefix for resources')
param namePrefix string = 'cvagt'

@description('Publisher email for API Management')
param publisherEmail string

@description('Publisher name for API Management')
param publisherName string = 'Clinic Voice Agent'

@description('API Management SKU')
@allowed(['Consumption', 'Developer', 'Basicv2', 'Standardv2'])
param apimSku string = 'Basicv2'

@description('Container Apps subnet resource ID (optional, for VNet integration)')
param containerAppsSubnetId string = ''

@description('AI Foundry endpoint for APIM backend')
param aiFoundryEndpoint string = ''

@description('Log Analytics workspace retention in days')
param logRetentionDays int = 30

@description('Tags for all resources')
param tags object = {
  project: 'clinic-voice-agent'
  environment: environment
}

// Variables
var uniqueSuffix = substring(uniqueString(resourceGroup().id), 0, 4)
var apimName = '${namePrefix}-apim-${uniqueSuffix}'
var containerAppsPrefix = '${namePrefix}-ca'
var appInsightsPrefix = namePrefix

// 1. Deploy Application Insights + Log Analytics (for AI Foundry tracing)
module appInsights 'modules-network-secured/application-insights.bicep' = {
  name: 'applicationInsights'
  params: {
    namePrefix: appInsightsPrefix
    location: location
    retentionInDays: logRetentionDays
    tags: tags
  }
}

// 2. Deploy API Management
module apiManagement 'modules-network-secured/api-management.bicep' = {
  name: 'apiManagement'
  params: {
    apiManagementName: apimName
    location: location
    publisherEmail: publisherEmail
    publisherName: publisherName
    sku: apimSku
    tags: tags
  }
}

// 3. Deploy Container Apps
module containerApps 'modules-network-secured/container-apps.bicep' = {
  name: 'containerApps'
  params: {
    namePrefix: containerAppsPrefix
    location: location
    infrastructureSubnetId: containerAppsSubnetId
    logAnalyticsWorkspaceId: appInsights.outputs.logAnalyticsId
    containerImage: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest' // Placeholder - will be updated with actual image
    containerPort: 8000
    externalIngress: true
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
output apiManagementPrincipalId string = apiManagement.outputs.principalId
output containerAppUrl string = containerApps.outputs.containerAppUrl
output containerAppFqdn string = containerApps.outputs.containerAppFqdn
output containerRegistryLoginServer string = containerApps.outputs.containerRegistryLoginServer
output managedIdentityClientId string = containerApps.outputs.managedIdentityClientId

// Application Insights outputs (for AI Foundry configuration)
output appInsightsConnectionString string = appInsights.outputs.appInsightsConnectionString
output appInsightsInstrumentationKey string = appInsights.outputs.appInsightsInstrumentationKey
output appInsightsName string = appInsights.outputs.appInsightsName
output logAnalyticsWorkspaceId string = appInsights.outputs.logAnalyticsId
