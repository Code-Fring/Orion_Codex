"""MCP Client for connecting to and interacting with MCP servers."""

import asyncio
import logging
from typing import Any, Callable
from uuid import uuid4

from backend.mcp.transports import (
    HTTPTransport,
    SSETransport,
    StdioTransport,
    StdioTransportConfig,
    WebSocketTransport,
)
from backend.mcp.types import MCPTransport

logger = logging.getLogger(__name__)


class MCPClient:
    """MCP Client for connecting to and interacting with MCP servers."""

    def __init__(
        self,
        name: str = "Orion Codex",
        version: str = "0.1.0",
    ) -> None:
        self.client_info = {"name": name, "version": version}
        self._transport: MCPTransport | None = None
        self._connected = False
        self._initialized = False
        self._server_info: dict[str, Any] | None = None
        self._pending_requests: dict[str, asyncio.Future] = {}
        self._notification_handlers: dict[str, list[Callable]] = {}
        self._read_task: asyncio.Task | None = None
        self._tools: list[dict] = []
        self._resources: list[dict] = []
        self._prompts: list[dict] = []

    @property
    def is_connected(self) -> bool:
        return self._connected and self._transport is not None and self._transport.is_connected

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def server_info(self) -> dict[str, Any] | None:
        return self._server_info

    @property
    def tools(self) -> list[dict]:
        return self._tools

    @property
    def resources(self) -> list[dict]:
        return self._resources

    @property
    def prompts(self) -> list[dict]:
        return self._prompts

    async def connect(self, transport: MCPTransport) -> bool:
        """Connect to an MCP server using the given transport."""
        if self._connected:
            logger.warning("Already connected")
            return True

        self._transport = transport
        try:
            await self._transport.connect()
            self._connected = True
            self._read_task = asyncio.create_task(self._read_loop())
            logger.info("MCP client connected")
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            self._connected = False
            self._transport = None
            return False

    async def initialize(self) -> bool:
        """Initialize the MCP connection with initialize request."""
        if not self._connected:
            raise RuntimeError("Not connected")

        if self._initialized:
            logger.warning("Already initialized")
            return True

        # Send initialize request
        result = await self._send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {},
                    "prompts": {},
                },
                "clientInfo": self.client_info,
            },
        )

        if "error" in result:
            logger.error(f"Initialize failed: {result.get('error')}")
            return False

        self._server_info = result.get("result", {})
        self._initialized = True
        logger.info(f"MCP initialized with server: {self._server_info.get('serverInfo', {}).get('name', 'unknown')}")

        # Send initialized notification
        await self._send_notification("notifications/initialized", {})

        # Fetch capabilities
        await self._fetch_capabilities()

        return True

    async def disconnect(self) -> None:
        """Disconnect from the server."""
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass

        if self._transport:
            await self._transport.disconnect()

        self._connected = False
        self._initialized = False
        self._server_info = None
        self._tools = []
        self._resources = []
        self._prompts = []

    async def _send_request(self, method: str, params: dict | None = None, timeout: float = 30.0) -> dict:
        """Send a request and wait for response."""
        if not self._connected:
            raise RuntimeError("Not connected")

        request_id = str(uuid4())
        future: asyncio.Future = asyncio.Future()
        self._pending_requests[request_id] = future

        message = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        }

        await self._send_message(message)

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            raise TimeoutError(f"Request {method} timed out")
        finally:
            self._pending_requests.pop(request_id, None)

    async def _send_notification(self, method: str, params: dict | None = None) -> None:
        """Send a notification (no response expected)."""
        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
        }
        await self._send_message(message)

    async def _send_message(self, message: dict) -> None:
        """Send a raw message."""
        if self._transport:
            await self._transport.send(message)

    async def _read_loop(self) -> None:
        """Read messages from transport."""
        while True:
            try:
                message = await self._transport.receive()
                if message is None:
                    await asyncio.sleep(0.1)
                    continue
                await self._handle_message(message)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error reading message: {e}")
                await asyncio.sleep(1)

    async def _handle_message(self, message: dict) -> None:
        """Handle incoming message."""
        if "id" in message and message["id"] in self._pending_requests:
            future = self._pending_requests.pop(message["id"], None)
            if future and not future.done():
                future.set_result(message)
        elif "method" in message:
            await self._handle_notification(message)

    async def _fetch_capabilities(self) -> None:
        """Fetch server capabilities (tools, resources, prompts)."""
        # List tools
        try:
            result = await self._send_request("tools/list")
            if "result" in result:
                self._tools = result["result"].get("tools", [])
        except Exception as e:
            logger.warning(f"Failed to list tools: {e}")

        # List resources
        try:
            result = await self._send_request("resources/list")
            if "result" in result:
                self._resources = result["result"].get("resources", [])
        except Exception as e:
            logger.warning(f"Failed to list resources: {e}")

        # List prompts
        try:
            result = await self._send_request("prompts/list")
            if "result" in result:
                self._prompts = result["result"].get("prompts", [])
        except Exception as e:
            logger.warning(f"Failed to list prompts: {e}")

    async def list_tools(self) -> list[dict]:
        """Get list of available tools."""
        return self._tools

    async def call_tool(self, name: str, arguments: dict) -> dict:
        """Call a tool on the server."""
        return await self._send_request("tools/call", {"name": name, "arguments": arguments})

    async def list_resources(self) -> list[dict]:
        """Get list of available resources."""
        return self._resources

    async def read_resource(self, uri: str) -> dict:
        """Read a resource from the server."""
        return await self._send_request("resources/read", {"uri": uri})

    async def list_prompts(self) -> list[dict]:
        """Get list of available prompts."""
        return self._prompts

    async def get_prompt(self, name: str, arguments: dict | None = None) -> dict:
        """Get a prompt from the server."""
        return await self._send_request("prompts/get", {"name": name, "arguments": arguments or {}})

    async def subscribe_resource(self, uri: str) -> bool:
        """Subscribe to resource changes."""
        result = await self._send_request("resources/subscribe", {"uri": uri})
        return "result" in result

    async def unsubscribe_resource(self, uri: str) -> bool:
        """Unsubscribe from resource changes."""
        result = await self._send_request("resources/unsubscribe", {"uri": uri})
        return "result" in result

    def add_notification_handler(self, method: str, handler: Callable) -> None:
        """Add a notification handler."""
        if method not in self._notification_handlers:
            self._notification_handlers[method] = []
        self._notification_handlers[method].append(handler)

    def remove_notification_handler(self, method: str, handler: Callable) -> None:
        """Remove a notification handler."""
        if method in self._notification_handlers:
            self._notification_handlers[method].remove(handler)

    async def _handle_notification(self, message: dict) -> None:
        """Handle incoming notification."""
        method = message.get("method")
        params = message.get("params", {})
        handlers = self._notification_handlers.get(method, [])
        for handler in handlers:
            try:
                await handler(params)
            except Exception as e:
                logger.error(f"Error in notification handler for {method}: {e}")