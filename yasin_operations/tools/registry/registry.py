"""Tool registry.

Holds registered tools by ID, without knowing anything about how
each tool is implemented. The registry only deals in
ToolDescriptor/Tool contracts.
"""

from __future__ import annotations

from typing import Optional

from yasin_operations.tools.contracts.tool import Tool, ToolDescriptor


class DuplicateToolError(Exception):
    """Raised when registering a tool ID that is already registered."""

    def __init__(self, tool_id: str):
        self.tool_id = tool_id
        super().__init__(f"Tool already registered: {tool_id!r}")


class ToolNotFoundError(Exception):
    """Raised when looking up or unregistering an unknown tool ID."""

    def __init__(self, tool_id: str):
        self.tool_id = tool_id
        super().__init__(f"No tool registered with id: {tool_id!r}")


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        tool_id = tool.descriptor.id
        if tool_id in self._tools:
            raise DuplicateToolError(tool_id)
        self._tools[tool_id] = tool

    def unregister(self, tool_id: str) -> None:
        if tool_id not in self._tools:
            raise ToolNotFoundError(tool_id)
        del self._tools[tool_id]

    def get(self, tool_id: str) -> Tool:
        try:
            return self._tools[tool_id]
        except KeyError:
            raise ToolNotFoundError(tool_id) from None

    def has(self, tool_id: str) -> bool:
        return tool_id in self._tools

    def list_tools(self) -> tuple[ToolDescriptor, ...]:
        return tuple(tool.descriptor for tool in self._tools.values())

    def find_for_operation(self, operation_name: str) -> tuple[Tool, ...]:
        """Return every registered tool that declares support for operation_name."""
        return tuple(
            tool
            for tool in self._tools.values()
            if tool.descriptor.supports(operation_name)
        )

    def supports(self, operation_name: str) -> bool:
        return len(self.find_for_operation(operation_name)) > 0
