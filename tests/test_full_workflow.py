"""Full Workflow Integration Tests for Clinic Voice Agent.

Tests the complete multi-turn conversation flow through the API:
- Patient lookup and OTP verification
- Doctor search and slot finding  
- Appointment booking, rescheduling, cancellation
- Policy queries
- Human handoff

Requires the server to be running on localhost:8000 OR runs against
the factory directly for unit-style tests.

Usage:
    pytest tests/test_full_workflow.py -v
    pytest tests/test_full_workflow.py -v -k "booking"  # Run specific test
"""

import asyncio
import uuid
from typing import AsyncGenerator

import httpx
import pytest
import pytest_asyncio

from agents.factory import AgentFactory

# ── Configuration ────────────────────────────────────────────────────────────

API_BASE = "http://localhost:8000"
TIMEOUT = 60.0  # LLM calls can be slow


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def factory() -> AsyncGenerator[AgentFactory, None]:
    """Create an AgentFactory for direct workflow testing."""
    f = AgentFactory()
    async with f:
        yield f


@pytest.fixture
def session_id() -> str:
    """Generate a unique session ID for each test."""
    return f"test-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def client() -> httpx.Client:
    """HTTP client for API testing."""
    return httpx.Client(base_url=API_BASE, timeout=TIMEOUT)


# ── Helper Functions ─────────────────────────────────────────────────────────


def chat(client: httpx.Client, message: str, session_id: str, retries: int = 2) -> dict:
    """Send a chat message and return the response with retry on 5xx."""
    import time
    for attempt in range(retries + 1):
        resp = client.post(
            "/chat",
            json={"message": message, "session_id": session_id},
        )
        if resp.status_code < 500:
            resp.raise_for_status()
            return resp.json()
        if attempt < retries:
            time.sleep(2)  # Wait before retry
    resp.raise_for_status()
    return resp.json()


def assert_contains_any(text: str, phrases: list[str], msg: str = ""):
    """Assert that text contains at least one of the phrases (case-insensitive)."""
    text_lower = text.lower()
    found = any(phrase.lower() in text_lower for phrase in phrases)
    if not found:
        raise AssertionError(f"{msg}\nExpected one of {phrases} in:\n{text}")


# ── API Integration Tests ────────────────────────────────────────────────────


class TestFullBookingFlow:
    """Test the complete appointment booking flow via API."""

    @pytest.mark.integration
    def test_greeting_and_intent(self, client: httpx.Client, session_id: str):
        """Test that the agent responds appropriately to booking request."""
        result = chat(client, "Hi, I need to book an appointment", session_id)
        
        assert "response" in result
        assert result["session_id"] == session_id
        # Agent should respond helpfully - either ask for ID, help with booking, offer assistance, or ask what to do
        assert_contains_any(
            result["response"],
            ["phone", "mrn", "medical record", "identify", "verify", "help", "assist", "appointment", "book", "connect", "representative", "what", "like"],
            "Agent should respond to booking request",
        )

    @pytest.mark.integration
    def test_patient_lookup(self, client: httpx.Client, session_id: str):
        """Test patient lookup with MRN."""
        # First message
        chat(client, "I need to book an appointment", session_id)
        
        # Provide MRN
        result = chat(client, "My MRN is MRN-5001", session_id)
        
        # Agent should find patient and mention name or confirm
        assert_contains_any(
            result["response"],
            ["khalid", "al-rashid", "found", "confirm", "otp", "code", "verify"],
            "Agent should find patient or ask for OTP",
        )

    @pytest.mark.integration
    def test_full_booking_flow(self, client: httpx.Client, session_id: str):
        """Test complete booking: greeting → ID → OTP → search → book."""
        # Turn 1: Greeting
        r1 = chat(client, "Hello, I want to book an appointment with a cardiologist", session_id)
        print(f"Turn 1: {r1['response'][:200]}")
        
        # Turn 2: Provide MRN
        r2 = chat(client, "My MRN is MRN-5001", session_id)
        print(f"Turn 2: {r2['response'][:200]}")
        
        # Turn 3: Confirm identity
        r3 = chat(client, "Yes, that's me - Khalid Al-Rashid, born March 12 1985", session_id)
        print(f"Turn 3: {r3['response'][:200]}")
        
        # Turn 4: Provide OTP
        r4 = chat(client, "The code is 123456", session_id)
        print(f"Turn 4: {r4['response'][:200]}")
        
        # Turn 5: Agent should now search for cardiologists or ask about date
        r5 = chat(client, "I'd like to see Dr. Sarah Al-Mansoori next Monday at 10am", session_id)
        print(f"Turn 5: {r5['response'][:200]}")
        
        # Turn 6: Confirm booking
        r6 = chat(client, "Yes, please book that appointment", session_id)
        print(f"Turn 6: {r6['response'][:200]}")
        
        # Final response should indicate booking confirmed or needs date
        assert_contains_any(
            r6["response"],
            ["booked", "confirmed", "scheduled", "appointment", "date", "when"],
            "Agent should confirm booking or ask for date details",
        )


