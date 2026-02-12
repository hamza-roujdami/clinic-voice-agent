"""Scheduling Tools - Mocked appointment actions.

Mock implementations designed for easy swap to real CRM/scheduling APIs.
Uses MAF @tool decorator for automatic schema generation.
"""

import uuid
from datetime import datetime
from typing import Annotated

from tools.decorator import tool

# ── In-memory mock data ──────────────────────────────────────────────────────

_DOCTORS = [
    {"id": "DR001", "name": "Dr. Sarah Al-Mansoori", "specialty": "Cardiology", "clinic": "Heart Center - Floor 3"},
    {"id": "DR002", "name": "Dr. Ahmed Khalil", "specialty": "Orthopedics", "clinic": "Bone & Joint - Floor 2"},
    {"id": "DR003", "name": "Dr. Fatima Hassan", "specialty": "Dermatology", "clinic": "Skin Care - Floor 1"},
    {"id": "DR004", "name": "Dr. Omar Nasser", "specialty": "Pediatrics", "clinic": "Children's Wing - Floor 4"},
    {"id": "DR005", "name": "Dr. Layla Ibrahim", "specialty": "General Medicine", "clinic": "Primary Care - Floor 1"},
    {"id": "DR006", "name": "Dr. Yousef Qasim", "specialty": "Cardiology", "clinic": "Heart Center - Floor 3"},
]

_APPOINTMENTS: dict[str, dict] = {
    "APT-1001": {
        "id": "APT-1001",
        "patient_mrn": "MRN-5050",
        "doctor_id": "DR001",
        "doctor_name": "Dr. Sarah Al-Mansoori",
        "specialty": "Cardiology",
        "date": "2026-02-15",
        "time": "10:00",
        "status": "confirmed",
    },
    "APT-1002": {
        "id": "APT-1002",
        "patient_mrn": "MRN-5050",
        "doctor_id": "DR005",
        "doctor_name": "Dr. Layla Ibrahim",
        "specialty": "General Medicine",
        "date": "2026-02-20",
        "time": "14:30",
        "status": "confirmed",
    },
}

_WAITLIST: list[dict] = []


def _generate_slots(doctor_id: str, date: str) -> list[dict]:
    """Generate fake available slots for a doctor on a given date."""
    base = datetime.strptime(date, "%Y-%m-%d")
    slots = []
    for hour in [9, 10, 11, 14, 15, 16]:
        slot_time = base.replace(hour=hour, minute=0)
        time_str = slot_time.strftime("%H:%M")
        conflict = any(
            a["doctor_id"] == doctor_id and a["date"] == date and a["time"] == time_str
            for a in _APPOINTMENTS.values()
            if a["status"] == "confirmed"
        )
        if not conflict:
            slots.append({"date": date, "time": time_str, "available": True})
    return slots


# ── Tools ────────────────────────────────────────────────────────────────────


@tool(approval_mode="never_require")
def search_doctors(
    specialty: Annotated[str, "Medical specialty to search for, e.g. Cardiology, Orthopedics, Dermatology"],
) -> str:
    """Search for doctors by medical specialty. Returns matching doctors with their clinic location."""
    matches = [d for d in _DOCTORS if specialty.lower() in d["specialty"].lower()]
    if not matches:
        return f"No doctors found for specialty '{specialty}'. Available specialties: {', '.join(set(d['specialty'] for d in _DOCTORS))}"
    lines = [f"Found {len(matches)} doctor(s) for {specialty}:"]
    for d in matches:
        lines.append(f"  - {d['name']} (ID: {d['id']}) — {d['clinic']}")
    return "\n".join(lines)


@tool(approval_mode="never_require")
def search_available_slots(
    doctor_id: Annotated[str, "Doctor ID to search slots for, e.g. DR001"],
    date: Annotated[str, "Date to search in YYYY-MM-DD format"],
) -> str:
    """Search for available appointment slots for a specific doctor on a given date."""
    doctor = next((d for d in _DOCTORS if d["id"] == doctor_id), None)
    if not doctor:
        return f"Doctor with ID '{doctor_id}' not found."
    slots = _generate_slots(doctor_id, date)
    if not slots:
        return f"No available slots for {doctor['name']} on {date}."
    lines = [f"Available slots for {doctor['name']} on {date}:"]
    for s in slots:
        lines.append(f"  - {s['time']}")
    return "\n".join(lines)


@tool(approval_mode="never_require")
def book_appointment(
    patient_mrn: Annotated[str, "Patient MRN (Medical Record Number)"],
    doctor_id: Annotated[str, "Doctor ID, e.g. DR001"],
    date: Annotated[str, "Appointment date in YYYY-MM-DD format"],
    time: Annotated[str, "Appointment time in HH:MM format, e.g. 10:00"],
) -> str:
    """Book an appointment for a verified patient with a specific doctor, date, and time."""
    doctor = next((d for d in _DOCTORS if d["id"] == doctor_id), None)
    if not doctor:
        return f"Doctor with ID '{doctor_id}' not found."
    apt_id = f"APT-{uuid.uuid4().hex[:6].upper()}"
    apt = {
        "id": apt_id,
        "patient_mrn": patient_mrn,
        "doctor_id": doctor_id,
        "doctor_name": doctor["name"],
        "specialty": doctor["specialty"],
        "date": date,
        "time": time,
        "status": "confirmed",
    }
    _APPOINTMENTS[apt_id] = apt
    return (
        f"Appointment booked successfully!\n"
        f"  Confirmation: {apt_id}\n"
        f"  Doctor: {doctor['name']} ({doctor['specialty']})\n"
        f"  Date: {date} at {time}\n"
        f"  Location: {doctor['clinic']}"
    )


