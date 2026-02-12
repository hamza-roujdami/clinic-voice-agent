"""Session Manager - Unified session handling with Cosmos + Memory.

Combines:
- Cosmos DB: Session state, conversation history, patient context
- Foundry Memory: Long-term patient preferences, chat summaries
- Workflow cache: Active agent workflows

Usage:
    async with SessionManager() as sessions:
        # Create or get session
        session = await sessions.get_or_create(session_id)
        
        # Add turn with persistence
        await sessions.add_turn(session_id, "user", "I need an appointment")
        
        # Get patient memories for grounding
        memories = await sessions.get_patient_memories(patient_mrn)
"""

from __future__ import annotations

import logging
from typing import Any

from sessions.cosmos_store import CosmosSessionStore
from agents.memory import FoundryMemoryStore

logger = logging.getLogger(__name__)


class SessionManager:
    """Unified session management with persistence and memory.
    
    Manages:
    - Session lifecycle (create, get, delete)
    - Conversation history (persisted to Cosmos)
    - Patient context caching (in Cosmos, verified status)
    - Long-term memories (Foundry Memory for preferences)
    - Active workflows (runtime cache for HandoffBuilder instances)
    
    Requires:
    - Cosmos DB for session persistence
    - Foundry Memory for long-term patient context
    """

    def __init__(
        self,
        cosmos_endpoint: str | None = None,
        cosmos_database: str | None = None,
        cosmos_container: str | None = None,
        project_endpoint: str | None = None,
        memory_store_name: str | None = None,
    ):
        """Initialize session manager.
        
        Args:
            cosmos_endpoint: Cosmos DB endpoint (or COSMOS_ENDPOINT env var)
            cosmos_database: Cosmos database name
            cosmos_container: Cosmos container name
            project_endpoint: Foundry project endpoint (or PROJECT_ENDPOINT env var)
            memory_store_name: Foundry memory store name
        """
        # Cosmos session store (required)
        self._cosmos = CosmosSessionStore(
            endpoint=cosmos_endpoint,
            database_name=cosmos_database,
            container_name=cosmos_container,
        )
        
        # Foundry Memory store (required)
        self._memory = FoundryMemoryStore(
            project_endpoint=project_endpoint,
            memory_store_name=memory_store_name,
        )
        
        # Workflow cache (runtime only, can't be serialized)
        self._workflows: dict[str, Any] = {}

    async def __aenter__(self):
        await self._cosmos.__aenter__()
        await self._memory.__aenter__()
        logger.info("SessionManager initialized: Cosmos + Foundry Memory")
        return self

    async def __aexit__(self, *exc):
        await self._cosmos.__aexit__(*exc)
        await self._memory.__aexit__(*exc)
        self._workflows.clear()

    # ── Session Lifecycle ────────────────────────────────────────────────────

    async def get_or_create(self, session_id: str) -> dict:
        """Get existing session or create new one."""
        session = await self.get_session(session_id)
        if session is None:
            session = await self.create_session(session_id)
        return session

    async def create_session(self, session_id: str) -> dict:
        """Create a new session."""
        return await self._cosmos.create_session(session_id)

    async def get_session(self, session_id: str) -> dict | None:
        """Get session by ID."""
        return await self._cosmos.get_session(session_id)

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and cleanup."""
        # Remove workflow from cache
        if session_id in self._workflows:
            del self._workflows[session_id]
        return await self._cosmos.delete_session(session_id)

    # ── Workflow Management ──────────────────────────────────────────────────

    def get_workflow(self, session_id: str) -> Any | None:
        """Get cached workflow for session."""
        return self._workflows.get(session_id)

    def set_workflow(self, session_id: str, workflow: Any, pending_requests: list = None):
        """Cache workflow for session."""
        self._workflows[session_id] = {
            "workflow": workflow,
            "pending_requests": pending_requests or [],
        }

    def get_pending_requests(self, session_id: str) -> list:
        """Get pending requests for workflow."""
        entry = self._workflows.get(session_id, {})
        return entry.get("pending_requests", [])

    def set_pending_requests(self, session_id: str, pending: list):
        """Update pending requests."""
        if session_id in self._workflows:
            self._workflows[session_id]["pending_requests"] = pending

    def has_workflow(self, session_id: str) -> bool:
        """Check if session has an active workflow."""
        return session_id in self._workflows

    def clear_workflow(self, session_id: str):
        """Remove workflow from cache."""
        if session_id in self._workflows:
            del self._workflows[session_id]

    # ── Thread Management (for direct agent.run API) ────────────────────────

    def get_thread(self, session_id: str) -> Any | None:
        """Get cached thread for session."""
        entry = self._workflows.get(session_id, {})
        return entry.get("thread")

    def set_thread(self, session_id: str, thread: Any, agent: Any = None):
        """Cache thread and agent for session."""
        self._workflows[session_id] = {
            "thread": thread,
            "agent": agent,
        }

    def get_agent(self, session_id: str) -> Any | None:
        """Get cached agent for session."""
        entry = self._workflows.get(session_id, {})
        return entry.get("agent")

    def clear_thread(self, session_id: str):
        """Remove thread from cache."""
        if session_id in self._workflows:
            del self._workflows[session_id]

    # ── Conversation ID Management (for Responses API) ──────────────────────

    def get_conversation_id(self, session_id: str) -> str | None:
        """Get conversation ID for multi-turn (previous_response_id)."""
        entry = self._workflows.get(session_id, {})
        return entry.get("conversation_id")

    def set_conversation_id(self, session_id: str, conversation_id: str):
        """Cache conversation ID for multi-turn."""
        if session_id not in self._workflows:
            self._workflows[session_id] = {}
        self._workflows[session_id]["conversation_id"] = conversation_id

    def clear_conversation(self, session_id: str):
        """Remove conversation from cache."""
        if session_id in self._workflows:
            del self._workflows[session_id]

    # ── Conversation History ─────────────────────────────────────────────────

    async def add_turn(
        self,
        session_id: str,
        role: str,
        text: str,
        agent: str | None = None,
        tool_calls: list[dict] | None = None,
    ) -> dict:
        """Add a conversation turn."""
        return await self._cosmos.add_turn(session_id, role, text, agent, tool_calls)

    async def get_conversation_history(self, session_id: str) -> list[dict]:
        """Get conversation history."""
        return await self._cosmos.get_conversation_history(session_id)

    async def record_handoff(self, session_id: str, from_agent: str, to_agent: str):
        """Record a handoff event."""
        await self._cosmos.increment_handoff(session_id, from_agent, to_agent)

    # ── Patient Context ──────────────────────────────────────────────────────

    async def set_patient_context(
        self,
        session_id: str,
        mrn: str,
        name: str,
        phone_masked: str,
        dob: str,
        verified: bool = False,
    ) -> dict:
        """Set patient context for session."""
        return await self._cosmos.set_patient_context(
            session_id, mrn, name, phone_masked, dob, verified
        )

    async def mark_patient_verified(self, session_id: str):
        """Mark patient as OTP-verified."""
        await self._cosmos.mark_patient_verified(session_id)

    async def get_patient_context(self, session_id: str) -> dict | None:
        """Get cached patient context."""
        return await self._cosmos.get_patient_context(session_id)

    async def is_patient_verified(self, session_id: str) -> bool:
        """Check if patient is verified."""
        return await self._cosmos.is_patient_verified(session_id)

    async def get_patient_mrn(self, session_id: str) -> str | None:
        """Get patient MRN if verified.
        
        Returns MRN only if patient verification is complete.
        Used for Foundry Memory scope.
        """
        session = await self._cosmos.get_session(session_id)
        if session and session.get("patient_verified"):
            return session.get("patient_mrn")
        return None

    # ── Long-term Memory ─────────────────────────────────────────────────────

    async def get_patient_memories(self, patient_mrn: str, topic: str = "") -> dict:
        """Get patient memories for grounding.
        
        Returns combined profile and relevant chat summaries.
        """
        result = {}
        
        # Get profile memories
        profile = await self._memory.get_patient_profile(patient_mrn)
        if profile:
            result["profile"] = profile
        
        # Get relevant chat summary
        summary = await self._memory.get_chat_summary(patient_mrn, topic)
        if summary:
            result["previous_context"] = summary
        
        return result

    async def update_patient_memories(self, patient_mrn: str, conversation: list[dict]):
        """Update long-term memories from conversation."""
        await self._memory.update(patient_mrn, conversation)

    async def search_memories(self, patient_mrn: str, query: str) -> list[dict]:
        """Search patient memories."""
        return await self._memory.search(patient_mrn, query)

    # ── Admin ────────────────────────────────────────────────────────────────

    async def list_active_sessions(self, limit: int = 100) -> list[dict]:
        """List active sessions for monitoring."""
        return await self._cosmos.list_active_sessions(limit)

    def get_stats(self) -> dict:
        """Get session manager stats."""
        return {
            "active_workflows": len(self._workflows),
        }
