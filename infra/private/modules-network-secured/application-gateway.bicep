/*
  Azure Application Gateway with WAF v2
  
  Provides:
  - Public ingress point with SSL termination
  - Web Application Firewall (OWASP 3.2 ruleset)
  - DDoS protection (Basic included, Standard optional)
  - Health probes and load balancing
  - Backend pools for Container Apps and APIM
*/

@description('Name of the Application Gateway')
param applicationGatewayName string

@description('Location for resources')
param location string

@description('Subnet ID for Application Gateway')
param subnetId string

@description('SKU tier for Application Gateway')
@allowed(['Standard_v2', 'WAF_v2'])
param skuTier string = 'WAF_v2'

@description('Capacity (instance count) for Application Gateway')
@minValue(1)
@maxValue(10)
param capacity int = 2

@description('Backend FQDN for Container Apps')
param containerAppFqdn string = ''

@description('Backend FQDN for API Management')
param apimGatewayFqdn string = ''

@description('Enable WAF')
param enableWaf bool = true

@description('WAF mode - Detection or Prevention')
@allowed(['Detection', 'Prevention'])
param wafMode string = 'Prevention'

@description('Tags for resources')
param tags object = {}

// Public IP for Application Gateway
resource publicIp 'Microsoft.Network/publicIPAddresses@2024-01-01' = {
  name: '${applicationGatewayName}-pip'
  location: location
  tags: tags
  sku: {
    name: 'Standard'
    tier: 'Regional'
  }
  properties: {
    publicIPAllocationMethod: 'Static'
    dnsSettings: {
      domainNameLabel: toLower(applicationGatewayName)
    }
  }
}

// WAF Policy
resource wafPolicy 'Microsoft.Network/ApplicationGatewayWebApplicationFirewallPolicies@2024-01-01' = if (enableWaf) {
  name: '${applicationGatewayName}-waf-policy'
  location: location
  tags: tags
  properties: {
    customRules: []
    policySettings: {
      requestBodyCheck: true
      maxRequestBodySizeInKb: 128
      fileUploadLimitInMb: 100
      state: 'Enabled'
      mode: wafMode
      requestBodyInspectLimitInKB: 128
      fileUploadEnforcement: true
      requestBodyEnforcement: true
    }
    managedRules: {
      managedRuleSets: [
        {
          ruleSetType: 'OWASP'
          ruleSetVersion: '3.2'
          ruleGroupOverrides: []
        }
        {
          ruleSetType: 'Microsoft_BotManagerRuleSet'
          ruleSetVersion: '1.0'
          ruleGroupOverrides: []
        }
      ]
      exclusions: []
    }
  }
}

// Application Gateway
resource applicationGateway 'Microsoft.Network/applicationGateways@2024-01-01' = {
  name: applicationGatewayName
  location: location
  tags: tags
  properties: {
    sku: {
      name: skuTier
      tier: skuTier
      capacity: capacity
    }
    gatewayIPConfigurations: [
      {
        name: 'appGatewayIpConfig'
        properties: {
          subnet: {
            id: subnetId
          }
        }
      }
    ]
    frontendIPConfigurations: [
      {
        name: 'appGatewayFrontendIP'
        properties: {
          publicIPAddress: {
            id: publicIp.id
          }
        }
      }
    ]
    frontendPorts: [
      {
        name: 'port_80'
        properties: {
          port: 80
        }
      }
      {
        name: 'port_443'
        properties: {
          port: 443
        }
      }
    ]
    backendAddressPools: [
      {
        name: 'containerAppsBackend'
        properties: {
          backendAddresses: empty(containerAppFqdn) ? [] : [
            {
              fqdn: containerAppFqdn
            }
          ]
        }
      }
      {
        name: 'apimBackend'
        properties: {
          backendAddresses: empty(apimGatewayFqdn) ? [] : [
            {
              fqdn: apimGatewayFqdn
            }
          ]
        }
      }
    ]
    backendHttpSettingsCollection: [
      {
        name: 'containerAppsHttpSettings'
        properties: {
          port: 443
          protocol: 'Https'
          cookieBasedAffinity: 'Disabled'
          pickHostNameFromBackendAddress: true
          requestTimeout: 60
          probe: {
            id: resourceId('Microsoft.Network/applicationGateways/probes', applicationGatewayName, 'containerAppsProbe')
          }
        }
      }
      {
        name: 'apimHttpSettings'
        properties: {
          port: 443
          protocol: 'Https'
          cookieBasedAffinity: 'Disabled'
          pickHostNameFromBackendAddress: true
          requestTimeout: 60
          probe: {
            id: resourceId('Microsoft.Network/applicationGateways/probes', applicationGatewayName, 'apimProbe')
          }
        }
      }
    ]
    httpListeners: [
      {
        name: 'httpListener'
        properties: {
          frontendIPConfiguration: {
            id: resourceId('Microsoft.Network/applicationGateways/frontendIPConfigurations', applicationGatewayName, 'appGatewayFrontendIP')
          }
          frontendPort: {
            id: resourceId('Microsoft.Network/applicationGateways/frontendPorts', applicationGatewayName, 'port_80')
          }
          protocol: 'Http'
        }
      }
    ]
    requestRoutingRules: [
      {
        name: 'defaultRoutingRule'
        properties: {
          ruleType: 'Basic'
          priority: 100
          httpListener: {
            id: resourceId('Microsoft.Network/applicationGateways/httpListeners', applicationGatewayName, 'httpListener')
          }
          backendAddressPool: {
            id: resourceId('Microsoft.Network/applicationGateways/backendAddressPools', applicationGatewayName, 'containerAppsBackend')
          }
          backendHttpSettings: {
            id: resourceId('Microsoft.Network/applicationGateways/backendHttpSettingsCollection', applicationGatewayName, 'containerAppsHttpSettings')
          }
        }
      }
    ]
    probes: [
      {
        name: 'containerAppsProbe'
        properties: {
          protocol: 'Https'
          path: '/health'
          interval: 30
          timeout: 30
          unhealthyThreshold: 3
          pickHostNameFromBackendHttpSettings: true
          minServers: 0
          match: {
            statusCodes: ['200-399']
          }
        }
      }
      {
        name: 'apimProbe'
        properties: {
          protocol: 'Https'
          path: '/status-0123456789abcdef'
          interval: 30
          timeout: 30
          unhealthyThreshold: 3
          pickHostNameFromBackendHttpSettings: true
          minServers: 0
          match: {
            statusCodes: ['200-399']
          }
        }
      }
    ]
    firewallPolicy: enableWaf ? {
      id: wafPolicy.id
    } : null
    enableHttp2: true
  }
}

// Outputs
output applicationGatewayId string = applicationGateway.id
output applicationGatewayName string = applicationGateway.name
output publicIpAddress string = publicIp.properties.ipAddress
output publicFqdn string = publicIp.properties.dnsSettings.fqdn
output wafPolicyId string = enableWaf ? wafPolicy.id : ''
