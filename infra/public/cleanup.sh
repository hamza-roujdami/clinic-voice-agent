#!/bin/bash
# Cleanup script - Delete all Clinic Voice Agent resource groups
# Run with: bash cleanup.sh

set -e

echo "⚠️  This will DELETE the following resource groups:"
echo ""

RESOURCE_GROUPS=(
    "rg-clinic-voice-agent"
    "rg-clinic-voice-agent-dev"
    "rg-clinic-voice-agent-prod"
    "rg-clinic-voice-agent-swedencentral"
    "rg-clinic-voice-agent-uaenorth"
)

for rg in "${RESOURCE_GROUPS[@]}"; do
    if az group exists --name "$rg" 2>/dev/null | grep -q true; then
        echo "  ✗ $rg (exists)"
    else
        echo "  - $rg (not found)"
    fi
done

echo ""
read -p "Type 'DELETE' to confirm: " confirm

if [ "$confirm" != "DELETE" ]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "🗑️  Deleting resource groups..."

for rg in "${RESOURCE_GROUPS[@]}"; do
    if az group exists --name "$rg" 2>/dev/null | grep -q true; then
        echo "  Deleting $rg..."
        az group delete --name "$rg" --yes --no-wait
    fi
done

echo ""
echo "✓ Deletion initiated (async). Check Azure Portal for status."
echo "  Resources may take 5-15 minutes to fully delete."
