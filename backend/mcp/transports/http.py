"""MCP HTTP transport implementation."""

import asyncio
import json
import logging
from typing import Any

import aiohttp
from aiohttp import ClientSession, ClientWebSocketResponse

from backend.mcp.types import MCPMessage, MCPTransport, MCPTransportType

logger = logging.getLogger(__name__)


class HTTPTransport(MCPTransport):
    """MCP HTTP transport for communicating with HTTP-based servers."""

    def __init__(
        self,
        base_url: str,
        headers: dict[str, str] | None = None,
        auth_token: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.headers = headers or {}
        if auth_token:
            self.headers["Authorization"] = f"Bearer {auth_token}"
        self._session: ClientSession | None = None
        self._connected = False
        self._message_queue: asyncio.Queue[MCPMessage] = asyncio.Queue()
        self._poll_task: asyncio.Task | None = None
        self._poll_interval = 1.0

    @property
    def is_connected(self) -> bool:
        return self._connected and self._session is not None and not self._session.closed

    @property
    def transport_type(self) -> MCPTransportType:
        return MCPTransportType.HTTP

    async def connect(self) -> None:
        """Initialize HTTP session."""
        if self._connected:
            return

        timeout = aiohttp.ClientTimeout(total=30)
        self._session = ClientSession(timeout=timeout, headers=self.headers)
        self._connected = True

        # Start polling for server-sent events/notifications
        self._poll_task = asyncio.create_task(self._poll_loop())
        logger.info(f"MCP HTTP transport connected to {self.base_url}")

    async def disconnect(self) -> None:
        """Close HTTP session."""
        if not self._connected:
            return

        self._connected = False

        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass

        if self._session:
            await self._session.close()
            self._session = None

        logger.info("MCP HTTP transport disconnected")

    async def send(self, message: MCPMessage) -> None:
        """Send a message via HTTP POST."""
        if not self.is_connected or not self._session:
            raise RuntimeError("Transport not connected")

        url = f"{self.base_url}/mcp"
        data = message.to_json()

        try:
            async with self._session.post(url, data=data, headers={"Content-Type": "application/json"}) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"HTTP {response.status}: {error_text}")

                # For request-response pattern, read response
                if message.id is not None:
                    response_data = await response.json()
                    response_message = MCPMessage.from_dict(response_data)
                    await self._message_queue.put(response_message)

        except aiohttp.ClientError as e:
            logger.error(f"HTTP send error: {e}")
            raise

    async def receive(self) -> MCPMessage | None:
        """Receive a message from the queue."""
        try:
            return await asyncio.wait_for(self._message_queue.get(), timeout=0.1)
        except asyncio.TimeoutError:
            return None

    async def _poll_loop(self) -> None:
        """Poll for server notifications (long-polling style)."""
        while self._connected and self._session:
            try:
                url = f"{self.base_url}/mcp/notifications"
                async with self._session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data:
                            message = MCPMessage.from_dict(data)
                            await self._message_queue.put(message)
                    elif response.status == 204:
                        # No notifications, continue polling
                        pass
                    else:
                        logger.warning(f"Poll error: HTTP {response.status}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Poll loop error: {e}")

            await asyncio.sleep(self._poll_interval)


