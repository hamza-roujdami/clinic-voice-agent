"""Clinic Voice Agent - Tools Package.

All tools use the @tool decorator for automatic schema generation.
"""
from tools.context import (
    set_session_context,
    get_session_context,
    clear_session_context,
)

from tools.scheduling import (
    search_doctors,
    search_available_slots,
    book_appointment,
    reschedule_appointment,
    cancel_appointment,
    get_appointment_history,
    add_to_waitlist,
    send_sms_confirmation,
)
from tools.otp import (
    lookup_patient,
    send_otp,
    verify_otp,
    get_last_verified_patient,
)
from tools.handoff import (
    initiate_human_transfer,
    get_transfer_status,
    get_queue_status,
)

# Grouped by agent for easy wiring
IDENTITY_TOOLS = [lookup_patient, send_otp, verify_otp]
SCHEDULING_TOOLS = [
    search_doctors,
    search_available_slots,
    book_appointment,
    reschedule_appointment,
    cancel_appointment,
    get_appointment_history,
    add_to_waitlist,
    send_sms_confirmation,
]
HANDOFF_TOOLS = [initiate_human_transfer, get_transfer_status, get_queue_status]

__all__ = [
    # Individual tools
    "search_doctors",
    "search_available_slots",
    "book_appointment",
    "reschedule_appointment",
    "cancel_appointment",
    "get_appointment_history",
    "add_to_waitlist",
    "send_sms_confirmation",
    "lookup_patient",
    "send_otp",
    "verify_otp",
    "get_last_verified_patient",
    "initiate_human_transfer",
    "get_transfer_status",
    "get_queue_status",
    # Grouped
    "IDENTITY_TOOLS",
    "SCHEDULING_TOOLS",
    "HANDOFF_TOOLS",
    # Session context
    "set_session_context",
    "get_session_context",
    "clear_session_context",
]