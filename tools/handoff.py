"""Handoff Tools - Mocked warm transfer to human agents.

Simulates the handoff process for escalation to live call center agents.
In production, this would integrate with the telephony platform's CTI/ACD system.
"""

import random
import string
from datetime import datetime
from typing import Annotated

from tools.decorator import tool

# ── Mock transfer state (in-memory for demo) ─────────────────────────────────

_PENDING_TRANSFERS: dict[str, dict] = {}

# Mock queue stats (would come from ACD system in production)
_QUEUE_STATS = {
    "general": {"agents_available": 3, "avg_wait_time": 120},
    "scheduling": {"agents_available": 2, "avg_wait_time": 90},
    "billing": {"agents_available": 1, "avg_wait_time": 180},
    "emergency": {"agents_available": 5, "avg_wait_time": 30},
}


def _generate_transfer_id() -> str:
    """Generate a unique transfer ID."""
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"TRX-{suffix}"


@tool(approval_mode="never_require")
def initiate_human_transfer(
    reason: Annotated[str, "Reason for transferring to a human agent"],
    department: Annotated[
        str,
        "Target department: 'general', 'scheduling', 'billing', or 'emergency'"
    ] = "general",
    priority: Annotated[str, "Priority level: 'normal' or 'high'"] = "normal",
    conversation_summary: Annotated[
        str, 
        "Brief summary of the conversation to pass to the human agent"
    ] = "",
) -> str:
    """Initiate a warm transfer to a human call center agent.
    
    Returns transfer details including estimated wait time and transfer ID.
    In production, this triggers the telephony platform to route the call.
    """
    transfer_id = _generate_transfer_id()
    queue = _QUEUE_STATS.get(department, _QUEUE_STATS["general"])
    
    # Adjust wait time based on priority
    wait_time = queue["avg_wait_time"]
    if priority == "high":
        wait_time = max(30, wait_time // 2)
    
    # Store transfer state
    transfer_record = {
        "transfer_id": transfer_id,
        "department": department,
        "reason": reason,
        "priority": priority,
        "summary": conversation_summary,
        "status": "pending",
        "initiated_at": datetime.now().isoformat(),
        "estimated_wait_seconds": wait_time,
        "agents_available": queue["agents_available"],
    }
    _PENDING_TRANSFERS[transfer_id] = transfer_record
    
    # Format response for the agent
    wait_minutes = wait_time // 60
    wait_seconds = wait_time % 60
    wait_str = f"{wait_minutes} minute(s)" if wait_minutes > 0 else f"{wait_seconds} seconds"
    
    return (
        f"Transfer initiated successfully.\n"
        f"- Transfer ID: {transfer_id}\n"
        f"- Department: {department.title()}\n"
        f"- Priority: {priority.title()}\n"
        f"- Estimated wait time: ~{wait_str}\n"
        f"- Agents available: {queue['agents_available']}\n\n"
        f"The caller will be connected to a live agent shortly. "
        f"Please inform them of the estimated wait time."
    )


@tool(approval_mode="never_require")
def get_transfer_status(
    transfer_id: Annotated[str, "The transfer ID to check status for"],
) -> str:
    """Check the status of a pending human transfer.
    
    Returns current status, position in queue, and updated wait time.
    """
    if transfer_id not in _PENDING_TRANSFERS:
        return f"Transfer {transfer_id} not found. It may have expired or been completed."
    
    record = _PENDING_TRANSFERS[transfer_id]
    
    # Simulate queue progress (mock - would poll ACD in production)
    statuses = ["pending", "in_queue", "connecting", "connected"]
    current_idx = statuses.index(record["status"])
    
    # Randomly progress status for demo
    if current_idx < len(statuses) - 1 and random.random() > 0.5:
        record["status"] = statuses[current_idx + 1]
    
    status_messages = {
        "pending": "Transfer is being processed...",
        "in_queue": f"Caller is in queue. Position: {random.randint(1, 3)}",
        "connecting": "An agent is becoming available. Connecting...",
        "connected": "Caller is now speaking with a human agent.",
    }
    
    return (
        f"Transfer Status: {record['status'].replace('_', ' ').title()}\n"
        f"- Transfer ID: {transfer_id}\n"
        f"- Department: {record['department'].title()}\n"
        f"- {status_messages[record['status']]}"
    )


@tool(approval_mode="never_require")
def get_queue_status(
    department: Annotated[
        str,
        "Department to check: 'general', 'scheduling', 'billing', or 'emergency'"
    ] = "general",
) -> str:
    """Get current queue status for a department.
    
    Returns number of available agents and estimated wait time.
    Useful for setting caller expectations before transfer.
    """
    queue = _QUEUE_STATS.get(department, _QUEUE_STATS["general"])
    
    wait_minutes = queue["avg_wait_time"] // 60
    wait_seconds = queue["avg_wait_time"] % 60
    wait_str = f"{wait_minutes} minute(s)" if wait_minutes > 0 else f"{wait_seconds} seconds"
    
    return (
        f"Queue Status for {department.title()}:\n"
        f"- Available agents: {queue['agents_available']}\n"
        f"- Average wait time: ~{wait_str}\n"
        f"- Current time: {datetime.now().strftime('%I:%M %p')}"
    )
