/*
  Azure Container Apps - FastAPI Hosting
  
  Hosts the Talent Reconnect FastAPI application with:
  - MAF (Microsoft Agent Framework) workflow
  - VNet integration for private access to AI services
  - Managed Identity for Azure authentication
*/

@description('Name prefix for Container Apps resources')
param namePrefix string

@description('Location for resources')
param location string

@description('VNet subnet resource ID for Container Apps environment')
param infrastructureSubnetId string = ''

@description('Log Analytics workspace resource ID')
param logAnalyticsWorkspaceId string = ''

@description('Container image to deploy (leave empty for placeholder)')
param containerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

@description('Port the container listens on')
param containerPort int = 8000

@description('Environment variables for the container')
param environmentVariables array = []

@description('Tags for resources')
param tags object = {}

@description('Enable external ingress')
param externalIngress bool = true

// Unique suffix for globally unique names
var uniqueSuffix = substring(uniqueString(resourceGroup().id), 0, 4)
var containerAppsEnvName = '${namePrefix}-env-${uniqueSuffix}'
var containerAppName = '${namePrefix}-app-${uniqueSuffix}'
var containerRegistryName = '${replace(namePrefix, '-', '')}acr${uniqueSuffix}'

// Log Analytics Workspace (if not provided)
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = if (empty(logAnalyticsWorkspaceId)) {
  name: '${namePrefix}-logs-${uniqueSuffix}'
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

var effectiveLogAnalyticsId = empty(logAnalyticsWorkspaceId) ? logAnalytics.id : logAnalyticsWorkspaceId

// Container Apps Environment
resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: containerAppsEnvName
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: reference(effectiveLogAnalyticsId, '2023-09-01').customerId
        sharedKey: listKeys(effectiveLogAnalyticsId, '2023-09-01').primarySharedKey
      }
    }
    vnetConfiguration: empty(infrastructureSubnetId) ? null : {
      infrastructureSubnetId: infrastructureSubnetId
      internal: false
    }
    workloadProfiles: [
      {
        workloadProfileType: 'Consumption'
        name: 'Consumption'
      }
    ]
    zoneRedundant: false
  }
}

// Container Registry (for custom images)
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: containerRegistryName
  location: location
  tags: tags
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
    publicNetworkAccess: 'Enabled'
  }
}

// User-Assigned Managed Identity for the Container App
resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${namePrefix}-identity-${uniqueSuffix}'
  location: location
  tags: tags
}

// Container App
resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: containerAppName
  location: location
  tags: union(tags, {
    'azd-service-name': 'api'
  })
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: externalIngress
        targetPort: containerPort
        transport: 'http'
        allowInsecure: false
        traffic: [
          {
            weight: 100
            latestRevision: true
          }
        ]
        corsPolicy: {
          allowedOrigins: ['*']
          allowCredentials: true
          allowedMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
          allowedHeaders: ['*']
        }
      }
      registries: [
        {
          server: containerRegistry.properties.loginServer
          username: containerRegistry.listCredentials().username
          passwordSecretRef: 'registry-password'
        }
      ]
      secrets: [
        {
          name: 'registry-password'
          value: containerRegistry.listCredentials().passwords[0].value
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'api'
          image: containerImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: concat([
            {
              name: 'AZURE_CLIENT_ID'
              value: managedIdentity.properties.clientId
            }
          ], environmentVariables)
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 10
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '50'
              }
            }
          }
        ]
      }
    }
  }
}

// Outputs
output environmentId string = containerAppsEnvironment.id
output environmentName string = containerAppsEnvironment.name
output containerAppId string = containerApp.id
output containerAppName string = containerApp.name
output containerAppFqdn string = containerApp.properties.configuration.ingress.fqdn
output containerAppUrl string = 'https://${containerApp.properties.configuration.ingress.fqdn}'
output containerRegistryLoginServer string = containerRegistry.properties.loginServer
output containerRegistryName string = containerRegistry.name
output managedIdentityId string = managedIdentity.id
output managedIdentityPrincipalId string = managedIdentity.properties.principalId
output managedIdentityClientId string = managedIdentity.properties.clientId
