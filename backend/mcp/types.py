"""MCP (Model Context Protocol) core types and protocol definitions."""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class MCPTransportType(Enum):
    """MCP transport types."""
    STDIO = "stdio"
    HTTP = "http"
    SSE = "sse"
    WEBSOCKET = "websocket"


class MCPMessageType(Enum):
    """MCP message types."""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"


class MCPErrorCode(Enum):
    """MCP standard error codes."""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    SERVER_NOT_INITIALIZED = -32000
    UNKNOWN_ERROR = -32001


@dataclass
class MCPError:
    """MCP error object."""
    code: int
    message: str
    data: Any = None

    def to_dict(self) -> dict[str, Any]:
        result = {"code": self.code, "message": self.message}
        if self.data is not None:
            result["data"] = self.data
        return result


@dataclass
class MCPMessage:
    """Base MCP message."""
    jsonrpc: str = "2.0"
    id: str | int | None = None
    method: str | None = None
    params: dict[str, Any] | None = None
    result: Any = None
    error: MCPError | None = None

    @classmethod
    def request(cls, method: str, params: dict[str, Any] | None = None, id: str | int | None = None) -> "MCPMessage":
        return cls(id=id or str(uuid4()), method=method, params=params)

    @classmethod
    def response(cls, result: Any, id: str | int) -> "MCPMessage":
        return cls(id=id, result=result)

    @classmethod
    def error_response(cls, error: MCPError, id: str | int) -> "MCPMessage":
        return cls(id=id, error=error)

    @classmethod
    def notification(cls, method: str, params: dict[str, Any] | None = None) -> "MCPMessage":
        return cls(method=method, params=params)

    def to_dict(self) -> dict[str, Any]:
        result = {"jsonrpc": self.jsonrpc}
        if self.id is not None:
            result["id"] = self.id
        if self.method is not None:
            result["method"] = self.method
        if self.params is not None:
            result["params"] = self.params
        if self.result is not None:
            result["result"] = self.result
        if self.error is not None:
            result["error"] = self.error.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MCPMessage":
        error = None
        if data.get("error"):
            error = MCPError(**data["error"])
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            id=data.get("id"),
            method=data.get("method"),
            params=data.get("params"),
            result=data.get("result"),
            error=error,
        )


@dataclass
class MCPServerInfo:
    """MCP server information."""
    name: str
    version: str
    protocol_version: str = "2024-11-05"
    capabilities: dict[str, Any] = field(default_factory=dict)
    instructions: str | None = None


@dataclass
class MCPClientInfo:
    """MCP client information."""
    name: str
    version: str
    protocol_version: str = "2024-11-05"
    capabilities: dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPTool:
    """MCP tool definition."""
    name: str
    description: str
    input_schema: dict[str, Any]
    annotations: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }
        if self.annotations:
            result["annotations"] = self.annotations
        return result


@dataclass
class MCPResource:
    """MCP resource definition."""
    uri: str
    name: str
    description: str | None = None
    mime_type: str | None = None
    annotations: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {"uri": self.uri, "name": self.name}
        if self.description:
            result["description"] = self.description
        if self.mime_type:
            result["mimeType"] = self.mime_type
        if self.annotations:
            result["annotations"] = self.annotations
        return result


@dataclass
class MCPResourceContent:
    """MCP resource content."""
    uri: str
    mime_type: str
    text: str | None = None
    blob: bytes | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {"uri": self.uri, "mimeType": self.mime_type}
        if self.text is not None:
            result["text"] = self.text
        if self.blob is not None:
            import base64
            result["blob"] = base64.b64encode(self.blob).decode()
        return result


@dataclass
class MCPPrompt:
    """MCP prompt definition."""
    name: str
    description: str
    arguments: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {"name": self.name, "description": self.description}
        if self.arguments:
            result["arguments"] = self.arguments
        return result


@dataclass
class MCPPromptMessage:
    """MCP prompt message."""
    role: str
    content: MCPResourceContent | str

    def to_dict(self) -> dict[str, Any]:
        if isinstance(self.content, str):
            return {"role": self.role, "content": {"type": "text", "text": self.content}}
        return {"role": self.role, "content": self.content.to_dict()}


@dataclass
class MCPPromptResult:
    """MCP prompt result."""
    description: str
    messages: list[MCPPromptMessage]

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "messages": [m.to_dict() for m in self.messages],
        }


class MCPTransport(ABC):
    """Abstract base class for MCP transports."""

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the transport."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the transport."""

    @abstractmethod
    async def send(self, message: MCPMessage) -> None:
        """Send a message."""

    @abstractmethod
    async def receive(self) -> MCPMessage | None:
        """Receive a message."""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if transport is connected."""

    @property
    @abstractmethod
    def transport_type(self) -> MCPTransportType:
        """Get transport type."""


class MCPServerCapability(ABC):
    """Base class for MCP server capabilities."""

    @property
    @abstractmethod
    def capability_name(self) -> str:
        """Return the capability name."""

    @abstractmethod
    def get_capability_definition(self) -> dict[str, Any]:
        """Get the capability definition for initialization."""

    @abstractmethod
    async def handle_request(self, method: str, params: dict[str, Any]) -> Any:
        """Handle a capability-specific request."""


@dataclass
class MCPConnectionConfig:
    """MCP connection configuration."""
    transport_type: MCPTransportType
    transport_config: dict[str, Any]
    auth_token: str | None = None
    reconnect: bool = True
    reconnect_interval: int = 5
    max_reconnect_attempts: int = 10
    timeout: int = 30


class MCPProtocolVersion:
    """MCP protocol version constants."""
    LATEST = "2024-11-05"
    SUPPORTED = ["2024-11-05", "2024-10-07", "2024-09-01"]


def parse_mcp_message(data: str | bytes) -> MCPMessage | None:
    """Parse raw message data into MCPMessage."""
    try:
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        parsed = json.loads(data)
        return MCPMessage.from_dict(parsed)
    except Exception:
        return None


def serialize_mcp_message(message: MCPMessage) -> str:
    """Serialize MCPMessage to JSON string."""
    return json.dumps(message.to_dict())
