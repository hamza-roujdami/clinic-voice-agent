using 'main.bicep'

param location = 'swedencentral'
param aiServices = 'cvagt'
param projectName = 'clinic-voice-agent'
param projectDescription = 'Clinic Voice Agent - Voice Scheduling Assistant'

// Model configuration
param modelName = 'gpt-4o-mini'
param modelFormat = 'OpenAI'
param modelVersion = '2024-07-18'
param modelSkuName = 'GlobalStandard'
param modelCapacity = 40
