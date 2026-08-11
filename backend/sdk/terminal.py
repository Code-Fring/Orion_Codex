"""Terminal API for plugins."""

import asyncio
import subprocess
from typing import Any

from backend.events import publish_event, EventType


class TerminalAPI:
    """API for terminal operations."""

    def __init__(self, project_id: str) -> None:
        self.project_id = project_id

    async def execute_command(
        self,
        command: str,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout: int = 300,
    ) -> dict[str, Any]:
        """Execute a terminal command."""
        # Publish event
        await publish_event(EventType.TERMINAL_COMMAND, {
            "project_id": self.project_id,
            "command": command,
            "cwd": cwd,
        })

        try:
            result = await asyncio.wait_for(
                asyncio.create_subprocess_shell(
                    command,
                    cwd=cwd,
                    env=env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                ).communicate(),
                timeout=timeout,
            )

            stdout = result[0].decode("utf-8", errors="replace") if result[0] else ""
            stderr = result[1].decode("utf-8", errors="replace") if result[1] else ""

            output = {
                "stdout": stdout,
                "stderr": stderr,
                "returncode": result[2] if len(result) > 2 else 0,
            }

            await publish_event(EventType.TERMINAL_OUTPUT, {
                "project_id": self.project_id,
                "command": command,
                "output": output,
            })

            return output

        except asyncio.TimeoutError:
            return {"stdout": "", "stderr": "Command timed out", "returncode": -1}
        except Exception as e:
            return {"stdout": "", "stderr": str(e), "returncode": -1}

    def execute_command_sync(
        self,
        command: str,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout: int = 300,
    ) -> dict[str, Any]:
        """Execute a terminal command synchronously."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"stdout": "", "stderr": "Command timed out", "returncode": -1}
        except Exception as e:
            return {"stdout": "", "stderr": str(e), "returncode": -1}