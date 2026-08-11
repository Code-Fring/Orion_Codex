"""GitHub API Tool Plugin."""

import asyncio
import logging
from typing import Any

from backend.plugins.sdk.base import ToolPlugin, PluginContext, PluginManifest

logger = logging.getLogger(__name__)


class GitHubToolPlugin(ToolPlugin):
    """GitHub API Tool Plugin."""

    def __init__(self, manifest: PluginManifest, context: PluginContext) -> None:
        super().__init__(manifest, context)
        self._session = None
        self._token = None
        self._base_url = "https://api.github.com"

    async def _on_initialize(self) -> None:
        """Initialize the tool."""
        self._token = self.get_config("token")
        self._base_url = self.get_config("base_url", "https://api.github.com")

        if not self._token:
            raise ValueError("GitHub token is required")

    async def _on_shutdown(self) -> None:
        """Shutdown the tool."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _get_session(self):
        import aiohttp
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Accept": "application/vnd.github.v3+json",
                }
            )
        return self._session

    async def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        """Execute a GitHub API operation."""
        action = args.get("action")
        if not action:
            return {"error": "No action specified"}

        session = await self._get_session()

        try:
            if action == "list_repos":
                return await self._list_repos(session, args)
            elif action == "get_repo":
                return await self._get_repo(session, args)
            elif action == "create_repo":
                return await self._create_repo(session, args)
            elif action == "list_issues":
                return await self._list_issues(session, args)
            elif action == "create_issue":
                return await self._create_issue(session, args)
            elif action == "get_pr":
                return await self._get_pr(session, args)
            elif action == "list_prs":
                return await self._list_prs(session, args)
            elif action == "create_pr":
                return await self._create_pr(session, args)
            elif action == "get_file":
                return await self._get_file(session, args)
            elif action == "create_file":
                return await self._create_file(session, args)
            elif action == "update_file":
                return await self._update_file(session, args)
            elif action == "delete_file":
                return await self._delete_file(session, args)
            elif action == "search_code":
                return await self._search_code(session, args)
            else:
                return {"error": f"Unknown action: {action}"}

        except Exception as e:
            logger.error(f"GitHub API error: {e}")
            return {"error": str(e)}

    async def _list_repos(self, session, args: dict) -> dict[str, Any]:
        """List repositories."""
        async with session.get(f"{self._base_url}/user/repos") as resp:
            return {"repos": await resp.json()}

    async def _get_repo(self, session, args: dict) -> dict[str, Any]:
        """Get repository details."""
        owner = args.get("owner")
        repo = args.get("repo")
        async with session.get(f"{self._base_url}/repos/{owner}/{repo}") as resp:
            return await resp.json()

    async def _create_repo(self, session, args: dict) -> dict[str, Any]:
        """Create a new repository."""
        payload = {"name": args.get("name"), "private": args.get("private", False)}
        async with session.post(f"{self._base_url}/user/repos", json=payload) as resp:
            return await resp.json()

    async def _list_issues(self, session, args: dict) -> dict[str, Any]:
        """List issues."""
        owner = args.get("owner")
        repo = args.get("repo")
        state = args.get("state", "open")
        async with session.get(f"{self._base_url}/repos/{owner}/{repo}/issues?state={state}") as resp:
            return {"issues": await resp.json()}

    async def _create_issue(self, session, args: dict) -> dict[str, Any]:
        """Create an issue."""
        owner = args.get("owner")
        repo = args.get("repo")
        payload = {"title": args.get("title"), "body": args.get("body", "")}
        async with session.post(f"{self._base_url}/repos/{owner}/{repo}/issues", json=payload) as resp:
            return await resp.json()

    async def _get_pr(self, session, args: dict) -> dict[str, Any]:
        """Get pull request."""
        owner = args.get("owner")
        repo = args.get("repo")
        pr_number = args.get("pr_number")
        async with session.get(f"{self._base_url}/repos/{owner}/{repo}/pulls/{pr_number}") as resp:
            return await resp.json()

    async def _list_prs(self, session, args: dict) -> dict[str, Any]:
        """List pull requests."""
        owner = args.get("owner")
        repo = args.get("repo")
        state = args.get("state", "open")
        async with session.get(f"{self._base_url}/repos/{owner}/{repo}/pulls?state={state}") as resp:
            return {"prs": await resp.json()}

    async def _create_pr(self, session, args: dict) -> dict[str, Any]:
        """Create a pull request."""
        owner = args.get("owner")
        repo = args.get("repo")
        payload = {
            "title": args.get("title"),
            "head": args.get("head"),
            "base": args.get("base"),
            "body": args.get("body", ""),
        }
        async with session.post(f"{self._base_url}/repos/{owner}/{repo}/pulls", json=payload) as resp:
            return await resp.json()

    async def _get_file(self, session, args: dict) -> dict[str, Any]:
        """Get file contents."""
        owner = args.get("owner")
        repo = args.get("repo")
        path = args.get("path")
        ref = args.get("ref", "")
        params = {"ref": ref} if ref else {}
        async with session.get(f"{self._base_url}/repos/{owner}/{repo}/contents/{path}", params=params) as resp:
            return await resp.json()

    async def _create_file(self, session, args: dict) -> dict[str, Any]:
        """Create a file."""
        import base64
        owner = args.get("owner")
        repo = args.get("repo")
        path = args.get("path")
        content = base64.b64encode(args.get("content", "").encode()).decode()
        message = args.get("message", f"Create {path}")
        payload = {"message": message, "content": content}
        async with session.put(f"{self._base_url}/repos/{owner}/{repo}/contents/{path}", json=payload) as resp:
            return await resp.json()

    async def _update_file(self, session, args: dict) -> dict[str, Any]:
        """Update a file."""
        import base64
        owner = args.get("owner")
        repo = args.get("repo")
        path = args.get("path")
        content = base64.b64encode(args.get("content", "").encode()).decode()
        message = args.get("message", f"Update {path}")
        sha = args.get("sha")
        payload = {"message": message, "content": content, "sha": sha}
        async with session.put(f"{self._base_url}/repos/{owner}/{repo}/contents/{path}", json=payload) as resp:
            return await resp.json()

    async def _delete_file(self, session, args: dict) -> dict[str, Any]:
        """Delete a file."""
        owner = args.get("owner")
        repo = args.get("repo")
        path = args.get("path")
        message = args.get("message", f"Delete {path}")
        sha = args.get("sha")
        payload = {"message": message, "sha": sha}
        async with session.delete(f"{self._base_url}/repos/{owner}/{repo}/contents/{path}", json=payload) as resp:
            return await resp.json()

    async def _search_code(self, session, args: dict) -> dict[str, Any]:
        """Search code."""
        query = args.get("query")
        async with session.get(f"{self._base_url}/search/code", params={"q": query}) as resp:
            return await resp.json()

    def get_tool_schema(self) -> dict[str, Any]:
        """Get tool schema for LLM function calling."""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "list_repos", "get_repo", "create_repo",
                        "list_issues", "create_issue",
                        "get_pr", "list_prs", "create_pr",
                        "get_file", "create_file", "update_file", "delete_file",
                        "search_code"
                    ],
                    "description": "GitHub API action to perform"
                },
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "name": {"type": "string", "description": "Repository name for creation"},
                "private": {"type": "boolean", "description": "Create private repository"},
                "title": {"type": "string", "description": "Issue/PR title"},
                "body": {"type": "string", "description": "Issue/PR body"},
                "state": {"type": "string", "enum": ["open", "closed", "all"], "description": "Issue/PR state"},
                "pr_number": {"type": "integer", "description": "Pull request number"},
                "path": {"type": "string", "description": "File path"},
                "ref": {"type": "string", "description": "Git reference (branch/tag/commit)"},
                "content": {"type": "string", "description": "File content"},
                "message": {"type": "string", "description": "Commit message"},
                "sha": {"type": "string", "description": "File SHA for updates/deletes"},
                "head": {"type": "string", "description": "PR head branch"},
                "base": {"type": "string", "description": "PR base branch"},
                "query": {"type": "string", "description": "Search query"},
            },
            "required": ["action"]
        }