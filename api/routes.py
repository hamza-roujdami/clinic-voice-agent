"""API Routes for Clinic Voice Agent.

Endpoints:
- POST /chat - Text-based chat (multi-turn via Responses API)
- POST /voice/turn - Voice turn (Phase 2)
- GET /session/{session_id} - Get session state
- GET /sessions - List active sessions (admin)
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from sessions import SessionManager
from tools import get_last_verified_patient, set_session_context

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Models ───────────────────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str
    session_id: str
    agent: str | None = None
    tools_called: list[str] = []


# ── Endpoints ────────────────────────────────────────────────────────────────


def _get_sessions(req: Request) -> SessionManager:
    """Get session manager from app state."""
    sessions = getattr(req.app.state, "sessions", None)
    if sessions is None:
        raise HTTPException(status_code=503, detail="Session manager not initialized.")
    return sessions


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, req: Request):
    """Process a text chat message through the Foundry triage agent."""
    factory = req.app.state.factory
    if factory is None:
        raise HTTPException(status_code=503, detail="Agent factory not initialized. Check PROJECT_ENDPOINT.")

    sessions = _get_sessions(req)
    session_id = request.session_id or str(uuid.uuid4())
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    try:
        # Ensure session exists
        await sessions.get_or_create(session_id)
        
        # Record user turn
        await sessions.add_turn(session_id, "user", message)
        
        # Set session context for tools
        set_session_context(session_id)
        
        # Get conversation_id for multi-turn (if continuing conversation)
        conversation_id = sessions.get_conversation_id(session_id)
        
        if conversation_id:
            logger.info(f"[{session_id}] Continuing conversation: {message[:80]}")
        else:
            logger.info(f"[{session_id}] New session: {message[:80]}")
        
        # Run agent via factory.run()
        # Pass session_id as primary key, conversation_id for multi-turn continuity
        result = await factory.run(
            message=message,
            session_id=session_id,
            conversation_id=conversation_id,
        )
        
        response_text = result["response"]
        new_conversation_id = result["conversation_id"]
        tools_called = result["tools_called"]
        
        # Save conversation_id for next turn
        sessions.set_conversation_id(session_id, new_conversation_id)
        
        logger.info(f"[{session_id}] Agent response: {response_text[:120]}")
        
        # Record assistant turn
        await sessions.add_turn(session_id, "assistant", response_text)
        
        # Check if patient was verified and update session context
        verified_patient = get_last_verified_patient(session_id)
        if verified_patient:
            phone = verified_patient.get("phone", "")
            phone_masked = phone[:5] + "****" + phone[-3:] if phone else ""
            await sessions.set_patient_context(
                session_id,
                mrn=verified_patient.get("mrn"),
                name=verified_patient.get("name", ""),
                phone_masked=phone_masked,
                dob=verified_patient.get("dob", ""),
                verified=True,
            )
            logger.info(f"[{session_id}] Patient context cached: {verified_patient.get('mrn')}")
        
        return ChatResponse(
            response=response_text,
            session_id=session_id,
            agent=None,
            tools_called=tools_called,
        )

    except Exception as e:
        logger.exception(f"[{session_id}] Error processing chat")
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")


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
