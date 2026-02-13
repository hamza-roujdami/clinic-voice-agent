"""
Chat and session management API for clinic voice agent.

Endpoints:
    POST /chat              Main chat endpoint - processes messages through Foundry agent
    POST /voice/turn        Voice turn handling (Phase 2 - telephony integration)
    GET  /session/{id}      Get session state (patient context, verification status)
    GET  /session/{id}/history  Conversation history for debugging
    DELETE /session/{id}    End session and cleanup
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from sessions import SessionManager
from tools import get_last_verified_patient, set_session_context

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None  # Auto-generated if not provided


class ChatResponse(BaseModel):
    response: str
    session_id: str
    agent: str | None = None       # For future multi-agent routing visibility
    tools_called: list[str] = []   # Tools invoked during this turn (for debugging)


def _get_sessions(req: Request) -> SessionManager:
    """Get session manager from app state."""
    sessions = getattr(req.app.state, "sessions", None)
    if sessions is None:
        raise HTTPException(status_code=503, detail="Session manager not initialized.")
    return sessions


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, req: Request):
    """
    Process a chat message through the Foundry triage agent.
    
    Flow:
    1. Get or create session (Cosmos DB for prod, in-memory for dev)
    2. Record user turn in conversation history
    3. Pass conversation_id for multi-turn context (Foundry handles state)
    4. Execute agent with tool loop until response
    5. Cache verified patient info for session-level access
    """
    factory = req.app.state.factory
    if factory is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    sessions = _get_sessions(req)
    session_id = request.session_id or str(uuid.uuid4())
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    try:
        await sessions.get_or_create(session_id)
        await sessions.add_turn(session_id, "user", message)
        
        # Tools need session context for OTP state, patient lookup caching
        set_session_context(session_id)
        
        # conversation_id enables multi-turn: Foundry maintains message history
        conversation_id = sessions.get_conversation_id(session_id)
        logger.info(f"[{session_id}] {'Continuing' if conversation_id else 'New'}: {message[:80]}")
        
        result = await factory.run(
            message=message,
            session_id=session_id,
            conversation_id=conversation_id,
        )
        
        response_text = result["response"]
        sessions.set_conversation_id(session_id, result["conversation_id"])
        await sessions.add_turn(session_id, "assistant", response_text)
        
        # After OTP verification, cache patient info at session level
        # so subsequent requests don't need re-verification
        verified_patient = get_last_verified_patient(session_id)
        if verified_patient:
            phone = verified_patient.get("phone", "")
            await sessions.set_patient_context(
                session_id,
                mrn=verified_patient.get("mrn"),
                name=verified_patient.get("name", ""),
                phone_masked=phone[:5] + "****" + phone[-3:] if phone else "",
                dob=verified_patient.get("dob", ""),
                verified=True,
            )
        
        return ChatResponse(
            response=response_text,
            session_id=session_id,
            agent=None,
            tools_called=result["tools_called"],
        )

    except Exception as e:
        logger.exception(f"[{session_id}] Chat error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/voice/turn")
async def voice_turn():
    """Process a voice turn from telephony platform (Phase 2)."""
    raise HTTPException(status_code=501, detail="Voice turn not implemented - Phase 2")


@router.get("/session/{session_id}")
async def get_session(session_id: str, req: Request):
    """Get session state."""
    sessions = _get_sessions(req)
    session = await sessions.get_or_create(session_id)
    if not session:
        return {"session_id": session_id, "active": False}
    return {
        "session_id": session_id,
        "active": True,
        "patient_mrn": session.get("patient_mrn"),
        "patient_verified": session.get("patient_verified", False),
        "created_at": session.get("created_at"),
        "updated_at": session.get("updated_at"),
    }


@router.get("/session/{session_id}/history")
async def get_session_history(session_id: str, req: Request):
    """Get conversation history for a session."""
    sessions = _get_sessions(req)
    history = await sessions.get_conversation_history(session_id)
    return {"session_id": session_id, "history": history}


@router.get("/sessions")
async def list_sessions(req: Request, limit: int = 50):
    """List recent sessions."""
    sessions = _get_sessions(req)
    items = await sessions.list_active_sessions(limit=limit)
    return {"sessions": items}


@router.delete("/session/{session_id}")
async def end_session(session_id: str, req: Request):
    """End a session and clean up resources."""
    sessions = _get_sessions(req)
    sessions.clear_conversation(session_id)
    return {"session_id": session_id, "ended": True}
