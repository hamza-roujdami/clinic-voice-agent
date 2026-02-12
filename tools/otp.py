"""OTP Tools - Patient identity verification.

Mock implementations for patient lookup and OTP verification.
Designed for easy swap to real SMS/voice OTP integration.
"""

from typing import Annotated

from tools.context import get_session_context
from tools.decorator import tool

# ── In-memory mock data ──────────────────────────────────────────────────────

_PATIENTS = {
    "MRN-5001": {
        "mrn": "MRN-5001",
        "name": "Khalid Al-Rashid",
        "phone": "+971501234567",
        "dob": "1985-03-12",
        "emirate_id": "784-****-*****-0",
    },
    "MRN-5050": {
        "mrn": "MRN-5050",
        "name": "Hamza El-Ghoujdami",
        "phone": "+971544842805",
        "dob": "1993-05-28",
        "emirate_id": "784-****-*****-1",
    },
    "MRN-5002": {
        "mrn": "MRN-5002",
        "name": "Mariam Abdullah",
        "phone": "+971509876543",
        "dob": "1990-07-22",
        "emirate_id": "784-****-*****-2",
    },
    "MRN-5003": {
        "mrn": "MRN-5003",
        "name": "Hassan Youssef",
        "phone": "+971507654321",
        "dob": "1978-11-05",
        "emirate_id": "784-****-*****-3",
    },
}

# Phone number → MRN lookup (reverse index)
_PHONE_INDEX = {p["phone"]: mrn for mrn, p in _PATIENTS.items()}

# Active OTP sessions: mrn → code
_ACTIVE_OTPS: dict[str, str] = {}

# Session-scoped verified patients: session_id → set of MRNs
_VERIFIED: dict[str, set[str]] = {}

# Session-scoped last verified patient: session_id → patient dict
_LAST_VERIFIED: dict[str, dict] = {}


def get_last_verified_patient(session_id: str | None = None) -> dict | None:
    """Get the last verified patient for a session and clear the flag.
    
    Args:
        session_id: Session ID to check (uses context if not provided)
    
    Returns:
        Patient dict if recently verified, None otherwise
    """
    sid = session_id or get_session_context()
    if not sid:
        return None
    result = _LAST_VERIFIED.pop(sid, None)
    return result


def get_patient_data(mrn: str) -> dict | None:
    """Get patient data by MRN (utility for session context)."""
    return _PATIENTS.get(mrn)


# ── Tools ────────────────────────────────────────────────────────────────────


@tool(approval_mode="never_require")
def lookup_patient(
    identifier: Annotated[str, "Patient phone number (e.g. +971501234567) or MRN (e.g. MRN-5001)"],
) -> str:
    """Look up a patient by phone number or MRN. Returns masked patient info for confirmation."""
    # Try MRN first
    if identifier.upper().startswith("MRN"):
        patient = _PATIENTS.get(identifier.upper())
    else:
        # Try phone number
        mrn = _PHONE_INDEX.get(identifier)
        patient = _PATIENTS.get(mrn) if mrn else None

    if not patient:
        return f"No patient found with identifier '{identifier}'. Please verify and try again."

    # Return masked info for the agent to confirm with the caller
    name = patient["name"]
    phone = patient["phone"]
    masked_phone = phone[:5] + "****" + phone[-3:]
    return (
        f"Patient found:\n"
        f"  Name: {name}\n"
        f"  MRN: {patient['mrn']}\n"
        f"  Phone (masked): {masked_phone}\n"
        f"  Date of Birth: {patient['dob']}\n"
        f"An OTP must be sent and verified before accessing appointment details."
    )


@tool(approval_mode="never_require")
def send_otp(
    patient_mrn: Annotated[str, "Patient MRN to send OTP to, e.g. MRN-5001"],
) -> str:
    """Send a one-time password to the patient's registered phone number for identity verification."""
    patient = _PATIENTS.get(patient_mrn)
    if not patient:
        return f"Patient '{patient_mrn}' not found."

    # Generate a 6-digit OTP (mock: always 123456 for demo convenience)
    otp = "123456"
    _ACTIVE_OTPS[patient_mrn] = otp

    masked_phone = patient["phone"][:5] + "****" + patient["phone"][-3:]
    return (
        f"OTP sent to {masked_phone}.\n"
        f"Please ask the patient to provide the 6-digit code.\n"
        f"(Demo hint: the code is {otp})"
    )


@tool(approval_mode="never_require")
def verify_otp(
    patient_mrn: Annotated[str, "Patient MRN"],
    otp_code: Annotated[str, "The 6-digit OTP code provided by the patient"],
) -> str:
    """Verify the OTP code provided by the patient. Must be called before accessing PHI."""
    expected = _ACTIVE_OTPS.get(patient_mrn)
    if not expected:
        return f"No active OTP for patient '{patient_mrn}'. Please send an OTP first."

    if otp_code.strip() == expected:
        session_id = get_session_context()
        if session_id:
            # Add to session-scoped verified set
            if session_id not in _VERIFIED:
                _VERIFIED[session_id] = set()
            _VERIFIED[session_id].add(patient_mrn)
            
            # Track for session update
            patient = _PATIENTS.get(patient_mrn, {})
            _LAST_VERIFIED[session_id] = {"mrn": patient_mrn, **patient}
        
        del _ACTIVE_OTPS[patient_mrn]
        patient = _PATIENTS.get(patient_mrn, {})
        return (
            f"Identity verified successfully for {patient.get('name', patient_mrn)}.\n"
            f"  MRN: {patient_mrn}\n"
            f"You may now access appointment information for this patient."
        )
    else:
        return "Invalid OTP code. Please ask the patient to try again."


def is_patient_verified(mrn: str, session_id: str | None = None) -> bool:
    """Check if a patient has been verified in current session.
    
    Args:
        mrn: Patient MRN to check
        session_id: Session ID to check (uses context if not provided)
    """
    sid = session_id or get_session_context()
    if not sid:
        return False
    return mrn in _VERIFIED.get(sid, set())