#!/bin/bash
# Delete Capability Host for Clinic Voice Agent
# Run this before deleting the resource group if you encounter deletion issues

set -e

RG_NAME="${1:-rg-clinic-voice-agent}"
ACCOUNT_NAME="${2:-}"

if [ -z "$ACCOUNT_NAME" ]; then
    echo "Usage: ./deleteCapHost.sh <resource-group> <ai-services-account-name>"
    echo "Example: ./deleteCapHost.sh rg-clinic-voice-agent cvagt1234"
    exit 1
fi

echo "🗑️  Deleting Capability Hosts for $ACCOUNT_NAME in $RG_NAME..."

# Delete project capability host
echo "  Deleting project capability host..."
az rest --method DELETE \
  --url "https://management.azure.com/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RG_NAME}/providers/Microsoft.CognitiveServices/accounts/${ACCOUNT_NAME}/projects/*/capabilityHosts/caphostproj?api-version=2025-04-01-preview" \
  2>/dev/null || echo "  (project cap host may not exist)"

# Delete account capability host
echo "  Deleting account capability host..."
az rest --method DELETE \
  --url "https://management.azure.com/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RG_NAME}/providers/Microsoft.CognitiveServices/accounts/${ACCOUNT_NAME}/capabilityHosts/caphostacc?api-version=2025-04-01-preview" \
  2>/dev/null || echo "  (account cap host may not exist)"

echo "✓ Capability hosts deletion initiated"
echo "  Wait 2-3 minutes before deleting the resource group"
