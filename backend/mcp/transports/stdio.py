"""MCP stdio transport implementation."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from backend.mcp.types import MCPMessage, MCPTransport, MCPTransportType

logger = logging.getLogger(__name__)


class StdioTransport(MCPTransport):
    """MCP stdio transport for communicating with subprocess servers."""

    def __init__(
        self,
        command: list[str],
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self.command = command
        self.cwd = cwd
        self.env = env or {}
        self._process: asyncio.subprocess.Process | None = None
        self._read_task: asyncio.Task | None = None
        self._message_queue: asyncio.Queue[MCPMessage] = asyncio.Queue()
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected and self._process is not None and self._process.returncode is None

    @property
    def transport_type(self) -> MCPTransportType:
        return MCPTransportType.STDIO

    async def connect(self) -> None:
        """Start the subprocess and connect via stdio."""
        if self._connected:
            return

        logger.info(f"Starting MCP server: {' '.join(self.command)}")

        # Prepare environment
        import os
        process_env = os.environ.copy()
        process_env.update(self.env)

        self._process = await asyncio.create_subprocess_exec(
            *self.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.cwd,
            env=process_env,
        )

        self._connected = True
        self._read_task = asyncio.create_task(self._read_loop())
        logger.info("MCP stdio transport connected")

    async def disconnect(self) -> None:
        """Stop the subprocess."""
        if not self._connected:
            return

        self._connected = False

        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass

        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()
                await self._process.wait()
            except Exception as e:
                logger.error(f"Error stopping MCP server: {e}")

        self._process = None
        logger.info("MCP stdio transport disconnected")

    async def send(self, message: MCPMessage) -> None:
        """Send a message via stdin."""
        if not self.is_connected or not self._process or not self._process.stdin:
            raise RuntimeError("Transport not connected")

        data = message.to_json() + "\n"
        self._process.stdin.write(data.encode("utf-8"))
        await self._process.stdin.drain()

    async def receive(self) -> MCPMessage | None:
        """Receive a message from the queue."""
        try:
            return await asyncio.wait_for(self._message_queue.get(), timeout=0.1)
        except asyncio.TimeoutError:
            return None

    async def _read_loop(self) -> None:
        """Read messages from stdout."""
        if not self._process or not self._process.stdout:
            return

        buffer = ""
        try:
            while self._connected and self._process.stdout:
                chunk = await self._process.stdout.read(4096)
                if not chunk:
                    break

                buffer += chunk.decode("utf-8", errors="replace")

                # Process complete lines
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        parsed = json.loads(line)
                        message = MCPMessage.from_dict(parsed)
                        await self._message_queue.put(message)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse MCP message: {e}, line: {line[:100]}")
                    except Exception as e:
                        logger.error(f"Error processing MCP message: {e}")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in stdio read loop: {e}")
        finally:
            self._connected = False


class StdioTransportConfig:
    """Configuration for stdio transport."""
    def __init__(
        self,
        command: list[str],
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self.command = command
        self.cwd = cwd
        self.env = env or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "cwd": str(self.cwd) if self.cwd else None,
            "env": self.env,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StdioTransportConfig":
        return cls(
            command=data["command"],
            cwd=Path(data["cwd"]) if data.get("cwd") else None,
            env=data.get("env"),
        )