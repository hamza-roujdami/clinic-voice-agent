# Copilot Instructions for Clinic Voice Agent

## Project Overview
This is a voice scheduling assistant for hospital call centers, integrating with a telephony platform (PBX/CCaaS) for PSTN calls and using Azure AI Foundry for multi-agent orchestration.

## Architecture
- **Voice Gateway API**: Receives audio from telephony platform, uses Azure Speech STT/TTS
- **MAF Orchestrator**: Routes to specialist agents
- **Tools**: Mocked scheduling/OTP APIs (designed for real integration)

## Key Constraints
- UAE North deployment for production (data sovereignty)
- No raw audio storage in Azure (stays in telephony platform)
- Healthcare compliance (ADHICS-like): least-privilege, audit logs
- ~200 calls/day, ~8 concurrent target

## Agents
1. Triage - routing, state, escalation, tool execution (all tools)
2. Identity/OTP - patient verification (lookup_patient, send_otp, verify_otp)
3. Scheduling - book/reschedule/cancel, doctor search (7 tools)
4. Policy - FAQ with citations, Bing Grounding for web search
5. Handoff - mocked warm transfer to human agent (initiate_human_transfer, get_queue_status)

## Tech Stack
- Azure AI Foundry SDK v2
- FastAPI
- Azure Speech STT/TTS
- Azure AI Search (RAG)
- Cosmos DB (sessions)
