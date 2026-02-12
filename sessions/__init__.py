"""Clinic Voice Agent - Sessions Package.

Provides session management with persistence:
- CosmosSessionStore: Cosmos DB persistence for sessions
- SessionManager: Unified interface with Cosmos + Memory
"""

from sessions.cosmos_store import CosmosSessionStore
from sessions.manager import SessionManager

__all__ = ["CosmosSessionStore", "SessionManager"]
