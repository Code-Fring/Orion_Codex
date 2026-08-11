"""MCP Server implementation for exposing Orion capabilities."""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from backend.mcp.transports import MCPTransport
from backend.mcp.types import (
    MCPClientInfo,
    MCPError,
    MCPErrorCode,
    MCPPrompt,
    MCPPromptResult,
    MCPResource,
    MCPResourceContent,
    MCPServerInfo,
    MCPTool,
)

logger = logging.getLogger(__name__)


@dataclass
class MCPToolHandler:
    """Handler for an MCP tool."""
    tool: MCPTool
    handler: Callable[[dict], Any]


@dataclass
class MCPResourceHandler:
    """Handler for an MCP resource."""
    resource: MCPResource
    handler: Callable[[str], MCPResourceContent | list[MCPResourceContent]]


@dataclass
class MCPPromptHandler:
    """Handler for an MCP prompt."""
    prompt: MCPPrompt
    handler: Callable[[dict], MCPPromptResult]


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


class ToolCapability(MCPServerCapability):
    """Tools capability for MCP server."""

    def __init__(self) -> None:
        self._tools: dict[str, MCPToolHandler] = {}

    @property
    def capability_name(self) -> str:
        return "tools"

    def get_capability_definition(self) -> dict[str, Any]:
        return {"tools": {"listChanged": True}}

    def register_tool(self, tool: MCPTool, handler: Callable[[dict], Any]) -> None:
        """Register a tool with its handler."""
        self._tools[tool.name] = MCPToolHandler(tool=tool, handler=handler)

    def unregister_tool(self, name: str) -> bool:
        """Unregister a tool."""
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def get_tools(self) -> list[MCPTool]:
        """Get all registered tools."""
        return [h.tool for h in self._tools.values()]

    async def handle_request(self, method: str, params: dict[str, Any]) -> Any:
        """Handle tool-related requests."""
        if method == "tools/list":
            return {"tools": [t.to_dict() for t in self.get_tools()]}

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            handler = self._tools.get(tool_name)
            if not handler:
                raise MCPError(MCPErrorCode.METHOD_NOT_FOUND, f"Tool not found: {tool_name}")

            try:
                result = await handler.handler(arguments)
                return {"content": [{"type": "text", "text": str(result)}], "isError": False}
            except Exception as e:
                logger.error(f"Tool {tool_name} error: {e}")
                return {"content": [{"type": "text", "text": str(e)}], "isError": True}

        raise MCPError(MCPErrorCode.METHOD_NOT_FOUND, f"Unknown method: {method}")


class ResourceCapability(MCPServerCapability):
    """Resources capability for MCP server."""

    def __init__(self) -> None:
        self._resources: dict[str, MCPResourceHandler] = {}

    @property
    def capability_name(self) -> str:
        return "resources"

    def get_capability_definition(self) -> dict[str, Any]:
        return {"resources": {"subscribe": True, "listChanged": True}}

    def register_resource(
        self,
        resource: MCPResource,
        handler: Callable[[str], MCPResourceContent | list[MCPResourceContent]],
    ) -> None:
        """Register a resource with its handler."""
        self._resources[resource.uri] = MCPResourceHandler(resource=resource, handler=handler)

    def unregister_resource(self, uri: str) -> bool:
        """Unregister a resource."""
        if uri in self._resources:
            del self._resources[uri]
            return True
        return False

    def get_resources(self) -> list[MCPResource]:
        """Get all registered resources."""
        return [h.resource for h in self._resources.values()]

    async def handle_request(self, method: str, params: dict[str, Any]) -> Any:
        """Handle resource-related requests."""
        if method == "resources/list":
            return {"resources": [r.to_dict() for r in self.get_resources()]}

        elif method == "resources/read":
            uri = params.get("uri")
            handler = self._resources.get(uri)
            if not handler:
                raise MCPError(MCPErrorCode.METHOD_NOT_FOUND, f"Resource not found: {uri}")

            try:
                result = await handler.handler(uri)
                if isinstance(result, list):
                    return {"contents": [c.to_dict() for c in result]}
                return {"contents": [result.to_dict()]}
            except Exception as e:
                logger.error(f"Resource {uri} error: {e}")
                raise MCPError(MCPErrorCode.INTERNAL_ERROR, str(e))

        elif method == "resources/subscribe":
            # Subscription handling (simplified)
            return {"result": "subscribed"}

        elif method == "resources/unsubscribe":
            return {"result": "unsubscribed"}

        raise MCPError(MCPErrorCode.METHOD_NOT_FOUND, f"Unknown method: {method}")


