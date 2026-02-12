"""Simple tool decorator

Creates FunctionTool-like objects with name, invoke, and definition properties.
"""

import asyncio
import inspect
from functools import wraps
from typing import Any, Callable, get_type_hints


class FunctionToolWrapper:
    """Wrapper that provides name, invoke, and definition for a function."""

    def __init__(self, func: Callable, approval_mode: str = "never_require"):
        self._func = func
        self.name = func.__name__
        self.description = func.__doc__ or ""
        self._approval_mode = approval_mode
        self._schema = self._generate_schema()

    def _generate_schema(self) -> dict:
        """Generate JSON schema from function signature."""
        sig = inspect.signature(self._func)
        hints = get_type_hints(self._func, include_extras=True)
        
        properties = {}
        required = []
        
        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue
            
            param_type = hints.get(param_name, str)
            param_schema = {"type": "string"}  # Default to string
            
            # Extract Annotated metadata for description
            if hasattr(param_type, "__metadata__"):
                for meta in param_type.__metadata__:
                    if isinstance(meta, str):
                        param_schema["description"] = meta
                        break
                # Get the actual type from Annotated
                param_type = param_type.__origin__ if hasattr(param_type, "__origin__") else str
            
            # Map Python types to JSON schema types
            origin = getattr(param_type, "__origin__", param_type)
            if origin in (str, type(None)):
                param_schema["type"] = "string"
            elif origin in (int,):
                param_schema["type"] = "integer"
            elif origin in (float,):
                param_schema["type"] = "number"
            elif origin in (bool,):
                param_schema["type"] = "boolean"
            elif origin in (list,):
                param_schema["type"] = "array"
            elif origin in (dict,):
                param_schema["type"] = "object"
            
            properties[param_name] = param_schema
            
            # With strict mode (additionalProperties: false), OpenAI requires 
            # ALL properties to be in required array - even those with defaults
            required.append(param_name)
        
        return {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,  # Strict mode compliance
        }

    @property
    def parameters(self) -> dict:
        """Return parameters schema for SDK FunctionTool."""
        return self._schema

    @property
    def definition(self) -> dict:
        """Return tool definition for agent registration."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description.strip().split("\n")[0],  # First line
                "parameters": self._schema,
            },
        }

    async def invoke(self, **kwargs) -> Any:
        """Invoke the wrapped function."""
        if asyncio.iscoroutinefunction(self._func):
            return await self._func(**kwargs)
        return self._func(**kwargs)

    def __call__(self, *args, **kwargs):
        """Allow direct function calls for testing."""
        return self._func(*args, **kwargs)


def tool(approval_mode: str = "never_require") -> Callable:
    """Decorator to create a FunctionTool-like wrapper.
    
    Args:
        approval_mode: Ignored, kept for compatibility with agent_framework.
    
    Returns:
        FunctionToolWrapper with name, invoke, and definition properties.
    """
    def decorator(func: Callable) -> FunctionToolWrapper:
        return FunctionToolWrapper(func, approval_mode)
    return decorator
