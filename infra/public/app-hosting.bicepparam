using 'app-hosting.bicep'

param location = 'swedencentral'
param namePrefix = 'cvagt'
param publisherEmail = 'admin@clinic-voice-agent.ai'
param publisherName = 'Clinic Voice Agent'
param apimSku = 'Consumption'
param aiFoundryEndpoint = '' // Fill from main.bicep output