class PromptCapability(MCPServerCapability):
    """Prompts capability for MCP server."""

    def __init__(self) -> None:
        self._prompts: dict[str, MCPPromptHandler] = {}

    @property
    def capability_name(self) -> str:
        return "prompts"

    def get_capability_definition(self) -> dict[str, Any]:
        return {"prompts": {"listChanged": True}}

    def register_prompt(self, prompt: MCPPrompt, handler: Callable[[dict], MCPPromptResult]) -> None:
        """Register a prompt with its handler."""
        self._prompts[prompt.name] = MCPPromptHandler(prompt=prompt, handler=handler)

    def unregister_prompt(self, name: str) -> bool:
        """Unregister a prompt."""
        if name in self._prompts:
            del self._prompts[name]
            return True
        return False

    def get_prompts(self) -> list[MCPPrompt]:
        """Get all registered prompts."""
        return [h.prompt for h in self._prompts.values()]

    async def handle_request(self, method: str, params: dict[str, Any]) -> Any:
        """Handle prompt-related requests."""
        if method == "prompts/list":
            return {"prompts": [p.to_dict() for p in self.get_prompts()]}

        elif method == "prompts/get":
            name = params.get("name")
            arguments = params.get("arguments", {})
            handler = self._prompts.get(name)
            if not handler:
                raise MCPError(MCPErrorCode.METHOD_NOT_FOUND, f"Prompt not found: {name}")

            try:
                result = await handler.handler(arguments)
                return result.to_dict()
            except Exception as e:
                logger.error(f"Prompt {name} error: {e}")
                raise MCPError(MCPErrorCode.INTERNAL_ERROR, str(e))

        raise MCPError(MCPErrorCode.METHOD_NOT_FOUND, f"Unknown method: {method}")