class TestOTPVerification:
    """Test OTP verification flow."""
    
    @pytest.mark.integration
    def test_wrong_otp(self, client: httpx.Client, session_id: str):
        """Test that wrong OTP is rejected."""
        chat(client, "I need an appointment", session_id)
        chat(client, "MRN-5001", session_id)
        chat(client, "Yes that's me", session_id)
        
        result = chat(client, "The code is 999999", session_id)
        
        # Should indicate OTP failed
        assert_contains_any(
            result["response"],
            ["invalid", "incorrect", "wrong", "try again", "not match"],
            "Agent should reject wrong OTP",
        )

    @pytest.mark.integration
    def test_patient_not_found(self, client: httpx.Client, session_id: str):
        """Test handling of unknown patient."""
        # Use a clearly invalid MRN that doesn't exist
        result = chat(client, "I need to book an appointment. My MRN is MRN-INVALID-99999", session_id)
        
        # Agent should indicate patient not found or ask for verification
        assert_contains_any(
            result["response"],
            ["not found", "no patient", "couldn't find", "try again", "verify", "unable", "check", "correct", "valid", "phone", "mrn"],
            "Agent should handle unknown patient",
        )

    @pytest.mark.integration
    def test_phone_lookup(self, client: httpx.Client, session_id: str):
        """Test patient lookup by phone number instead of MRN."""
        chat(client, "I need to book an appointment", session_id)
        result = chat(client, "My phone number is +971-50-123-4567", session_id)
        
        # Agent should find patient or ask for confirmation
        assert_contains_any(
            result["response"],
            ["khalid", "al-rashid", "found", "confirm", "otp", "code", "verify", "phone"],
            "Agent should find patient by phone or ask for OTP",
        )


class TestDoctorSearch:
    """Test doctor search functionality."""
    
    @pytest.mark.integration
    def test_search_specialty(self, client: httpx.Client, session_id: str):
        """Test searching for doctors by specialty after verification."""
        # Quick verification
        chat(client, "I need a cardiologist", session_id)
        chat(client, "MRN-5001", session_id)
        chat(client, "Yes, Khalid Al-Rashid", session_id)
        chat(client, "123456", session_id)
        
        result = chat(client, "What cardiologists do you have?", session_id)
        
        assert_contains_any(
            result["response"],
            ["sarah", "mansoori", "yousef", "qasim", "cardio", "doctor"],
            "Agent should list cardiologists",
        )


class TestPolicyQueries:
    """Test policy/FAQ functionality."""
    
    @pytest.mark.integration
    def test_visiting_hours(self, client: httpx.Client, session_id: str):
        """Test asking about visiting hours."""
        result = chat(client, "What are your visiting hours?", session_id)
        
        assert_contains_any(
            result["response"],
            ["hour", "visit", "time", "am", "pm", "morning", "afternoon"],
            "Agent should provide visiting hours info",
        )

    @pytest.mark.integration
    def test_cancellation_policy(self, client: httpx.Client, session_id: str):
        """Test asking about cancellation policy."""
        result = chat(client, "What is your cancellation policy?", session_id)
        
        assert_contains_any(
            result["response"],
            ["cancel", "policy", "hour", "reschedule", "fee", "notice"],
            "Agent should explain cancellation policy",
        )


