"""Session context for tools.

Provides session-scoped state for tool execution.
Factory sets the session ID before executing tools.
"""

from contextvars import ContextVar

# Current session ID (set by factory before tool execution)
_current_session_id: ContextVar[str | None] = ContextVar("session_id", default=None)


def set_session_context(session_id: str) -> None:
    """Set the current session ID for tool execution."""
    _current_session_id.set(session_id)


def get_session_context() -> str | None:
    """Get the current session ID."""
    return _current_session_id.get()


def clear_session_context() -> None:
    """Clear the session context."""
    _current_session_id.set(None)