class MCPServer:
    """MCP Server for exposing Orion capabilities."""

    def __init__(
        self,
        name: str = "Orion Codex",
        version: str = "0.1.0",
        instructions: str | None = None,
    ) -> None:
        self.server_info = MCPServerInfo(
            name=name,
            version=version,
            instructions=instructions,
        )
        self._capabilities: dict[str, MCPServerCapability] = {}
        self._transports: dict[str, MCPTransport] = {}
        self._initialized = False
        self._client_info: MCPClientInfo | None = None
        self._request_handlers: dict[str, Callable] = {}

        # Register core capabilities
        self._tool_capability = ToolCapability()
        self._resource_capability = ResourceCapability()
        self._prompt_capability = PromptCapability()

        self._capabilities["tools"] = self._tool_capability
        self._capabilities["resources"] = self._resource_capability
        self._capabilities["prompts"] = self._prompt_capability

        # Register core request handlers
        self._register_core_handlers()

    def _register_core_handlers(self) -> None:
        """Register core MCP request handlers."""
        self._request_handlers["initialize"] = self._handle_initialize
        self._request_handlers["ping"] = self._handle_ping

    @property
    def tool_capability(self) -> ToolCapability:
        return self._tool_capability

    @property
    def resource_capability(self) -> ResourceCapability:
        return self._resource_capability

    @property
    def prompt_capability(self) -> PromptCapability:
        return self._prompt_capability

    def register_tool(self, name: str, description: str, input_schema: dict, handler: Callable[[dict], Any]) -> None:
        """Register a tool."""
        tool = MCPTool(name=name, description=description, input_schema=input_schema)
        self._tool_capability.register_tool(tool, handler)

    def register_resource(
        self,
        uri: str,
        name: str,
        description: str | None,
        mime_type: str | None,
        handler: Callable[[str], MCPResourceContent | list[MCPResourceContent]],
    ) -> None:
        """Register a resource."""
        resource = MCPResource(uri=uri, name=name, description=description, mime_type=mime_type)
        self._resource_capability.register_resource(resource, handler)

    def register_prompt(
        self,
        name: str,
        description: str,
        arguments: list[dict] | None,
        handler: Callable[[dict], MCPPromptResult],
    ) -> None:
        """Register a prompt."""
        prompt = MCPPrompt(name=name, description=description, arguments=arguments)
        self._prompt_capability.register_prompt(prompt, handler)

    async def add_transport(self, name: str, transport: MCPTransport) -> None:
        """Add a transport to the server."""
        self._transports[name] = transport
        await transport.connect()
        asyncio.create_task(self._handle_transport(name, transport))

    async def _handle_transport(self, name: str, transport: MCPTransport) -> None:
        """Handle messages from a transport."""
        logger.info(f"Starting transport handler for {name}")
        while transport.is_connected:
            try:
                message = await transport.receive()
                if message is None:
                    await asyncio.sleep(0.1)
                    continue

                response = await self._handle_message(message)
                if response and message.get("id") is not None:
                    await transport.send(response)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error handling transport {name}: {e}")
                await asyncio.sleep(1)

    async def _handle_message(self, message: dict) -> dict | None:
        """Handle an incoming message and return response if needed."""
        method = message.get("method")
        params = message.get("params", {})
        request_id = message.get("id")

        if not method:
            return None

        try:
            # Check core handlers first
            if method in self._request_handlers:
                result = await self._request_handlers[method](params)
                if request_id is not None:
                    return {"jsonrpc": "2.0", "id": request_id, "result": result}
                return None

            # Check capability handlers
            for capability in self._capabilities.values():
                try:
                    result = await capability.handle_request(method, params)
                    if request_id is not None:
                        return {"jsonrpc": "2.0", "id": request_id, "result": result}
                    return None
                except MCPError as e:
                    if request_id is not None:
                        return {"jsonrpc": "2.0", "id": request_id, "error": e.to_dict()}
                    raise
                except Exception as e:
                    logger.error(f"Capability error for {method}: {e}")

            # Method not found
            error = MCPError(MCPErrorCode.METHOD_NOT_FOUND, f"Method not found: {method}")
            if request_id is not None:
                return {"jsonrpc": "2.0", "id": request_id, "error": error.to_dict()}

        except Exception as e:
            logger.error(f"Error handling {method}: {e}")
            error = MCPError(MCPErrorCode.INTERNAL_ERROR, str(e))
            if request_id is not None:
                return {"jsonrpc": "2.0", "id": request_id, "error": error.to_dict()}

        return None

    async def _handle_initialize(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle initialize request."""
        self._client_info = MCPClientInfo(
            name=params.get("clientInfo", {}).get("name", "Unknown"),
            version=params.get("clientInfo", {}).get("version", "0.0.0"),
            protocol_version=params.get("protocolVersion", "2024-11-05"),
            capabilities=params.get("capabilities", {}),
        )

        self._initialized = True
        logger.info(f"MCP initialized with client: {self._client_info.name} {self._client_info.version}")

        # Build capabilities
        capabilities = {}
        for cap_name, cap in self._capabilities.items():
            capabilities[cap_name] = cap.get_capability_definition()

        return {
            "protocolVersion": "2024-11-05",
            "capabilities": capabilities,
            "serverInfo": {
                "name": self.server_info.name,
                "version": self.server_info.version,
            },
            "instructions": self.server_info.instructions,
        }

    async def _handle_ping(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle ping request."""
        return {}

    async def shutdown(self) -> None:
        """Shutdown the server."""
        for name, transport in self._transports.items():
            try:
                await transport.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting transport {name}: {e}")
        self._transports.clear()
        self._initialized = False
        logger.info("MCP server shutdown complete")


class MCPStdioServer(MCPServer):
    """MCP Server that runs over stdio."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._stdio_transport: MCPTransport | None = None

    async def run_stdio(self) -> None:
        """Run the server over stdio."""
        import sys

        logger.info("Starting MCP stdio server")

        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

        writer = asyncio.StreamWriter(sys.stdout, None, None, None)

        class StdioTransportWrapper:
            def __init__(self, reader, writer):
                self._reader = reader
                self._writer = writer
                self._connected = True

            @property
            def is_connected(self):
                return self._connected

            async def connect(self):
                pass

            async def disconnect(self):
                self._connected = False

            async def send(self, message):
                data = json.dumps(message) + "\n"
                self._writer.write(data.encode())
                await self._writer.drain()

            async def receive(self):
                line = await self._reader.readline()
                if not line:
                    return None
                try:
                    return json.loads(line.decode().strip())
                except json.JSONDecodeError:
                    return None

        transport = StdioTransportWrapper(reader, writer)
        await self.add_transport("stdio", transport)

        # Keep running
        while transport.is_connected:
            await asyncio.sleep(1)

        await self.shutdown()
