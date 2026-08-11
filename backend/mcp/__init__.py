"""MCP (Model Context Protocol) package for Orion Codex."""

from backend.mcp.client import MCPClient
from backend.mcp.server import MCPServer, MCPStdioServer, PromptCapability, ResourceCapability, ToolCapability
from backend.mcp.transports import (
    HTTPTransport,
    SSETransport,
    StdioTransport,
    StdioTransportConfig,
    WebSocketTransport,
)
from backend.mcp.types import (
    MCPClientInfo,
    MCPConnectionConfig,
    MCPError,
    MCPErrorCode,
    MCPMessage,
    MCPPrompt,
    MCPPromptMessage,
    MCPPromptResult,
    MCPResource,
    MCPResourceContent,
    MCPServerInfo,
    MCPTool,
    MCPTransportType,
)

__all__ = [
    "HTTPTransport",
    "MCPClient",
    "MCPClientInfo",
    "MCPConnectionConfig",
    "MCPError",
    "MCPErrorCode",
    "MCPMessage",
    "MCPPrompt",
    "MCPPromptMessage",
    "MCPPromptResult",
    "MCPResource",
    "MCPResourceContent",
    "MCPServer",
    "MCPServerInfo",
    "MCPStdioServer",
    "MCPTool",
    "MCPTransportType",
    "PromptCapability",
    "ResourceCapability",
    "SSETransport",
    "StdioTransport",
    "StdioTransportConfig",
    "ToolCapability",
    "WebSocketTransport",
]
