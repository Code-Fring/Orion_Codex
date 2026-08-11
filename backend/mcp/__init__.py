"""MCP (Model Context Protocol) package for Orion Codex."""

from backend.mcp.client import MCPClient
from backend.mcp.server import MCPServer, MCPStdioServer, ToolCapability, ResourceCapability, PromptCapability
from backend.mcp.transports import (
    StdioTransport,
    StdioTransportConfig,
    HTTPTransport,
    SSETransport,
    WebSocketTransport,
)
from backend.mcp.types import (
    MCPMessage,
    MCPTool,
    MCPResource,
    MCPResourceContent,
    MCPPrompt,
    MCPPromptMessage,
    MCPPromptResult,
    MCPServerInfo,
    MCPClientInfo,
    MCPError,
    MCPErrorCode,
    MCPTransportType,
    MCPConnectionConfig,
)

__all__ = [
    "MCPClient",
    "MCPServer",
    "MCPStdioServer",
    "ToolCapability",
    "ResourceCapability",
    "PromptCapability",
    "StdioTransport",
    "StdioTransportConfig",
    "HTTPTransport",
    "SSETransport",
    "WebSocketTransport",
    "MCPMessage",
    "MCPTool",
    "MCPResource",
    "MCPResourceContent",
    "MCPPrompt",
    "MCPPromptMessage",
    "MCPPromptResult",
    "MCPServerInfo",
    "MCPClientInfo",
    "MCPError",
    "MCPErrorCode",
    "MCPTransportType",
    "MCPConnectionConfig",
]