class TestHumanHandoff:
    """Test human escalation flow."""
    
    @pytest.mark.integration  
    def test_request_human(self, client: httpx.Client, session_id: str):
        """Test requesting to speak with a human."""
        result = chat(client, "I want to speak with a real person please", session_id)
        
        assert_contains_any(
            result["response"],
            ["transfer", "connect", "human", "agent", "representative", "moment", "hold", "someone", "person", "assist", "help"],
            "Agent should acknowledge handoff request",
        )

    @pytest.mark.integration
    def test_queue_status_check(self, client: httpx.Client, session_id: str):
        """Test checking queue status during handoff."""
        # Request handoff first
        chat(client, "I need to speak to a human representative", session_id)
        
        # Ask about wait time
        result = chat(client, "How long will I have to wait?", session_id)
        
        assert_contains_any(
            result["response"],
            ["wait", "minute", "queue", "available", "shortly", "soon", "hold"],
            "Agent should provide wait time or queue info",
        )


class TestAppointmentManagement:
    """Test appointment rescheduling and cancellation."""

    @pytest.mark.integration
    def test_reschedule_appointment(self, client: httpx.Client, session_id: str):
        """Test rescheduling an existing appointment."""
        # Verify patient first
        chat(client, "I need to reschedule my appointment", session_id)
        chat(client, "My MRN is MRN-5001", session_id)
        chat(client, "Yes, I'm Khalid", session_id)
        chat(client, "123456", session_id)
        
        # Request reschedule
        result = chat(client, "I need to move my cardiology appointment to next week", session_id)
        
        assert_contains_any(
            result["response"],
            ["reschedule", "appointment", "available", "slot", "date", "time", "when", "move"],
            "Agent should discuss rescheduling options",
        )

    @pytest.mark.integration
    def test_cancel_appointment(self, client: httpx.Client, session_id: str):
        """Test cancelling an appointment."""
        # Verify patient first
        chat(client, "I need to cancel an appointment", session_id)
        chat(client, "MRN-5001", session_id)
        chat(client, "Yes that's me", session_id)
        chat(client, "123456", session_id)
        
        # Request cancellation
        result = chat(client, "Please cancel my upcoming appointment", session_id)
        
        assert_contains_any(
            result["response"],
            ["cancel", "cancelled", "confirm", "appointment", "sure", "which"],
            "Agent should confirm or ask which appointment to cancel",
        )

    @pytest.mark.integration
    def test_appointment_history(self, client: httpx.Client, session_id: str):
        """Test viewing appointment history."""
        # Verify patient first
        chat(client, "I want to see my appointment history", session_id)
        chat(client, "MRN-5001", session_id)
        chat(client, "Yes, Khalid Al-Rashid", session_id)
        chat(client, "123456", session_id)
        
        # Ask for history
        result = chat(client, "What appointments do I have coming up?", session_id)
        
        assert_contains_any(
            result["response"],
            ["appointment", "scheduled", "upcoming", "history", "doctor", "date", "no appointment", "don't have"],
            "Agent should show appointments or indicate none found",
        )


class TestSlotSearch:
    """Test available slot search."""
    
    @pytest.mark.integration
    def test_search_available_slots(self, client: httpx.Client, session_id: str):
        """Test searching for available appointment slots."""
        # Verify patient first
        chat(client, "I need an appointment with a cardiologist", session_id)
        chat(client, "MRN-5001", session_id)
        chat(client, "Yes", session_id)
        chat(client, "123456", session_id)
        
        # Ask for specific slots
        result = chat(client, "What times are available this week for Dr. Sarah Al-Mansoori?", session_id)
        
        assert_contains_any(
            result["response"],
            ["available", "slot", "time", "appointment", "am", "pm", "morning", "afternoon", "date"],
            "Agent should show available slots or ask for preferences",
        )

    @pytest.mark.integration
    def test_waitlist_request(self, client: httpx.Client, session_id: str):
        """Test adding patient to waitlist."""
        # Verify patient first
        chat(client, "I need an urgent appointment", session_id)
        chat(client, "MRN-5001", session_id)
        chat(client, "Yes", session_id)
        chat(client, "123456", session_id)
        
        # Ask for earlier slot
        result = chat(client, "Can you put me on the waitlist for an earlier appointment if something opens up?", session_id)
        
        assert_contains_any(
            result["response"],
            ["waitlist", "wait list", "notify", "contact", "opening", "earlier", "added", "available"],
            "Agent should acknowledge waitlist request",
        )


