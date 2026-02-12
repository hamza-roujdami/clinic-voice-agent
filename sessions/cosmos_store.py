"""Cosmos DB Session Store.

Persistent session storage for voice conversations with conversation history.
Stores workflow state, conversation turns, and patient context.

Schema:
{
    "id": "session-uuid",
    "session_id": "session-uuid",  # partition key
    "created_at": "2026-02-09T...",
    "updated_at": "2026-02-09T...",
    "patient_mrn": "MRN-5001" | null,
    "patient_verified": false,
    "conversation_history": [
        {"role": "user", "text": "...", "timestamp": "..."},
        {"role": "assistant", "text": "...", "agent": "triage-agent", "timestamp": "..."}
    ],
    "patient_context": {
        "name": "Khalid Al-Rashid",
        "phone_masked": "+9715****567",
        "dob": "1985-03-12",
        "verified_at": "..."
    },
    "metadata": {
        "last_agent": "triage-agent",
        "handoff_count": 0,
        "tool_calls": [...]
    },
    "ttl": 86400  # 24 hours auto-expiry
}
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from azure.identity.aio import DefaultAzureCredential

logger = logging.getLogger(__name__)


class CosmosSessionStore:
    """Async Cosmos DB session store with conversation history."""

    DEFAULT_TTL = 86400  # 24 hours in seconds

    def __init__(
        self,
        endpoint: str | None = None,
        database_name: str | None = None,
        container_name: str | None = None,
        credential: Any | None = None,
        connection_string: str | None = None,
    ):
        """Initialize Cosmos session store.
        
        Args:
            endpoint: Cosmos DB endpoint. Uses COSMOS_ENDPOINT env var if not provided.
            database_name: Database name. Uses COSMOS_DATABASE env var if not provided.
            container_name: Container name. Uses COSMOS_CONTAINER env var if not provided.
            credential: Azure credential. Uses DefaultAzureCredential if not provided.
            connection_string: Connection string (alternative to endpoint+credential).
                Uses COSMOS_CONNECTION_STRING env var if not provided.
        """
        self._connection_string = connection_string or os.environ.get("COSMOS_CONNECTION_STRING")
        self._endpoint = endpoint or os.environ.get("COSMOS_ENDPOINT")
        self._database_name = database_name or os.environ.get("COSMOS_DATABASE", "enterprise_memory")
        self._container_name = container_name or os.environ.get("COSMOS_CONTAINER", "sessions")
        self._credential = credential
        self._client: CosmosClient | None = None
        self._container = None

    async def __aenter__(self):
        # Prefer connection string (key-based auth) over RBAC
        if self._connection_string:
            self._client = CosmosClient.from_connection_string(self._connection_string)
            logger.info("CosmosSessionStore using connection string auth")
        elif self._endpoint:
            self._credential = self._credential or DefaultAzureCredential()
            self._client = CosmosClient(self._endpoint, credential=self._credential)
            logger.info("CosmosSessionStore using RBAC auth")
        else:
            raise ValueError("COSMOS_CONNECTION_STRING or COSMOS_ENDPOINT is required")
        
        # Get or create database and container
        database = await self._client.create_database_if_not_exists(self._database_name)
        self._container = await database.create_container_if_not_exists(
            id=self._container_name,
            partition_key=PartitionKey(path="/session_id"),
            default_ttl=self.DEFAULT_TTL,
        )
        
        logger.info(f"CosmosSessionStore connected: {self._database_name}/{self._container_name}")
        return self

    async def __aexit__(self, *exc):
        if self._client:
            await self._client.close()
        if self._credential and hasattr(self._credential, "close"):
            await self._credential.close()

    async def create_session(self, session_id: str) -> dict:
        """Create a new session."""
        now = datetime.now(timezone.utc).isoformat()
        session = {
            "id": session_id,
            "session_id": session_id,
            "created_at": now,
            "updated_at": now,
            "patient_mrn": None,
            "patient_verified": False,
            "conversation_history": [],
            "patient_context": None,
            "metadata": {
                "last_agent": None,
                "handoff_count": 0,
                "tool_calls": [],
            },
            "ttl": self.DEFAULT_TTL,
        }
        await self._container.create_item(session)
        logger.info(f"[{session_id}] Session created in Cosmos")
        return session

    async def get_session(self, session_id: str) -> dict | None:
        """Get session by ID. Returns None if not found."""
        try:
            session = await self._container.read_item(
                item=session_id, 
                partition_key=session_id
            )
            return session
        except CosmosResourceNotFoundError:
            return None

    async def update_session(self, session: dict) -> dict:
        """Update an existing session."""
        session["updated_at"] = datetime.now(timezone.utc).isoformat()
        await self._container.replace_item(item=session["id"], body=session)
        return session

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session. Returns True if deleted, False if not found."""
        try:
            await self._container.delete_item(item=session_id, partition_key=session_id)
            logger.info(f"[{session_id}] Session deleted from Cosmos")
            return True
        except CosmosResourceNotFoundError:
            return False

    async def add_turn(
        self,
        session_id: str,
        role: str,
        text: str,
        agent: str | None = None,
        tool_calls: list[dict] | None = None,
    ) -> dict:
        """Add a conversation turn to the session history.
        
        Args:
            session_id: Session ID
            role: "user" or "assistant"
            text: Message text
            agent: Agent name (for assistant messages)
            tool_calls: List of tool calls made during this turn
        """
        session = await self.get_session(session_id)
        if not session:
            session = await self.create_session(session_id)

        turn = {
            "role": role,
            "text": text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if agent:
            turn["agent"] = agent
        if tool_calls:
            turn["tool_calls"] = tool_calls

        session["conversation_history"].append(turn)
        
        if agent:
            session["metadata"]["last_agent"] = agent
        if tool_calls:
            session["metadata"]["tool_calls"].extend(tool_calls)

        return await self.update_session(session)

    async def set_patient_context(
        self,
        session_id: str,
        mrn: str,
        name: str,
        phone_masked: str,
        dob: str,
        verified: bool = False,
    ) -> dict:
        """Set patient context after lookup/verification.
        
        Args:
            session_id: Session ID
            mrn: Patient MRN
            name: Patient name
            phone_masked: Masked phone number
            dob: Date of birth
            verified: Whether OTP verification is complete
        """
        session = await self.get_session(session_id)
        if not session:
            session = await self.create_session(session_id)

        session["patient_mrn"] = mrn
        session["patient_verified"] = verified
        session["patient_context"] = {
            "name": name,
            "phone_masked": phone_masked,
            "dob": dob,
            "verified_at": datetime.now(timezone.utc).isoformat() if verified else None,
        }

        return await self.update_session(session)

    async def mark_patient_verified(self, session_id: str) -> dict:
        """Mark the patient as OTP-verified."""
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session["patient_verified"] = True
        if session.get("patient_context"):
            session["patient_context"]["verified_at"] = datetime.now(timezone.utc).isoformat()

        return await self.update_session(session)

    async def increment_handoff(self, session_id: str, from_agent: str, to_agent: str) -> dict:
        """Record a handoff between agents."""
        session = await self.get_session(session_id)
        if not session:
            session = await self.create_session(session_id)

        session["metadata"]["handoff_count"] += 1
        session["metadata"]["last_agent"] = to_agent
        
        # Add handoff to history as a system event
        session["conversation_history"].append({
            "role": "system",
            "text": f"Handoff from {from_agent} to {to_agent}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "handoff",
            "from_agent": from_agent,
            "to_agent": to_agent,
        })

        return await self.update_session(session)

    async def get_conversation_history(self, session_id: str) -> list[dict]:
        """Get conversation history for a session."""
        session = await self.get_session(session_id)
        if not session:
            return []
        return session.get("conversation_history", [])

    async def get_patient_context(self, session_id: str) -> dict | None:
        """Get cached patient context for a session."""
        session = await self.get_session(session_id)
        if not session:
            return None
        return session.get("patient_context")

    async def is_patient_verified(self, session_id: str) -> bool:
        """Check if patient is verified for this session."""
        session = await self.get_session(session_id)
        if not session:
            return False
        return session.get("patient_verified", False)

    async def list_active_sessions(self, limit: int = 100) -> list[dict]:
        """List active sessions (for admin/monitoring)."""
        query = "SELECT c.session_id, c.created_at, c.updated_at, c.patient_mrn, c.patient_verified FROM c ORDER BY c.updated_at DESC"
        items = []
        async for item in self._container.query_items(query=query, max_item_count=limit):
            items.append(item)
        return items