@tool(approval_mode="never_require")
def reschedule_appointment(
    appointment_id: Annotated[str, "Existing appointment ID, e.g. APT-1001"],
    new_date: Annotated[str, "New date in YYYY-MM-DD format"],
    new_time: Annotated[str, "New time in HH:MM format"],
) -> str:
    """Reschedule an existing appointment to a new date and time."""
    apt = _APPOINTMENTS.get(appointment_id)
    if not apt:
        return f"Appointment '{appointment_id}' not found."
    if apt["status"] == "cancelled":
        return f"Appointment '{appointment_id}' has been cancelled and cannot be rescheduled."
    old_date, old_time = apt["date"], apt["time"]
    apt["date"] = new_date
    apt["time"] = new_time
    return (
        f"Appointment {appointment_id} rescheduled.\n"
        f"  From: {old_date} at {old_time}\n"
        f"  To:   {new_date} at {new_time}\n"
        f"  Doctor: {apt['doctor_name']}"
    )


@tool(approval_mode="never_require")
def cancel_appointment(
    appointment_id: Annotated[str, "Appointment ID to cancel, e.g. APT-1001"],
) -> str:
    """Cancel an existing appointment."""
    apt = _APPOINTMENTS.get(appointment_id)
    if not apt:
        return f"Appointment '{appointment_id}' not found."
    if apt["status"] == "cancelled":
        return f"Appointment '{appointment_id}' is already cancelled."
    apt["status"] = "cancelled"
    return f"Appointment {appointment_id} with {apt['doctor_name']} on {apt['date']} at {apt['time']} has been cancelled."


@tool(approval_mode="never_require")
def get_appointment_history(
    patient_mrn: Annotated[str, "Patient MRN to look up appointment history"],
) -> str:
    """Get appointment history for a patient. Requires patient to be verified first."""
    matches = [a for a in _APPOINTMENTS.values() if a["patient_mrn"] == patient_mrn]
    if not matches:
        return f"No appointments found for patient {patient_mrn}."
    lines = [f"Appointments for patient {patient_mrn}:"]
    for a in sorted(matches, key=lambda x: x["date"]):
        lines.append(f"  - [{a['status'].upper()}] {a['id']}: {a['doctor_name']} on {a['date']} at {a['time']}")
    return "\n".join(lines)


@tool(approval_mode="never_require")
def add_to_waitlist(
    patient_mrn: Annotated[str, "Patient MRN"],
    doctor_id: Annotated[str, "Preferred doctor ID"],
    preferred_dates: Annotated[str, "Comma-separated preferred dates in YYYY-MM-DD format"],
) -> str:
    """Add a patient to the waitlist for a doctor when no suitable slots are available."""
    doctor = next((d for d in _DOCTORS if d["id"] == doctor_id), None)
    if not doctor:
        return f"Doctor with ID '{doctor_id}' not found."
    entry = {
        "id": f"WL-{uuid.uuid4().hex[:6].upper()}",
        "patient_mrn": patient_mrn,
        "doctor_id": doctor_id,
        "doctor_name": doctor["name"],
        "preferred_dates": preferred_dates,
        "status": "waiting",
        "position": len(_WAITLIST) + 1,
    }
    _WAITLIST.append(entry)
    return (
        f"Added to waitlist for {doctor['name']}.\n"
        f"  Waitlist ID: {entry['id']}\n"
        f"  Position: {entry['position']}\n"
        f"  Preferred dates: {preferred_dates}\n"
        f"  We'll notify you when a slot opens up."
    )


@tool(approval_mode="never_require")
def send_sms_confirmation(
    patient_phone: Annotated[str, "Patient phone number to send SMS to"],
    appointment_id: Annotated[str, "Appointment confirmation ID"],
    appointment_details: Annotated[str, "Appointment details: date, time, doctor, location"],
) -> str:
    """Send SMS confirmation to patient after booking an appointment.
    
    In production, this would integrate with an SMS gateway (e.g., Twilio, Azure Communication Services).
    """
    # Mock: In production, this would call SMS API
    masked_phone = f"***-***-{patient_phone[-4:]}" if len(patient_phone) >= 4 else patient_phone
    
    return (
        f"SMS confirmation sent successfully.\n"
        f"  To: {masked_phone}\n"
        f"  Confirmation: {appointment_id}\n"
        f"  Message: Your appointment is confirmed - {appointment_details}"
    )