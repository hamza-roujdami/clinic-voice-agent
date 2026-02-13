"""
Agent factory for clinic voice assistant.

Wraps Azure AI Foundry Agent Service v2 with local function tool execution.

Architecture:
    - Agent definition (prompt, tools) stored in Foundry Agent Service
    - Conversations/responses managed via OpenAI-compatible API
    - Function tools execute locally, results sent back to agent
    - Built-in tools (WebSearch, MemorySearch) run server-side in Foundry

Usage:
    async with AgentFactory() as factory:
        result = await factory.run("I need an appointment", session_id="abc")
"
from __future__ import annotations

import json
import logging
import os
from typing import Any

from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import (
    ApproximateLocation,
    FunctionTool,
    MemorySearchTool,
    PromptAgentDefinition,
    WebSearchPreviewTool,
)
from azure.identity.aio import DefaultAzureCredential
from openai.types.responses.response_input_param import FunctionCallOutput

from agents.prompts import TRIAGE_SYSTEM_PROMPT
from tools import HANDOFF_TOOLS, IDENTITY_TOOLS, SCHEDULING_TOOLS

logger = logging.getLogger(__name__)
MEMORY_STORE_NAME = os.environ.get("FOUNDRY_MEMORY_STORE_NAME", "clinic-patient-memory")


class AgentFactory:
    """
    Creates and runs the clinic voice assistant via Foundry Agent Service.
    
    Lifecycle:
        1. __aenter__: Connect to Foundry, register agent definition
        2. run(): Process messages with tool loop
        3. __aexit__: Cleanup connections
    """

    AGENT_NAME = "clinic-voice-agent"
    MAX_TOOL_ITERATIONS = 30  # Prevent infinite tool loops

    def __init__(
        self,
        project_endpoint: str | None = None,
        model: str = "gpt-4o-mini",
    ):
        self._project_endpoint = project_endpoint or os.environ.get("PROJECT_ENDPOINT")
        self._model = model

        self._credential: DefaultAzureCredential | None = None
        self._project_client: AIProjectClient | None = None
        self._openai_client = None
        self._agent_name: str | None = None
        self._agent_version: str | None = None
        self._function_tools: list = []
        self._tool_lookup: dict[str, Any] = {}
        self._sessions: dict[str, dict[str, str]] = {}

    async def __aenter__(self):
        """Initialize clients and create agent."""
        # Initialize Azure clients
        self._credential = DefaultAzureCredential()
        self._project_client = AIProjectClient(
            endpoint=self._project_endpoint,
            credential=self._credential,
        )
        self._openai_client = self._project_client.get_openai_client()

        # Setup tools and agent
        await self._setup_tools()
        await self._create_agent()

        logger.info(f"AgentFactory ready: {self._agent_name} v{self._agent_version}")
        return self

    async def __aexit__(self, *exc):
        if self._openai_client:
            await self._openai_client.close()
        if self._project_client:
            await self._project_client.close()
        if self._credential:
            await self._credential.close()

    async def _setup_tools(self):
        """Prepare function tools for local execution."""
        self._function_tools = [
            *IDENTITY_TOOLS,
            *SCHEDULING_TOOLS,
            *HANDOFF_TOOLS,
        ]
        self._tool_lookup = {
            tool.name: tool
            for tool in self._function_tools
            if hasattr(tool, "name") and hasattr(tool, "invoke")
        }

        logger.info(f"Loaded {len(self._tool_lookup)} tools")

    def _build_agent_tools(self) -> list:
        """Build tool definitions for the agent."""
        tools = []

        for tool in self._function_tools:
            if hasattr(tool, "name") and hasattr(tool, "parameters"):
                tools.append(
                    FunctionTool(
                        name=tool.name,
                        description=tool.description,
                        parameters=tool.parameters,
                        strict=True,
                    )
                )

        # WebSearch: UAE-localized results for clinic info queries
        tools.append(
            WebSearchPreviewTool(
                user_location=ApproximateLocation(
                    country="AE",
                    city="Abu Dhabi",
                    region="Abu Dhabi"
                )
            )
        )

        # MemorySearch: Long-term patient context (preferences, history)
        # Scoped by threadId so conversations don't leak data
        if MEMORY_STORE_NAME:
            tools.append(
                MemorySearchTool(
                    memory_store_name=MEMORY_STORE_NAME,
                    scope="{{$threadId}}",
                    update_delay=30,  # Delay before indexing new content
                )
            )

        return tools

    async def _create_agent(self):
        """Create or update the agent in Foundry Agent Service."""
        tools = self._build_agent_tools()

        logger.info(f"Creating agent: {self.AGENT_NAME}")
        agent = await self._project_client.agents.create_version(
            agent_name=self.AGENT_NAME,
            definition=PromptAgentDefinition(
                model=self._model,
                instructions=TRIAGE_SYSTEM_PROMPT,
                tools=tools,
            ),
        )

        self._agent_name = agent.name
        self._agent_version = agent.version
        logger.info(f"Agent created: {self._agent_name} v{self._agent_version} ({len(tools)} tools)")

    async def _execute_tool(self, name: str, arguments: str) -> str:
        """Execute a function tool and return the result."""
        tool = self._tool_lookup.get(name)
        if not tool:
            logger.warning(f"Unknown tool: {name}")
            return json.dumps({"error": f"Unknown tool: {name}"})

        try:
            args = json.loads(arguments) if arguments else {}
            result = await tool.invoke(**args)
            logger.info(f"Tool executed: {name}")
            return json.dumps(result) if not isinstance(result, str) else result
        except Exception as e:
            logger.error(f"Tool failed: {name} - {e}")
            return json.dumps({"error": str(e)})

    async def _process_function_calls(
        self, response, tools_called: list[str]
    ) -> tuple[Any, bool]:
        """
        Execute function calls and continue the agent loop.
        
        The agent may request multiple tools in one turn. We execute all,
        send results back, and check if agent needs more tools or is done.
        """
        function_calls = [
            item for item in response.output if item.type == "function_call"
        ]

        if not function_calls:
            return response, False

        # Execute all function calls
        outputs = []
        for call in function_calls:
            tools_called.append(call.name)
            result = await self._execute_tool(call.name, call.arguments)
            outputs.append(
                FunctionCallOutput(
                    type="function_call_output",
                    call_id=call.call_id,
                    output=result,
                )
            )

        # Feed tool outputs back to agent for next reasoning step
        new_response = await self._openai_client.responses.create(
            input=outputs,
            previous_response_id=response.id,
            extra_body={"agent": {"name": self._agent_name, "type": "agent_reference"}},
        )

        return new_response, True

    async def _get_or_create_conversation(
        self, session_id: str, message: str | None = None
    ) -> str:
        """Get existing or create new conversation for session."""
        if session_id in self._sessions:
            return self._sessions[session_id]["conv_id"]

        items = []
        if message:
            items.append({"type": "message", "role": "user", "content": message})

        conversation = await self._openai_client.conversations.create(items=items)
        self._sessions[session_id] = {"conv_id": conversation.id, "last_response_id": None}
        logger.info(f"Created conversation: {conversation.id}")
        return conversation.id

    async def run(
        self,
        message: str,
        session_id: str | None = None,
        conversation_id: str | None = None,
    ) -> dict[str, Any]:
        """Run a conversation turn with the agent.

        Args:
            message: User message
            session_id: Session ID for conversation continuity
            conversation_id: Alias for session_id (backwards compat)

        Returns:
            dict with response, conversation_id, tools_called
        """
        if not self._project_client or not self._agent_name:
            raise RuntimeError("AgentFactory not initialized. Use 'async with'.")

        session = session_id or conversation_id or "default"
        tools_called: list[str] = []

        # Get or create conversation
        is_new = session not in self._sessions
        if is_new:
            conv_id = await self._get_or_create_conversation(session, message)
            # First call - use conversation
            response = await self._openai_client.responses.create(
                conversation=conv_id,
                extra_body={"agent": {"name": self._agent_name, "type": "agent_reference"}},
            )
        else:
            # Existing session - use previous_response_id to continue
            session_data = self._sessions[session]
            conv_id = session_data["conv_id"]
            last_response_id = session_data["last_response_id"]
            
            # Add user message and continue from last response
            await self._openai_client.conversations.items.create(
                conversation_id=conv_id,
                items=[{"type": "message", "role": "user", "content": message}],
            )
            response = await self._openai_client.responses.create(
                previous_response_id=last_response_id,
                input=[{"type": "message", "role": "user", "content": message}],
                extra_body={"agent": {"name": self._agent_name, "type": "agent_reference"}},
            )

        # Process function calls
        for _ in range(self.MAX_TOOL_ITERATIONS):
            response, has_more = await self._process_function_calls(
                response, tools_called
            )
            if not has_more:
                break

        # Store last response ID for this session
        self._sessions[session]["last_response_id"] = response.id

        # Extract response
        text = response.output_text if hasattr(response, "output_text") else ""

        return {
            "response": text,
            "conversation_id": session,
            "tools_called": tools_called,
        }

    async def clear_session(self, session_id: str):
        """Delete a session's conversation."""
        if session_id not in self._sessions:
            return

        conv_id = self._sessions[session_id]["conv_id"]
        try:
            await self._openai_client.conversations.delete(conversation_id=conv_id)
            logger.info(f"Deleted conversation: {conv_id}")
        except Exception as e:
            logger.warning(f"Could not delete conversation: {e}")

        del self._sessions[session_id]