class SSETransport(MCPTransport):
    """MCP Server-Sent Events transport."""

    def __init__(
        self,
        base_url: str,
        headers: dict[str, str] | None = None,
        auth_token: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.headers = headers or {}
        if auth_token:
            self.headers["Authorization"] = f"Bearer {auth_token}"
        self._session: ClientSession | None = None
        self._sse_response: aiohttp.ClientResponse | None = None
        self._connected = False
        self._message_queue: asyncio.Queue[MCPMessage] = asyncio.Queue()
        self._read_task: asyncio.Task | None = None

    @property
    def is_connected(self) -> bool:
        return self._connected and self._session is not None and not self._session.closed

    @property
    def transport_type(self) -> MCPTransportType:
        return MCPTransportType.SSE

    async def connect(self) -> None:
        """Connect to SSE endpoint."""
        if self._connected:
            return

        timeout = aiohttp.ClientTimeout(total=None)
        self._session = ClientSession(timeout=timeout, headers=self.headers)

        # Connect to SSE stream
        url = f"{self.base_url}/mcp/sse"
        self._sse_response = await self._session.get(url, headers={"Accept": "text/event-stream"})

        if self._sse_response.status != 200:
            await self._sse_response.release()
            await self._session.close()
            raise RuntimeError(f"SSE connection failed: HTTP {self._sse_response.status}")

        self._connected = True
        self._read_task = asyncio.create_task(self._read_sse())
        logger.info(f"MCP SSE transport connected to {self.base_url}")

    async def disconnect(self) -> None:
        """Disconnect from SSE."""
        if not self._connected:
            return

        self._connected = False

        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass

        if self._sse_response:
            self._sse_response.close()

        if self._session:
            await self._session.close()

        logger.info("MCP SSE transport disconnected")

    async def send(self, message: MCPMessage) -> None:
        """Send a message via HTTP POST (separate from SSE)."""
        if not self.is_connected or not self._session:
            raise RuntimeError("Transport not connected")

        url = f"{self.base_url}/mcp"
        data = message.to_json()

        async with self._session.post(url, data=data, headers={"Content-Type": "application/json"}) as response:
            if response.status != 200:
                error_text = await response.text()
                raise RuntimeError(f"HTTP {response.status}: {error_text}")

            if message.id is not None:
                response_data = await response.json()
                response_message = MCPMessage.from_dict(response_data)
                await self._message_queue.put(response_message)

    async def receive(self) -> MCPMessage | None:
        """Receive a message from the queue."""
        try:
            return await asyncio.wait_for(self._message_queue.get(), timeout=0.1)
        except asyncio.TimeoutError:
            return None

    async def _read_sse(self) -> None:
        """Read Server-Sent Events stream."""
        if not self._sse_response:
            return

        buffer = ""
        try:
            async for line in self._sse_response.content:
                if not self._connected:
                    break

                line = line.decode("utf-8").rstrip("\n")

                if line.startswith("data: "):
                    data = line[6:]
                    buffer += data
                    if buffer.strip():
                        try:
                            parsed = json.loads(buffer)
                            message = MCPMessage.from_dict(parsed)
                            await self._message_queue.put(message)
                            buffer = ""
                        except json.JSONDecodeError:
                            # Incomplete message, wait for more data
                            pass
                elif line == "":
                    # End of event
                    if buffer.strip():
                        try:
                            parsed = json.loads(buffer)
                            message = MCPMessage.from_dict(parsed)
                            await self._message_queue.put(message)
                        except json.JSONDecodeError:
                            pass
                        buffer = ""

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"SSE read error: {e}")
        finally:
            self._connected = False


class WebSocketTransport(MCPTransport):
    """MCP WebSocket transport."""

    def __init__(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        auth_token: str | None = None,
    ) -> None:
        self.url = url
        self.headers = headers or {}
        if auth_token:
            self.headers["Authorization"] = f"Bearer {auth_token}"
        self._session: ClientSession | None = None
        self._ws: ClientWebSocketResponse | None = None
        self._connected = False
        self._message_queue: asyncio.Queue[MCPMessage] = asyncio.Queue()
        self._read_task: asyncio.Task | None = None

    @property
    def is_connected(self) -> bool:
        return self._connected and self._ws is not None and not self._ws.closed

    @property
    def transport_type(self) -> MCPTransportType:
        return MCPTransportType.WEBSOCKET

    async def connect(self) -> None:
        """Connect to WebSocket endpoint."""
        if self._connected:
            return

        self._session = ClientSession()
        self._ws = await self._session.ws_connect(self.url, headers=self.headers)
        self._connected = True
        self._read_task = asyncio.create_task(self._read_loop())
        logger.info(f"MCP WebSocket transport connected to {self.url}")

    async def disconnect(self) -> None:
        """Disconnect WebSocket."""
        if not self._connected:
            return

        self._connected = False

        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass

        if self._ws:
            await self._ws.close()

        if self._session:
            await self._session.close()

        logger.info("MCP WebSocket transport disconnected")

    async def send(self, message: MCPMessage) -> None:
        """Send message via WebSocket."""
        if not self.is_connected or not self._ws:
            raise RuntimeError("Transport not connected")

        await self._ws.send_str(message.to_json())

    async def receive(self) -> MCPMessage | None:
        """Receive message from queue."""
        try:
            return await asyncio.wait_for(self._message_queue.get(), timeout=0.1)
        except asyncio.TimeoutError:
            return None

    async def _read_loop(self) -> None:
        """Read messages from WebSocket."""
        if not self._ws:
            return

        try:
            async for msg in self._ws:
                if not self._connected:
                    break

                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        parsed = json.loads(msg.data)
                        message = MCPMessage.from_dict(parsed)
                        await self._message_queue.put(message)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse WebSocket message: {e}")
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {self._ws.exception()}")
                    break
                elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSING, aiohttp.WSMsgType.CLOSED):
                    break

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"WebSocket read error: {e}")
        finally:
            self._connected = False