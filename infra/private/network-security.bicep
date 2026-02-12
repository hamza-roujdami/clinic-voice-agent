/*
  Clinic Voice Agent - Network Security Enhancement
  
  Adds enterprise security layer:
  1. Application Gateway with WAF v2 - Public ingress with DDoS/WAF protection
  2. APIM VNet Integration - Move APIM into private subnet
  3. NSG rules for proper traffic flow
  
  Prerequisites:
  - Existing VNet with subnets: appgw-subnet, apim-subnet
  - Existing APIM instance
  - Existing Container Apps
*/

targetScope = 'resourceGroup'

@description('Location for all resources')
param location string = resourceGroup().location

@description('Base name prefix for resources')
param namePrefix string = 'cvagt'

@description('Existing VNet name')
param vnetName string = 'clinic-voice-agent-vnet'

@description('Application Gateway subnet name')
param appGwSubnetName string = 'appgw-subnet'

@description('APIM subnet name')
param apimSubnetName string = 'apim-subnet'

@description('Existing Container App FQDN (for backend pool)')
param containerAppFqdn string = ''

@description('Existing APIM Gateway FQDN (for backend pool)')
param apimGatewayFqdn string = ''

@description('Enable WAF on Application Gateway')
param enableWaf bool = true

@description('WAF mode')
@allowed(['Detection', 'Prevention'])
param wafMode string = 'Prevention'

@description('Application Gateway capacity (instances)')
@minValue(1)
@maxValue(10)
param appGwCapacity int = 2

@description('Tags for all resources')
param tags object = {
  project: 'clinic-voice-agent'
  component: 'network-security'
}

// Variables
var uniqueSuffix = substring(uniqueString(resourceGroup().id), 0, 4)
var appGwName = '${namePrefix}-appgw-${uniqueSuffix}'

// Reference existing VNet
resource vnet 'Microsoft.Network/virtualNetworks@2024-01-01' existing = {
  name: vnetName
}

// Reference subnets
resource appGwSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-01-01' existing = {
  parent: vnet
  name: appGwSubnetName
}

resource apimSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-01-01' existing = {
  parent: vnet
  name: apimSubnetName
}

// NSG for Application Gateway subnet
resource appGwNsg 'Microsoft.Network/networkSecurityGroups@2024-01-01' = {
  name: '${appGwName}-nsg'
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'AllowGatewayManager'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourceAddressPrefix: 'GatewayManager'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '65200-65535'
          description: 'Allow Azure Gateway Manager'
        }
      }
      {
        name: 'AllowHttps'
        properties: {
          priority: 110
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourceAddressPrefix: 'Internet'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '443'
          description: 'Allow HTTPS from Internet'
        }
      }
      {
        name: 'AllowHttp'
        properties: {
          priority: 120
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourceAddressPrefix: 'Internet'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '80'
          description: 'Allow HTTP from Internet (for redirect)'
        }
      }
      {
        name: 'AllowAzureLoadBalancer'
        properties: {
          priority: 130
          direction: 'Inbound'
          access: 'Allow'
          protocol: '*'
          sourceAddressPrefix: 'AzureLoadBalancer'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '*'
          description: 'Allow Azure Load Balancer probes'
        }
      }
    ]
  }
}

// NSG for APIM subnet
resource apimNsg 'Microsoft.Network/networkSecurityGroups@2024-01-01' = {
  name: '${namePrefix}-apim-nsg-${uniqueSuffix}'
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'AllowAPIMManagement'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourceAddressPrefix: 'ApiManagement'
          sourcePortRange: '*'
          destinationAddressPrefix: 'VirtualNetwork'
          destinationPortRange: '3443'
          description: 'Management endpoint for Azure portal and PowerShell'
        }
      }
      {
        name: 'AllowAzureLoadBalancer'
        properties: {
          priority: 110
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourceAddressPrefix: 'AzureLoadBalancer'
          sourcePortRange: '*'
          destinationAddressPrefix: 'VirtualNetwork'
          destinationPortRange: '6390'
          description: 'Azure Infrastructure Load Balancer'
        }
      }
      {
        name: 'AllowAppGateway'
        properties: {
          priority: 120
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourceAddressPrefix: appGwSubnet.properties.addressPrefix
          sourcePortRange: '*'
          destinationAddressPrefix: 'VirtualNetwork'
          destinationPortRanges: ['80', '443']
          description: 'Allow traffic from Application Gateway'
        }
      }
      {
        name: 'AllowVNetInbound'
        properties: {
          priority: 130
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourceAddressPrefix: 'VirtualNetwork'
          sourcePortRange: '*'
          destinationAddressPrefix: 'VirtualNetwork'
          destinationPortRanges: ['80', '443']
          description: 'Allow VNet internal traffic'
        }
      }
      {
        name: 'AllowStorageOutbound'
        properties: {
          priority: 100
          direction: 'Outbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourceAddressPrefix: 'VirtualNetwork'
          sourcePortRange: '*'
          destinationAddressPrefix: 'Storage'
          destinationPortRange: '443'
          description: 'Dependency on Azure Storage'
        }
      }
      {
        name: 'AllowSqlOutbound'
        properties: {
          priority: 110
          direction: 'Outbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourceAddressPrefix: 'VirtualNetwork'
          sourcePortRange: '*'
          destinationAddressPrefix: 'Sql'
          destinationPortRange: '1433'
          description: 'Dependency on Azure SQL'
        }
      }
      {
        name: 'AllowKeyVaultOutbound'
        properties: {
          priority: 120
          direction: 'Outbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourceAddressPrefix: 'VirtualNetwork'
          sourcePortRange: '*'
          destinationAddressPrefix: 'AzureKeyVault'
          destinationPortRange: '443'
          description: 'Dependency on Azure Key Vault'
        }
      }
    ]
  }
}

// Deploy Application Gateway with WAF
module applicationGateway 'modules-network-secured/application-gateway.bicep' = {
  name: 'applicationGateway'
  params: {
    applicationGatewayName: appGwName
    location: location
    subnetId: appGwSubnet.id
    skuTier: enableWaf ? 'WAF_v2' : 'Standard_v2'
    capacity: appGwCapacity
    containerAppFqdn: containerAppFqdn
    apimGatewayFqdn: apimGatewayFqdn
    enableWaf: enableWaf
    wafMode: wafMode
    tags: tags
  }
}

// Outputs
output applicationGatewayId string = applicationGateway.outputs.applicationGatewayId
output applicationGatewayPublicIp string = applicationGateway.outputs.publicIpAddress
output applicationGatewayFqdn string = applicationGateway.outputs.publicFqdn
output appGwNsgId string = appGwNsg.id
output apimNsgId string = apimNsg.id
output apimSubnetId string = apimSubnet.id
