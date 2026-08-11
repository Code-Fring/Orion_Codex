"""Git agent for version control operations."""

import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.agents.base import AgentContext, AgentResult, BaseAgent
from backend.core.model_manager import AgentRole, model_manager
from backend.core.providers.interfaces import ChatMessage

logger = logging.getLogger(__name__)


class GitAgent(BaseAgent):
    """Agent for Git operations and version control management."""

    def __init__(
        self,
        name: str = "git_agent",
        description: str = "Git operations and version control agent",
        config: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(name=name, description=description, config=config)

    @property
    def agent_type(self) -> str:
        return "git"

    async def execute(self, context: AgentContext) -> AgentResult:
        """Perform Git operations."""
        action = context.config.get("action", "status")
        workspace_path = Path(context.workspace_path)

        # Ensure we're in a git repo
        if not (workspace_path / ".git").exists():
            return AgentResult(success=False, error="Not a git repository")

        if action == "status":
            return await self._git_status(workspace_path)
        elif action == "commit":
            return await self._git_commit(workspace_path, context)
        elif action == "branch":
            return await self._git_branch(workspace_path, context)
        elif action == "merge":
            return await self._git_merge(workspace_path, context)
        elif action == "push":
            return await self._git_push(workspace_path, context)
        elif action == "pull":
            return await self._git_pull(workspace_path, context)
        elif action == "log":
            return await self._git_log(workspace_path, context)
        elif action == "diff":
            return await self._git_diff(workspace_path, context)
        elif action == "stash":
            return await self._git_stash(workspace_path, context)
        elif action == "tag":
            return await self._git_tag(workspace_path, context)
        elif action == "auto_commit":
            return await self._auto_commit(workspace_path, context)
        elif action == "generate_changelog":
            return await self._generate_changelog(workspace_path, context)
        else:
            return AgentResult(success=False, error=f"Unknown git action: {action}")

    async def _run_git(
        self, workspace_path: Path, args: list[str]
    ) -> subprocess.CompletedProcess:
        """Run a git command."""
        return subprocess.run(
            ["git"] + args,
            cwd=workspace_path,
            capture_output=True,
            text=True,
            timeout=60,
        )

    async def _git_status(self, workspace_path: Path) -> AgentResult:
        """Get git status."""
        result = await self._run_git(workspace_path, ["status", "--porcelain"])

        files = []
        for line in result.stdout.splitlines():
            if line:
                status = line[:2]
                filepath = line[3:]
                files.append({"status": status.strip(), "path": filepath})

        # Get current branch
        branch_result = await self._run_git(
            workspace_path, ["branch", "--show-current"]
        )
        current_branch = branch_result.stdout.strip()

        # Get ahead/behind
        ahead_behind = await self._run_git(
            workspace_path,
            [
                "rev-list",
                "--left-right",
                "--count",
                f"{current_branch}...origin/{current_branch}",
            ],
        )
        ahead_behind_counts = (
            ahead_behind.stdout.strip().split("\t")
            if ahead_behind.stdout.strip()
            else ["0", "0"]
        )

        return AgentResult(
            success=True,
            output={
                "branch": current_branch,
                "files": files,
                "ahead": int(ahead_behind_counts[0]),
                "behind": int(ahead_behind_counts[1]),
                "clean": len(files) == 0,
            },
        )

    async def _git_commit(
        self, workspace_path: Path, context: AgentContext
    ) -> AgentResult:
        """Create a commit."""
        message = context.config.get("message")
        if not message:
            # Generate commit message from changes
            diff_result = await self._run_git(workspace_path, ["diff", "--cached"])
            if not diff_result.stdout.strip():
                diff_result = await self._run_git(workspace_path, ["diff"])

            if diff_result.stdout.strip():
                message = await self._generate_commit_message(diff_result.stdout)
            else:
                return AgentResult(success=False, error="No changes to commit")

        # Stage all changes if requested
        if context.config.get("stage_all", True):
            await self._run_git(workspace_path, ["add", "-A"])

        result = await self._run_git(workspace_path, ["commit", "-m", message])

        if result.returncode == 0:
            return AgentResult(
                success=True, output={"message": message, "output": result.stdout}
            )
        else:
            return AgentResult(success=False, error=result.stderr)

    async def _generate_commit_message(self, diff: str) -> str:
        """Generate a commit message from diff using AI."""
        provider_info = model_manager.get_model_for_role(AgentRole.GIT)
        if not provider_info:
            return f"chore: update files ({datetime.now().strftime('%Y-%m-%d %H:%M')})"

        provider, model_id = provider_info

        try:
            system_prompt = """Generate a conventional commit message from the diff.
Format: <type>(<scope>): <subject>

Types: feat, fix, docs, style, refactor, test, chore, perf, ci, build, revert

Return ONLY the commit message, nothing else."""

            messages = [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=f"Diff:\n{diff[:3000]}"),
            ]

            response = await provider.chat(
                messages=messages,
                model=model_id,
                temperature=0.3,
                max_tokens=200,
            )

            return response.content.strip()
        except Exception:
            return f"chore: update files ({datetime.now().strftime('%Y-%m-%d %H:%M')})"

    async def _git_branch(
        self, workspace_path: Path, context: AgentContext
    ) -> AgentResult:
        """Branch operations."""
        sub_action = context.config.get("branch_action", "list")
        branch_name = context.config.get("branch_name")

        if sub_action == "list":
            result = await self._run_git(workspace_path, ["branch", "-a"])
            branches = [
                b.strip().replace("* ", "")
                for b in result.stdout.splitlines()
                if b.strip()
            ]
            return AgentResult(success=True, output={"branches": branches})

        elif sub_action == "create":
            if not branch_name:
                return AgentResult(success=False, error="Branch name required")
            result = await self._run_git(
                workspace_path, ["checkout", "-b", branch_name]
            )
            return AgentResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr,
            )

        elif sub_action == "delete":
            if not branch_name:
                return AgentResult(success=False, error="Branch name required")
            force = context.config.get("force", False)
            args = ["branch", "-D" if force else "-d", branch_name]
            result = await self._run_git(workspace_path, args)
            return AgentResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr,
            )

        elif sub_action == "switch":
            if not branch_name:
                return AgentResult(success=False, error="Branch name required")
            result = await self._run_git(workspace_path, ["checkout", branch_name])
            return AgentResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr,
            )

        return AgentResult(success=False, error=f"Unknown branch action: {sub_action}")

    async def _git_merge(
        self, workspace_path: Path, context: AgentContext
    ) -> AgentResult:
        """Merge branches."""
        source_branch = context.config.get("source_branch")
        target_branch = context.config.get("target_branch")

        if not source_branch:
            return AgentResult(success=False, error="Source branch required")

        # Switch to target branch if specified
        if target_branch:
            result = await self._run_git(workspace_path, ["checkout", target_branch])
            if result.returncode != 0:
                return AgentResult(
                    success=False,
                    error=f"Failed to checkout {target_branch}: {result.stderr}",
                )

        result = await self._run_git(workspace_path, ["merge", source_branch])

        if result.returncode == 0:
            return AgentResult(success=True, output=result.stdout)
        else:
            # Check for conflicts
            if "CONFLICT" in result.stdout:
                conflicts = await self._get_conflicts(workspace_path)
                return AgentResult(
                    success=False,
                    error="Merge conflicts detected",
                    output={"conflicts": conflicts, "stdout": result.stdout},
                )
            return AgentResult(success=False, error=result.stderr)

    async def _get_conflicts(self, workspace_path: Path) -> list[str]:
        """Get list of conflicted files."""
        result = await self._run_git(
            workspace_path, ["diff", "--name-only", "--diff-filter=U"]
        )
        return [f.strip() for f in result.stdout.splitlines() if f.strip()]

    async def _git_push(
        self, workspace_path: Path, context: AgentContext
    ) -> AgentResult:
        """Push to remote."""
        remote = context.config.get("remote", "origin")
        branch = context.config.get("branch")
        force = context.config.get("force", False)

        args = ["push"]
        if force:
            args.append("--force-with-lease")
        if branch:
            args.extend([remote, branch])
        else:
            args.append(remote)

        result = await self._run_git(workspace_path, args)
        return AgentResult(
            success=result.returncode == 0, output=result.stdout, error=result.stderr
        )

    async def _git_pull(
        self, workspace_path: Path, context: AgentContext
    ) -> AgentResult:
        """Pull from remote."""
        remote = context.config.get("remote", "origin")
        branch = context.config.get("branch")
        rebase = context.config.get("rebase", False)

        args = ["pull"]
        if rebase:
            args.append("--rebase")
        if branch:
            args.extend([remote, branch])
        else:
            args.append(remote)

        result = await self._run_git(workspace_path, args)
        return AgentResult(
            success=result.returncode == 0, output=result.stdout, error=result.stderr
        )

    async def _git_log(
        self, workspace_path: Path, context: AgentContext
    ) -> AgentResult:
        """Get git log."""
        limit = context.config.get("limit", 20)
        oneline = context.config.get("oneline", True)

        args = ["log", f"-{limit}"]
        if oneline:
            args.append("--oneline")
        else:
            args.extend(["--pretty=format:%H|%an|%ad|%s", "--date=short"])

        result = await self._run_git(workspace_path, args)

        commits = []
        for line in result.stdout.splitlines():
            if oneline:
                parts = line.split(" ", 1)
                if len(parts) == 2:
                    commits.append({"hash": parts[0], "message": parts[1]})
            else:
                parts = line.split("|", 3)
                if len(parts) == 4:
                    commits.append(
                        {
                            "hash": parts[0],
                            "author": parts[1],
                            "date": parts[2],
                            "message": parts[3],
                        }
                    )

        return AgentResult(success=True, output={"commits": commits})

    async def _git_diff(
        self, workspace_path: Path, context: AgentContext
    ) -> AgentResult:
        """Get git diff."""
        staged = context.config.get("staged", False)
        file_path = context.config.get("file")

        args = ["diff"]
        if staged:
            args.append("--cached")
        if file_path:
            args.append(file_path)

        result = await self._run_git(workspace_path, args)
        return AgentResult(success=True, output={"diff": result.stdout})

    async def _git_stash(
        self, workspace_path: Path, context: AgentContext
    ) -> AgentResult:
        """Stash operations."""
        sub_action = context.config.get("stash_action", "push")

        if sub_action == "push":
            message = context.config.get("message")
            args = ["stash", "push"]
            if message:
                args.extend(["-m", message])
            result = await self._run_git(workspace_path, args)
            return AgentResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr,
            )

        elif sub_action == "pop":
            result = await self._run_git(workspace_path, ["stash", "pop"])
            return AgentResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr,
            )

        elif sub_action == "list":
            result = await self._run_git(workspace_path, ["stash", "list"])
            stashes = [s.strip() for s in result.stdout.splitlines() if s.strip()]
            return AgentResult(success=True, output={"stashes": stashes})

        elif sub_action == "drop":
            index = context.config.get("index", 0)
            result = await self._run_git(
                workspace_path, ["stash", "drop", f"stash@{{{index}}}"]
            )
            return AgentResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr,
            )

        return AgentResult(success=False, error=f"Unknown stash action: {sub_action}")

    async def _git_tag(
        self, workspace_path: Path, context: AgentContext
    ) -> AgentResult:
        """Tag operations."""
        sub_action = context.config.get("tag_action", "list")
        tag_name = context.config.get("tag_name")
        message = context.config.get("message")

        if sub_action == "list":
            result = await self._run_git(workspace_path, ["tag", "-l"])
            tags = [t.strip() for t in result.stdout.splitlines() if t.strip()]
            return AgentResult(success=True, output={"tags": tags})

        elif sub_action == "create":
            if not tag_name:
                return AgentResult(success=False, error="Tag name required")
            args = ["tag"]
            if message:
                args.extend(["-a", tag_name, "-m", message])
            else:
                args.append(tag_name)
            result = await self._run_git(workspace_path, args)
            return AgentResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr,
            )

        elif sub_action == "delete":
            if not tag_name:
                return AgentResult(success=False, error="Tag name required")
            result = await self._run_git(workspace_path, ["tag", "-d", tag_name])
            return AgentResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr,
            )

        return AgentResult(success=False, error=f"Unknown tag action: {sub_action}")

    async def _auto_commit(
        self, workspace_path: Path, context: AgentContext
    ) -> AgentResult:
        """Automatically commit changes with generated message."""
        # Check status first
        status = await self._git_status(workspace_path)
        if status.output.get("clean", True):
            return AgentResult(success=True, output={"message": "No changes to commit"})

        # Generate commit message
        diff_result = await self._run_git(workspace_path, ["diff"])
        message = await self._generate_commit_message(diff_result.stdout)

        # Stage and commit
        await self._run_git(workspace_path, ["add", "-A"])
        result = await self._run_git(workspace_path, ["commit", "-m", message])

        if result.returncode == 0:
            return AgentResult(
                success=True, output={"message": message, "commit": result.stdout}
            )
        return AgentResult(success=False, error=result.stderr)

    async def _generate_changelog(
        self, workspace_path: Path, context: AgentContext
    ) -> AgentResult:
        """Generate changelog from git history."""
        since = context.config.get("since")
        until = context.config.get("until", "HEAD")
        format_type = context.config.get("format", "markdown")

        args = [
            "log",
            "--pretty=format:%H|%an|%ad|%s",
            "--date=short",
            f"{since}..{until}" if since else until,
        ]
        result = await self._run_git(workspace_path, args)

        commits = []
        for line in result.stdout.splitlines():
            parts = line.split("|", 3)
            if len(parts) == 4:
                commits.append(
                    {
                        "hash": parts[0],
                        "author": parts[1],
                        "date": parts[2],
                        "message": parts[3],
                    }
                )

        # Categorize commits
        categories = {
            "Features": [],
            "Bug Fixes": [],
            "Documentation": [],
            "Refactoring": [],
            "Tests": [],
            "Chore": [],
            "Performance": [],
            "CI/CD": [],
            "Other": [],
        }

        for commit in commits:
            msg = commit["message"].lower()
            if msg.startswith("feat"):
                categories["Features"].append(commit)
            elif msg.startswith("fix"):
                categories["Bug Fixes"].append(commit)
            elif msg.startswith("docs"):
                categories["Documentation"].append(commit)
            elif msg.startswith("refactor"):
                categories["Refactoring"].append(commit)
            elif msg.startswith("test"):
                categories["Tests"].append(commit)
            elif msg.startswith("perf"):
                categories["Performance"].append(commit)
            elif msg.startswith("ci") or msg.startswith("build"):
                categories["CI/CD"].append(commit)
            elif msg.startswith("chore"):
                categories["Chore"].append(commit)
            else:
                categories["Other"].append(commit)

        if format_type == "markdown":
            changelog = "# Changelog\n\n"
            for category, cat_commits in categories.items():
                if cat_commits:
                    changelog += f"## {category}\n\n"
                    for commit in cat_commits:
                        changelog += f"- {commit['message']} ({commit['hash'][:7]})\n"
                    changelog += "\n"
        else:
            changelog = json.dumps(categories, indent=2)

        return AgentResult(
            success=True, output={"changelog": changelog, "commits": commits}
        )
