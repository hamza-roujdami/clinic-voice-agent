#!/usr/bin/env python3
"""Automated test for full booking conversation flow.

Usage:
    python test_flow.py              # Test all scenarios
    python test_flow.py booking      # Test booking flow only
    python test_flow.py cancel       # Test cancel flow only
    python test_flow.py handoff      # Test human handoff
    python test_flow.py general      # Test general question

Requires server running: python main.py
"""

import asyncio
import sys
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

BASE_URL = "http://localhost:8000"


async def send_message(client: httpx.AsyncClient, message: str, session_id: str | None = None) -> tuple[str, str, list]:
    """Send a message and return response, session_id, and tools called."""
    payload = {"message": message}
    if session_id:
        payload["session_id"] = session_id
    
    resp = await client.post(f"{BASE_URL}/chat", json=payload)
    data = resp.json()
    
    return data["response"], data["session_id"], data.get("tools_called", [])


async def run_scenario(name: str, messages: list[str], description: str = ""):
    """Run a test scenario with a list of messages."""
    console.print(Panel(f"[bold blue]{name}[/]\n[dim]{description}[/]", border_style="blue"))
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Check server
        try:
            await client.get(f"{BASE_URL}/health")
        except httpx.ConnectError:
            console.print("[red]✗ Server not running. Start with: python main.py[/]")
            return False
        
        session_id = None
        success = True
        
        for i, msg in enumerate(messages, 1):
            # User message
            console.print(f"\n[cyan]You:[/] {msg}")
            
            try:
                response, session_id, tools = await send_message(client, msg, session_id)
                
                # Bot response
                console.print(f"[green]Bot:[/] {response}")
                
                # Tools called (dim)
                if tools:
                    console.print(f"[dim]    → Tools: {', '.join(tools)}[/]")
                    
            except Exception as e:
                console.print(f"[red]Error: {e}[/]")
                success = False
                break
        
        # Summary
        status = "[green]✓ PASSED[/]" if success else "[red]✗ FAILED[/]"
        console.print(f"\n{status}\n")
        return success


async def test_booking_flow():
    """Test complete appointment booking flow."""
    messages = [
        "Hello",
        "I need to see a cardiologist next week",
        "For me",
        "Tuesday would be great",
        "Dr. Al-Mansoori please",
        "Tuesday afternoon",
        "Yes please",
        "My MRN is MRN-5050",
        "The code is 123456",
        "Yes",
        "No that's all",
    ]
    return await run_scenario(
        "Full Booking Flow",
        messages,
        "Book cardiologist appointment → verify identity → SMS confirmation"
    )


async def test_cancel_flow():
    """Test appointment cancellation flow."""
    messages = [
        "I want to cancel my appointment",
        "The one with Dr. Al-Mansoori",
        "MRN-5050",
        "123456",
        "Yes cancel it",
    ]
    return await run_scenario(
        "Cancel Appointment",
        messages,
        "Cancel existing appointment with identity verification"
    )


async def test_reschedule_flow():
    """Test appointment rescheduling flow."""
    messages = [
        "I need to reschedule my appointment",
        "MRN-5050",
        "123456",
        "Move it to Wednesday at 10am",
        "Yes",
    ]
    return await run_scenario(
        "Reschedule Appointment",
        messages,
        "Reschedule existing appointment to new time"
    )


async def test_handoff():
    """Test human handoff."""
    messages = [
        "This is frustrating, let me speak to a real person",
    ]
    return await run_scenario(
        "Human Handoff",
        messages,
        "Escalate to human agent"
    )


async def test_general_question():
    """Test general question (no verification needed)."""
    messages = [
        "What are the visiting hours?",
    ]
    return await run_scenario(
        "General Question",
        messages,
        "Answer using web search (no verification required)"
    )


async def test_direct_doctor():
    """Test booking with specific doctor request."""
    messages = [
        "I want to book with Dr. Khalil",
        "Tomorrow morning",
        "For me",
        "9am works",
        "Yes book it",
        "MRN-5050",
        "123456",
        "No thanks",
    ]
    return await run_scenario(
        "Direct Doctor Request",
        messages,
        "Book with specific doctor by name"
    )


async def main():
    """Run test scenarios."""
    console.print(Panel.fit(
        "[bold]🏥 Clinic Voice Agent - Flow Tests[/]\n"
        "[dim]Automated conversation testing[/]",
        border_style="cyan"
    ))
    console.print()
    
    # Parse args
    scenario = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    results = []
    
    if scenario in ("all", "booking"):
        results.append(("Booking", await test_booking_flow()))
    
    if scenario in ("all", "cancel"):
        results.append(("Cancel", await test_cancel_flow()))
    
    if scenario in ("all", "reschedule"):
        results.append(("Reschedule", await test_reschedule_flow()))
    
    if scenario in ("all", "handoff"):
        results.append(("Handoff", await test_handoff()))
    
    if scenario in ("all", "general"):
        results.append(("General", await test_general_question()))
    
    if scenario in ("all", "doctor"):
        results.append(("Direct Doctor", await test_direct_doctor()))
    
    # Summary table
    if len(results) > 1:
        console.print("\n")
        table = Table(title="Test Results", show_header=True)
        table.add_column("Scenario")
        table.add_column("Result")
        
        for name, passed in results:
            status = "[green]✓ PASSED[/]" if passed else "[red]✗ FAILED[/]"
            table.add_row(name, status)
        
        console.print(table)
        
        passed_count = sum(1 for _, p in results if p)
        total = len(results)
        console.print(f"\n[bold]Total: {passed_count}/{total} passed[/]")


if __name__ == "__main__":
    asyncio.run(main())
