#!/usr/bin/env python3
"""CLI mode for testing Clinic Voice Agent.

Usage:
    python cli.py                    # Interactive mode (calls running server)
    python cli.py --local            # Direct mode (runs agents locally, no server needed)
    python cli.py --session abc123   # Resume existing session

Examples of test scenarios:
    1. Book appointment: "I want to book an appointment with a cardiologist"
    2. Identity verification: Provide MRN and OTP when prompted
    3. Reschedule: "I need to reschedule my appointment"
    4. Cancel: "Cancel my appointment for tomorrow"
"""

import argparse
import asyncio
import sys
import httpx
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.theme import Theme

custom_theme = Theme({
    "user": "bold cyan",
    "agent": "bold green",
    "system": "dim",
    "error": "bold red",
    "info": "dim cyan",
})

console = Console(theme=custom_theme)


async def run_server_mode(session_id: str | None = None, base_url: str = "http://localhost:8000"):
    """Interactive CLI that calls the running server."""
    
    console.print(Panel.fit(
        "[bold blue]🏥 Clinic Voice Agent CLI[/]\n"
        "[dim]Type your messages below. Commands: /new, /session, /quit[/]",
        border_style="blue"
    ))
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Check server health
        try:
            resp = await client.get(f"{base_url}/health")
            data = resp.json()
            if data.get("factory_initialized"):
                console.print("[info]✓ Connected to server[/]")
            else:
                console.print("[error]⚠ Server running but AI backend not initialized[/]")
        except httpx.ConnectError:
            console.print(f"[error]✗ Cannot connect to {base_url}. Is the server running?[/]")
            console.print("[info]Start with: python main.py[/]")
            return
        
        current_session = session_id
        if current_session:
            console.print(f"[info]Resuming session: {current_session}[/]")
        
        console.print()
        
        while True:
            try:
                user_input = Prompt.ask("[user]You[/]")
            except (KeyboardInterrupt, EOFError):
                console.print("\n[system]Goodbye![/]")
                break
            
            if not user_input.strip():
                continue
            
            # Handle commands
            if user_input.strip().lower() == "/quit":
                console.print("[system]Goodbye![/]")
                break
            elif user_input.strip().lower() == "/new":
                current_session = None
                console.print("[system]New session started[/]")
                continue
            elif user_input.strip().lower() == "/session":
                if current_session:
                    console.print(f"[info]Session ID: {current_session}[/]")
                else:
                    console.print("[info]No active session yet[/]")
                continue
            elif user_input.strip().lower() == "/help":
                console.print("[system]Commands: /new (new session), /session (show ID), /quit (exit)[/]")
                continue
            
            # Send message to server
            payload = {"message": user_input}
            if current_session:
                payload["session_id"] = current_session
            
            try:
                with console.status("[dim]Agent thinking...[/]", spinner="dots"):
                    resp = await client.post(f"{base_url}/chat", json=payload)
                
                if resp.status_code != 200:
                    console.print(f"[error]Error: {resp.text}[/]")
                    continue
                
                data = resp.json()
                current_session = data.get("session_id")
                agent = data.get("agent", "Agent")
                response = data.get("response", "")
                
                # Show handoff if any
                if data.get("handoff_from") and data.get("handoff_to"):
                    console.print(f"[system]🔄 {data['handoff_from']} → {data['handoff_to']}[/]")
                
                # Display agent response
                agent_label = agent.replace("_", " ").title() if agent else "Agent"
                console.print(f"[agent]{agent_label}[/]: {response}")
                console.print()
                
            except httpx.TimeoutException:
                console.print("[error]Request timed out. The server may be overloaded.[/]")
            except Exception as e:
                console.print(f"[error]Error: {e}[/]")


async def run_local_mode():
    """Run agents directly without a server."""
    
    console.print(Panel.fit(
        "[bold blue]🏥 Clinic Voice Agent CLI (Local Mode)[/]\n"
        "[dim]Running agents directly. Type your messages below.[/]",
        border_style="blue"
    ))
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        from config import config
        from agents.factory import AgentFactory
    except ImportError as e:
        console.print(f"[error]Missing dependency: {e}[/]")
        console.print("[info]Install with: pip install -r requirements.txt[/]")
        return
    
    # Validate config
    missing = config.validate()
    if missing:
        console.print(f"[error]Missing config: {', '.join(missing)}[/]")
        console.print("[info]Copy .env.example to .env and configure[/]")
        return
    
    console.print("[info]Initializing agents...[/]")
    
    async with AgentFactory(
        project_endpoint=config.project_endpoint,
        model=config.model_primary,
    ) as factory:
        console.print("[info]✓ Agent factory ready[/]")
        
        session_id = None
        
        while True:
            try:
                user_input = Prompt.ask("[user]You[/]")
            except (KeyboardInterrupt, EOFError):
                console.print("\n[system]Goodbye![/]")
                break
            
            if not user_input.strip():
                continue
            
            if user_input.strip().lower() == "/quit":
                console.print("[system]Goodbye![/]")
                break
            elif user_input.strip().lower() == "/new":
                if session_id:
                    await factory.clear_session(session_id)
                session_id = None
                console.print("[system]New session started[/]")
                continue
            elif user_input.strip().lower() == "/session":
                if session_id:
                    console.print(f"[info]Session ID: {session_id}[/]")
                else:
                    console.print("[info]No active session yet[/]")
                continue
            elif user_input.strip().lower() == "/help":
                console.print("[system]Commands: /new (new session), /session (show ID), /quit (exit)[/]")
                continue
            
            try:
                with console.status("[dim]Agent thinking...[/]", spinner="dots"):
                    result = await factory.run(user_input, session_id=session_id)
                
                session_id = result.get("conversation_id")
                response = result.get("response", "(No response)")
                tools = result.get("tools_called", [])
                
                # Show tools used if any
                if tools:
                    console.print(f"[system]🔧 Tools: {', '.join(tools)}[/]")
                
                # Display agent response
                console.print(f"[agent]Agent[/]: {response}")
                console.print()
                
            except Exception as e:
                console.print(f"[error]Error: {e}[/]")
                import traceback
                console.print(f"[dim]{traceback.format_exc()}[/]")


def main():
    parser = argparse.ArgumentParser(
        description="CLI for Clinic Voice Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py                     Interactive mode (requires running server)
  python cli.py --local             Direct mode (no server needed)
  python cli.py --session abc123    Resume existing session
  python cli.py --url http://...    Use custom server URL

Test Scenarios:
  1. "I want to book an appointment with a cardiologist"
  2. "My MRN is MRN-5001"
  3. "The OTP is 123456"
  4. "I need Dr. Ahmed on Tuesday morning"
        """
    )
    parser.add_argument("--local", action="store_true", help="Run agents locally (no server)")
    parser.add_argument("--session", type=str, help="Resume existing session ID")
    parser.add_argument("--url", type=str, default="http://localhost:8000", help="Server URL")
    
    args = parser.parse_args()
    
    try:
        if args.local:
            asyncio.run(run_local_mode())
        else:
            asyncio.run(run_server_mode(session_id=args.session, base_url=args.url))
    except KeyboardInterrupt:
        console.print("\n[system]Interrupted[/]")


if __name__ == "__main__":
    main()
