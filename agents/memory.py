"""Foundry Memory Store - Long-term patient context.

Provides manual API access to Azure AI Foundry Memory for:
- User profile: patient preferences (preferred doctor, time, contact method)
- Chat summaries: distilled conversation topics for continuity

Note: MemorySearchTool in factory.py handles automatic memory during agent
conversations. This module is for app-level operations outside the agent flow.

Usage:
    async with FoundryMemoryStore() as memory:
        await memory.update(patient_mrn, messages)
        memories = await memory.search(patient_mrn, "appointment preferences")
"""

from __future__ import annotations

import logging
import os

from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import ItemParam
from azure.identity.aio import DefaultAzureCredential

logger = logging.getLogger(__name__)


# =============================================================================
# FOUNDRY MEMORY STORE
# =============================================================================


class FoundryMemoryStore:
    """Azure AI Foundry Memory for long-term patient context."""

    def __init__(
        self,
        project_endpoint: str | None = None,
        memory_store_name: str | None = None,
    ):
        self._project_endpoint = project_endpoint or os.environ.get("PROJECT_ENDPOINT")
        self._memory_store_name = memory_store_name or os.environ.get(
            "FOUNDRY_MEMORY_STORE_NAME", "clinic-patient-memory"
        )
        self._credential: DefaultAzureCredential | None = None
        self._client: AIProjectClient | None = None
        self._ready = False

    async def __aenter__(self):
        if not self._project_endpoint:
            raise ValueError("PROJECT_ENDPOINT is required")

        self._credential = DefaultAzureCredential()
        self._client = AIProjectClient(
            endpoint=self._project_endpoint,
            credential=self._credential,
        )

        # Verify memory store exists
        try:
            await self._client.memory_stores.get(self._memory_store_name)
            self._ready = True
            logger.info(f"Memory store '{self._memory_store_name}' exists")
        except Exception as e:
            logger.warning(f"Memory store not available: {e}")

        logger.info(f"FoundryMemoryStore connected: {self._memory_store_name}")
        return self

    async def __aexit__(self, *exc):
        if self._client:
            await self._client.close()
        if self._credential:
            await self._credential.close()

    # -------------------------------------------------------------------------
    # Core Operations
    # -------------------------------------------------------------------------

    async def search(self, scope: str, query: str, max_results: int = 10) -> list[dict]:
        """Search memories for a patient (scope = MRN)."""
        if not self._client or not self._ready:
            return []

        try:
            result = await self._client.memory_stores.search_memories(
                name=self._memory_store_name,
                scope=scope,
                query=query,
                max_results=max_results,
            )
            memories = [
                {
                    "type": getattr(item, "type", "unknown"),
                    "content": getattr(item, "content", str(item)),
                    "score": getattr(item, "score", 0.0),
                }
                for item in result.memories
            ]
            logger.info(f"Found {len(memories)} memories for scope '{scope}'")
            return memories
        except Exception as e:
            logger.warning(f"Memory search failed: {e}")
            return []

    async def update(
        self, scope: str, messages: list[dict], update_delay: int = 0
    ) -> str | None:
        """Update memories from conversation (Foundry extracts & consolidates)."""
        if not self._client or not self._ready:
            return None

        try:
            items = [
                ItemParam(role=msg.get("role", "user"), content=msg.get("content", ""))
                for msg in messages
                if msg.get("content")
            ]
            if not items:
                return None

            poller = await self._client.memory_stores.begin_update_memories(
                name=self._memory_store_name,
                scope=scope,
                items=items,
                update_delay=update_delay,
            )
            result = await poller.result()
            logger.info(f"Updated memories for '{scope}': {len(result.memory_operations)} ops")
            return getattr(result, "update_id", "success")
        except Exception as e:
            logger.warning(f"Memory update failed: {e}")
            return None

    # -------------------------------------------------------------------------
    # Convenience Methods
    # -------------------------------------------------------------------------

    async def get_patient_profile(self, patient_mrn: str) -> dict | None:
        """Get patient profile (preferred doctor, time, contact method)."""
        memories = await self.search(
            scope=patient_mrn,
            query="patient profile preferences contact preferred doctor time",
            max_results=5,
        )
        profile = {}
        for mem in memories:
            if mem.get("type") == "user_profile":
                content = mem.get("content", {})
                if isinstance(content, dict):
                    profile.update(content)
                elif isinstance(content, str):
                    profile["info"] = content
        return profile or None

    async def get_chat_summary(self, patient_mrn: str, topic: str = "") -> str | None:
        """Get chat summary for conversation continuity."""
        query = f"conversation summary {topic}" if topic else "recent conversation summary"
        memories = await self.search(scope=patient_mrn, query=query, max_results=3)
        summaries = [
            m.get("content", "")
            for m in memories
            if m.get("type") == "chat_summary" and isinstance(m.get("content"), str)
        ]
        return " ".join(summaries) or None
