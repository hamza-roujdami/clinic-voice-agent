// Standard agent setup with PUBLIC networking (no VNet/private endpoints)
// Based on: https://github.com/microsoft-foundry/foundry-samples/tree/main/infrastructure/infrastructure-setup-bicep/41-standard-agent-setup

@allowed([
  'australiaeast'
  'canadaeast'
  'eastus'
  'eastus2'
  'francecentral'
  'japaneast'
  'koreacentral'
  'norwayeast'
  'polandcentral'
  'southindia'
  'swedencentral'
  'switzerlandnorth'
  'uaenorth'
  'uksouth'
  'westus'
  'westus2'
  'westus3'
  'westeurope'
  'southeastasia'
  'brazilsouth'
  'germanywestcentral'
  'italynorth'
  'southafricanorth'
  'southcentralus'
])
@description('The Azure region where resources will be created.')
param location string = 'swedencentral'

@maxLength(9)
@description('Base name for AI Services resource.')
param aiServices string = 'cvagt'

@description('Name for the project resource.')
param projectName string = 'clinic-voice-agent'

@description('Project description.')
param projectDescription string = 'Clinic Voice Agent - NICE Voice Scheduling Assistant'

// Model deployment parameters
@description('The name of the model to deploy')
param modelName string = 'gpt-4o-mini'

@description('The model provider')
param modelFormat string = 'OpenAI'

@description('The model version')
param modelVersion string = '2024-07-18'

@description('The SKU for model deployment')
param modelSkuName string = 'GlobalStandard'

@description('Tokens per minute capacity')
param modelCapacity int = 40

// Create a short, unique suffix
param deploymentTimestamp string = utcNow('yyyyMMddHHmmss')
var uniqueSuffix = substring(uniqueString('${resourceGroup().id}-${deploymentTimestamp}'), 0, 4)
var accountName = toLower('${aiServices}${uniqueSuffix}')
var projectResourceName = toLower('${projectName}${uniqueSuffix}')

var cosmosDBName = toLower('${uniqueSuffix}cosmosdb')
var aiSearchName = toLower('${uniqueSuffix}search')
var azureStorageName = toLower('${uniqueSuffix}storage')

// =============================================================================
// Dependent Resources (Cosmos DB, AI Search, Storage) - PUBLIC ACCESS
// =============================================================================

module aiDependencies 'modules-standard/standard-dependent-resources.bicep' = {
  name: 'dependencies-${accountName}-deployment'
  params: {
    location: location
    azureStorageName: azureStorageName
    aiSearchName: aiSearchName
    cosmosDBName: cosmosDBName
    // No existing resources - create all new
    aiSearchResourceId: ''
    aiSearchExists: false
    azureStorageAccountResourceId: ''
    azureStorageExists: false
    cosmosDBResourceId: ''
    cosmosDBExists: false
  }
}

// =============================================================================
// AI Services Account with Model Deployment
// =============================================================================

module aiAccount 'modules-standard/ai-account-identity.bicep' = {
  name: 'ai-${accountName}-deployment'
  params: {
    accountName: accountName
    location: location
    modelName: modelName
    modelFormat: modelFormat
    modelVersion: modelVersion
    modelSkuName: modelSkuName
    modelCapacity: modelCapacity
  }
  dependsOn: [aiDependencies]
}

// =============================================================================
// AI Project (sub-resource of AI Services account)
// =============================================================================

module aiProject 'modules-standard/ai-project-identity.bicep' = {
  name: 'ai-${projectResourceName}-deployment'
  params: {
    projectName: projectResourceName
    projectDescription: projectDescription
    displayName: projectName
    location: location
    accountName: aiAccount.outputs.accountName
    
    aiSearchName: aiDependencies.outputs.aiSearchName
    aiSearchServiceResourceGroupName: resourceGroup().name
    aiSearchServiceSubscriptionId: subscription().subscriptionId
    
    cosmosDBName: aiDependencies.outputs.cosmosDBName
    cosmosDBResourceGroupName: resourceGroup().name
    cosmosDBSubscriptionId: subscription().subscriptionId
    
    azureStorageName: aiDependencies.outputs.azureStorageName
    azureStorageResourceGroupName: resourceGroup().name
    azureStorageSubscriptionId: subscription().subscriptionId
  }
}

module formatProjectWorkspaceId 'modules-standard/format-project-workspace-id.bicep' = {
  name: 'format-project-workspace-id-deployment'
  params: {
    projectWorkspaceId: aiProject.outputs.projectWorkspaceId
  }
}

// =============================================================================
// Role Assignments
// =============================================================================

module storageAccountRoleAssignment 'modules-standard/azure-storage-account-role-assignment.bicep' = {
  name: 'storage-ra-deployment'
  params: {
    azureStorageName: aiDependencies.outputs.azureStorageName
    projectPrincipalId: aiProject.outputs.projectPrincipalId
  }
}

module cosmosAccountRoleAssignment 'modules-standard/cosmosdb-account-role-assignment.bicep' = {
  name: 'cosmos-account-ra-deployment'
  params: {
    cosmosDBName: aiDependencies.outputs.cosmosDBName
    projectPrincipalId: aiProject.outputs.projectPrincipalId
  }
  dependsOn: [storageAccountRoleAssignment]
}

module aiSearchRoleAssignment 'modules-standard/ai-search-role-assignments.bicep' = {
  name: 'ai-search-ra-deployment'
  params: {
    aiSearchName: aiDependencies.outputs.aiSearchName
    projectPrincipalId: aiProject.outputs.projectPrincipalId
  }
  dependsOn: [cosmosAccountRoleAssignment]
}

// =============================================================================
// Capability Host (enables agent features)
// =============================================================================

module addProjectCapabilityHost 'modules-standard/add-project-capability-host.bicep' = {
  name: 'capabilityHost-deployment'
  params: {
    accountName: aiAccount.outputs.accountName
    projectName: aiProject.outputs.projectName
    cosmosDBConnection: aiProject.outputs.cosmosDBConnection
    azureStorageConnection: aiProject.outputs.azureStorageConnection
    aiSearchConnection: aiProject.outputs.aiSearchConnection
    projectCapHost: 'caphostproj'
    accountCapHost: 'caphostacc'
  }
  dependsOn: [aiSearchRoleAssignment]
}

// Storage container role assignments
module storageContainersRoleAssignment 'modules-standard/blob-storage-container-role-assignments.bicep' = {
  name: 'storage-containers-ra-deployment'
  params: {
    aiProjectPrincipalId: aiProject.outputs.projectPrincipalId
    storageName: aiDependencies.outputs.azureStorageName
    workspaceId: formatProjectWorkspaceId.outputs.projectWorkspaceIdGuid
  }
  dependsOn: [addProjectCapabilityHost]
}

// Cosmos container role assignments
module cosmosContainerRoleAssignment 'modules-standard/cosmos-container-role-assignments.bicep' = {
  name: 'cosmos-container-ra-deployment'
  params: {
    cosmosAccountName: aiDependencies.outputs.cosmosDBName
    projectWorkspaceId: formatProjectWorkspaceId.outputs.projectWorkspaceIdGuid
    projectPrincipalId: aiProject.outputs.projectPrincipalId
  }
  dependsOn: [addProjectCapabilityHost]
}

// =============================================================================
// Outputs
// =============================================================================

output projectEndpoint string = 'https://${accountName}.services.ai.azure.com/api/projects/${projectResourceName}'
output aiSearchEndpoint string = 'https://${aiSearchName}.search.windows.net'
output cosmosEndpoint string = 'https://${cosmosDBName}.documents.azure.com:443/'
output storageAccountName string = azureStorageName