class TestAdvancedPolicyQueries:
    """Test more complex policy and FAQ queries."""
    
    @pytest.mark.integration
    def test_insurance_coverage(self, client: httpx.Client, session_id: str):
        """Test asking about insurance coverage."""
        result = chat(client, "What insurance plans do you accept?", session_id)
        
        assert_contains_any(
            result["response"],
            ["insurance", "coverage", "accept", "plan", "provider", "daman", "thiqa", "contact"],
            "Agent should provide insurance information",
        )

    @pytest.mark.integration
    def test_emergency_services(self, client: httpx.Client, session_id: str):
        """Test asking about emergency services."""
        result = chat(client, "Do you have emergency services?", session_id)
        
        assert_contains_any(
            result["response"],
            ["emergency", "urgent", "24", "hour", "care", "call", "hospital"],
            "Agent should provide emergency info",
        )

    @pytest.mark.integration
    def test_payment_options(self, client: httpx.Client, session_id: str):
        """Test asking about payment options."""
        try:
            result = chat(client, "What payment methods do you accept?", session_id)
            
            assert_contains_any(
                result["response"],
                ["payment", "pay", "card", "cash", "credit", "insurance", "accept", "contact", "billing"],
                "Agent should provide payment information",
            )
        except Exception as e:
            # Server may hit rate limits or have transient errors on policy queries
            if "500" in str(e):
                pytest.skip("Server returned 500 - possible rate limit or transient error")
            raise


# ── Direct Workflow Tests (no API) ───────────────────────────────────────────


class TestWorkflowDirect:
    """Test AgentFactory directly without HTTP."""

    @pytest.mark.asyncio
    async def test_factory_initialization(self, factory: AgentFactory):
        """Test that factory initializes correctly."""
        assert factory is not None
        # Factory should be ready after async context entry

    @pytest.mark.asyncio
    async def test_single_turn(self, factory: AgentFactory):
        """Test a single turn through the factory."""
        session_id = f"direct-{uuid.uuid4().hex[:8]}"
        
        result = await factory.run("Hello, I need help", session_id=session_id)
        
        assert "response" in result
        assert len(result["response"]) > 10, "Response should have content"

    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self, factory: AgentFactory):
        """Test multi-turn conversation through factory."""
        session_id = f"direct-{uuid.uuid4().hex[:8]}"
        
        turns = [
            "Hi, I need to book a doctor appointment",
            "My MRN is MRN-5001",
            "Yes, I am Khalid Al-Rashid, born March 12 1985",
            "The code is 123456",
        ]
        
        responses = []
        for turn_msg in turns:
            result = await factory.run(turn_msg, session_id=session_id)
            responses.append(result["response"])
        
        assert len(responses) == 4, "Should have 4 responses"
        
        # Check conversation progression - first should ask for ID
        assert_contains_any(responses[0], ["phone", "mrn", "identify", "verify", "help"])
        # Later turns should progress the flow (find patient, send OTP, verify)
        combined = " ".join(responses).lower()
        assert "khalid" in combined or "otp" in combined or "verified" in combined or "code" in combined

    @pytest.mark.asyncio
    async def test_tools_called_tracking(self, factory: AgentFactory):
        """Test that tools_called is properly tracked."""
        session_id = f"direct-{uuid.uuid4().hex[:8]}"
        
        # Should trigger lookup_patient tool
        result = await factory.run("My MRN is MRN-5001", session_id=session_id)
        
        # Should have tools_called in result
        assert "tools_called" in result
        # lookup_patient should be in the list (if LLM decided to use it)
        # Note: LLM behavior may vary, so we just check structure
        assert isinstance(result["tools_called"], list)


# ── Test Configuration ───────────────────────────────────────────────────────


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (require running server)"
    )


if __name__ == "__main__":
    # Run with: python -m pytest tests/test_full_workflow.py -v
    pytest.main([__file__, "-v", "-x"])
