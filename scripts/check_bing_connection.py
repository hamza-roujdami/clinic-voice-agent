#!/usr/bin/env python3
"""Check Bing connection details in AI Foundry."""
import asyncio
import os
from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import DefaultAzureCredential

async def check_connections():
    credential = DefaultAzureCredential()
    client = AIProjectClient(
        endpoint=os.environ.get('PROJECT_ENDPOINT'),
        credential=credential,
    )
    
    print('All connections in project:')
    print('-' * 60)
    try:
        async for conn in client.connections.list():
            print(f'\nName: {conn.name}')
            print(f'  ID: {conn.id[:100]}...' if len(conn.id) > 100 else f'  ID: {conn.id}')
            # Print all non-callable, non-private attributes
            for attr in sorted(dir(conn)):
                if not attr.startswith('_') and attr not in ['name', 'id']:
                    try:
                        val = getattr(conn, attr)
                        if not callable(val) and val is not None:
                            print(f'  {attr}: {val}')
                    except:
                        pass
    except Exception as e:
        print(f'Error: {e}')
    finally:
        await client.close()
        await credential.close()

if __name__ == '__main__':
    asyncio.run(check_connections())
