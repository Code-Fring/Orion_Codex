"""Git API for plugins."""

import asyncio
import subprocess
from pathlib import Path
from typing import Any

from backend.events import publish_event, EventType


class GitAPI:
    """API for git operations."""

    def __init__(self, project_id: str, workspace_path: str) -> None:
        self.project_id = project_id
        self.workspace_path = workspace_path

    def _run_git(self, args: list[str]) -> dict[str, Any]:
        """Run a git command."""
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                timeout=60,
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "stdout": "", "stderr": "Git command timed out", "returncode": -1}
        except Exception as e:
            return {"success": False, "stdout": "", "stderr": str(e), "returncode": -1}

    def status(self) -> dict[str, Any]:
        """Get git status."""
        result = self._run_git(["status", "--porcelain"])
        if not result["success"]:
            return result

        files = []
        for line in result["stdout"].splitlines():
            if line:
                status = line[:2]
                path = line[3:]
                files.append({"status": status.strip(), "path": path})

        # Get branch info
        branch_result = self._run_git(["branch", "--show-current"])
        branch = branch_result["stdout"].strip() if branch_result["success"] else "unknown"

        return {"success": True, "branch": branch, "files": files, "clean": len(files) == 0}

    def commit(self, message: str, add_all: bool = True) -> dict[str, Any]:
        """Create a commit."""
        if add_all:
            self._run_git(["add", "-A"])

        result = self._run_git(["commit", "-m", message])
        if result["success"]:
            asyncio.create_task(publish_event(EventType.GIT_COMMIT, {
                "project_id": self.project_id,
                "message": message,
            }))
        return result

    def push(self, remote: str = "origin", branch: str | None = None) -> dict[str, Any]:
        """Push to remote."""
        args = ["push", remote]
        if branch:
            args.append(branch)
        result = self._run_git(args)
        if result["success"]:
            asyncio.create_task(publish_event(EventType.GIT_PUSH, {
                "project_id": self.project_id,
                "remote": remote,
                "branch": branch,
            }))
        return result

    def pull(self, remote: str = "origin", branch: str | None = None) -> dict[str, Any]:
        """Pull from remote."""
        args = ["pull", remote]
        if branch:
            args.append(branch)
        result = self._run_git(args)
        if result["success"]:
            asyncio.create_task(publish_event(EventType.GIT_PULL, {
                "project_id": self.project_id,
                "remote": remote,
                "branch": branch,
            }))
        return result

    def log(self, limit: int = 20) -> list[dict[str, str]]:
        """Get commit log."""
        result = self._run_git(["log", f"-{limit}", "--pretty=format:%H|%s|%an|%ad", "--date=short"])
        if not result["success"]:
            return []

        commits = []
        for line in result["stdout"].splitlines():
            if line:
                parts = line.split("|", 3)
                if len(parts) == 4:
                    commits.append({
                        "hash": parts[0],
                        "message": parts[1],
                        "author": parts[2],
                        "date": parts[3],
                    })
        return commits

    def diff(self, file_path: str | None = None) -> str:
        """Get diff."""
        args = ["diff"]
        if file_path:
            args.append(file_path)
        result = self._run_git(args)
        return result["stdout"] if result["success"] else ""

    def branch(self, name: str | None = None) -> dict[str, Any]:
        """Create or list branches."""
        if name:
            result = self._run_git(["checkout", "-b", name])
        else:
            result = self._run_git(["branch"])
        return result

    def is_repo(self) -> bool:
        """Check if workspace is a git repo."""
        return (Path(self.workspace_path) / ".git").exists()