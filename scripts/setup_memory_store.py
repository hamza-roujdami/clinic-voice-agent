#!/usr/bin/env python3
"""Create Foundry Memory Store for clinic voice agent.

Uses REST API since SDK doesn't expose memory_stores operations yet.
Reference: https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/memory-usage
"""

import asyncio
import os
import httpx
from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

MEMORY_STORE_NAME = "clinic-patient-memory"
API_VERSION = "2025-11-15-preview"


async def get_access_token() -> str:
    """Get access token for Azure AI Foundry."""
    credential = DefaultAzureCredential()
    token = await credential.get_token("https://ai.azure.com/.default")
    await credential.close()
    return token.token


async def create_memory_store():
    """Create the memory store using REST API."""
    endpoint = os.environ.get("PROJECT_ENDPOINT")
    if not endpoint:
        print("ERROR: PROJECT_ENDPOINT not set")
        return

    token = await get_access_token()
    
    # Memory store configuration
    chat_model = os.environ.get("FOUNDRY_MODEL_PRIMARY", "gpt-4o-mini")
    embedding_model = os.environ.get("FOUNDRY_EMBEDDING_MODEL", "text-embedding-3-small")
    
    payload = {
        "name": MEMORY_STORE_NAME,
        "description": "Memory store for clinic voice agent - patient preferences and context",
        "definition": {
            "kind": "default",
            "chat_model": chat_model,
            "embedding_model": embedding_model,
            "options": {
                "chat_summary_enabled": True,
                "user_profile_enabled": True,
                "user_profile_details": "preferred_doctor, preferred_time_of_day, preferred_location, contact_preference, language_preference"
            }
        }
    }
    
    url = f"{endpoint}/memory_stores?api-version={API_VERSION}"
    
    async with httpx.AsyncClient() as client:
        # First check if it exists
        print(f"Checking if memory store '{MEMORY_STORE_NAME}' exists...")
        check_url = f"{endpoint}/memory_stores/{MEMORY_STORE_NAME}?api-version={API_VERSION}"
        headers = {"Authorization": f"Bearer {token}"}
        
        check_response = await client.get(check_url, headers=headers)
        
        if check_response.status_code == 200:
            print(f"Memory store '{MEMORY_STORE_NAME}' already exists:")
            print(check_response.json())
            return check_response.json()
        
        # Create new memory store
        print(f"Creating memory store '{MEMORY_STORE_NAME}'...")
        print(f"  Chat model: {chat_model}")
        print(f"  Embedding model: {embedding_model}")
        
        response = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=60.0
        )
        
        if response.status_code in (200, 201):
            result = response.json()
            print(f"\n✅ Memory store created successfully!")
            print(f"  Name: {result.get('name')}")
            print(f"  Description: {result.get('description')}")
            return result
        else:
            print(f"❌ Failed to create memory store: {response.status_code}")
            print(response.text)
            return None


async def list_memory_stores():
    """List all memory stores in the project."""
    endpoint = os.environ.get("PROJECT_ENDPOINT")
    if not endpoint:
        print("ERROR: PROJECT_ENDPOINT not set")
        return
    
    token = await get_access_token()
    url = f"{endpoint}/memory_stores?api-version={API_VERSION}"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0
        )
        
        if response.status_code == 200:
            stores = response.json()
            print(f"\n=== Memory Stores ===")
            for store in stores.get("data", []):
                print(f"  - {store.get('name')}: {store.get('description', 'No description')}")
            return stores
        else:
            print(f"Failed to list memory stores: {response.status_code}")
            print(response.text)
            return None


async def main():
    print("=== Foundry Memory Store Setup ===\n")
    
    # Create the memory store
    await create_memory_store()
    
    # List all stores
    await list_memory_stores()


if __name__ == "__main__":
    asyncio.run(main())
