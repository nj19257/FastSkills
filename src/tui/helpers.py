"""Helper utilities for the FastSkills TUI."""

from __future__ import annotations


def mcp_tools_to_openai(mcp_tools: list) -> list[dict]:
    """Convert MCP tool objects to OpenAI-compatible function tool defs."""
    openai_tools = []
    for tool in mcp_tools:
        schema = tool.inputSchema if hasattr(tool, "inputSchema") else {}
        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": schema,
            },
        })
    return openai_tools
