"""Shared project memory for all agents."""

import json
import logging
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ProjectMemory:
    """Shared project memory accessible by all agents."""

    project_id: str
    workspace_path: str

    # Project plan and architecture
    analysis: dict[str, Any] | None = None
    plan: dict[str, Any] | None = None
    architecture: dict[str, Any] | None = None
    architecture_review: dict[str, Any] | None = None

    # Code artifacts
    generated_files: list[str] = field(default_factory=list)
    file_contents: dict[str, str] = field(default_factory=dict)
    file_hashes: dict[str, str] = field(default_factory=dict)

    # Test results
    test_results: list[dict[str, Any]] = field(default_factory=list)
    test_coverage: dict[str, float] = field(default_factory=dict)

    # Code review
    code_reviews: list[dict[str, Any]] = field(default_factory=list)
    review_summary: dict[str, Any] | None = None

    # Security
    security_findings: list[dict[str, Any]] = field(default_factory=list)
    security_report: dict[str, Any] | None = None

    # Dependencies
    dependencies: dict[str, Any] = field(default_factory=dict)
    dependency_vulnerabilities: list[dict[str, Any]] = field(default_factory=list)
    outdated_packages: list[dict[str, Any]] = field(default_factory=list)

    # Debugging
    bugs_found: list[dict[str, Any]] = field(default_factory=list)
    fixes_applied: list[dict[str, Any]] = field(default_factory=list)

    # Git
    git_commits: list[dict[str, Any]] = field(default_factory=list)
    git_branches: list[str] = field(default_factory=list)
    git_status: dict[str, Any] | None = None

    # Deployment
    deployment_configs: list[str] = field(default_factory=list)
    deployment_artifacts: list[str] = field(default_factory=list)

    # Task tracking
    current_tasks: dict[str, dict[str, Any]] = field(default_factory=dict)
    completed_tasks: list[str] = field(default_factory=list)
    failed_tasks: list[dict[str, Any]] = field(default_factory=list)

    # Agent outputs
    agent_outputs: dict[str, Any] = field(default_factory=dict)

    # Coding conventions learned
    conventions: dict[str, Any] = field(default_factory=dict)

    # Known issues
    known_issues: list[dict[str, Any]] = field(default_factory=list)
    open_issues: list[dict[str, Any]] = field(default_factory=list)

    # Metadata
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "workspace_path": self.workspace_path,
            "analysis": self.analysis,
            "plan": self.plan,
            "architecture": self.architecture,
            "architecture_review": self.architecture_review,
            "generated_files": self.generated_files,
            "file_contents": self.file_contents,
            "file_hashes": self.file_hashes,
            "test_results": self.test_results,
            "test_coverage": self.test_coverage,
            "code_reviews": self.code_reviews,
            "review_summary": self.review_summary,
            "security_findings": self.security_findings,
            "security_report": self.security_report,
            "dependencies": self.dependencies,
            "dependency_vulnerabilities": self.dependency_vulnerabilities,
            "outdated_packages": self.outdated_packages,
            "bugs_found": self.bugs_found,
            "fixes_applied": self.fixes_applied,
            "git_commits": self.git_commits,
            "git_branches": self.git_branches,
            "git_status": self.git_status,
            "deployment_configs": self.deployment_configs,
            "deployment_artifacts": self.deployment_artifacts,
            "current_tasks": self.current_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "agent_outputs": self.agent_outputs,
            "conventions": self.conventions,
            "known_issues": self.known_issues,
            "open_issues": self.open_issues,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectMemory":
        memory = cls(
            project_id=data["project_id"],
            workspace_path=data["workspace_path"],
        )
        memory.analysis = data.get("analysis")
        memory.plan = data.get("plan")
        memory.architecture = data.get("architecture")
        memory.architecture_review = data.get("architecture_review")
        memory.generated_files = data.get("generated_files", [])
        memory.file_contents = data.get("file_contents", {})
        memory.file_hashes = data.get("file_hashes", {})
        memory.test_results = data.get("test_results", [])
        memory.test_coverage = data.get("test_coverage", {})
        memory.code_reviews = data.get("code_reviews", [])
        memory.review_summary = data.get("review_summary")
        memory.security_findings = data.get("security_findings", [])
        memory.security_report = data.get("security_report")
        memory.dependencies = data.get("dependencies", {})
        memory.dependency_vulnerabilities = data.get("dependency_vulnerabilities", [])
        memory.outdated_packages = data.get("outdated_packages", [])
        memory.bugs_found = data.get("bugs_found", [])
        memory.fixes_applied = data.get("fixes_applied", [])
        memory.git_commits = data.get("git_commits", [])
        memory.git_branches = data.get("git_branches", [])
        memory.git_status = data.get("git_status")
        memory.deployment_configs = data.get("deployment_configs", [])
        memory.deployment_artifacts = data.get("deployment_artifacts", [])
        memory.current_tasks = data.get("current_tasks", {})
        memory.completed_tasks = data.get("completed_tasks", [])
        memory.failed_tasks = data.get("failed_tasks", [])
        memory.agent_outputs = data.get("agent_outputs", {})
        memory.conventions = data.get("conventions", {})
        memory.known_issues = data.get("known_issues", [])
        memory.open_issues = data.get("open_issues", [])
        memory.created_at = data.get("created_at", datetime.utcnow().isoformat())
        memory.updated_at = data.get("updated_at", datetime.utcnow().isoformat())
        memory.version = data.get("version", 1)
        return memory


class SharedMemoryManager:
    """Manages shared project memory with thread-safe access."""

    def __init__(self, storage_path: Path | None = None) -> None:
        self.storage_path = storage_path or Path("./shared_memory")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._memories: dict[str, ProjectMemory] = {}
        self._locks: dict[str, threading.RLock] = defaultdict(threading.RLock)
        self._subscribers: dict[str, list[callable]] = defaultdict(list)

    def _get_lock(self, project_id: str) -> threading.RLock:
        return self._locks[project_id]

    def _get_memory_path(self, project_id: str) -> Path:
        return self.storage_path / f"{project_id}.json"

    def load_memory(self, project_id: str, workspace_path: str) -> ProjectMemory:
        """Load or create project memory."""
        with self._get_lock(project_id):
            if project_id in self._memories:
                return self._memories[project_id]

            memory_path = self._get_memory_path(project_id)
            if memory_path.exists():
                try:
                    with open(memory_path, "r") as f:
                        data = json.load(f)
                    memory = ProjectMemory.from_dict(data)
                    memory.workspace_path = workspace_path
                    self._memories[project_id] = memory
                    logger.info(f"Loaded shared memory for project {project_id}")
                    return memory
                except Exception as e:
                    logger.warning(f"Failed to load memory for {project_id}: {e}")

            # Create new memory
            memory = ProjectMemory(project_id=project_id, workspace_path=workspace_path)
            self._memories[project_id] = memory
            self.save_memory(project_id)
            return memory

    def save_memory(self, project_id: str) -> bool:
        """Save project memory to disk."""
        with self._get_lock(project_id):
            memory = self._memories.get(project_id)
            if not memory:
                return False

            memory.updated_at = datetime.utcnow().isoformat()
            memory.version += 1

            try:
                memory_path = self._get_memory_path(project_id)
                with open(memory_path, "w") as f:
                    json.dump(memory.to_dict(), f, indent=2)

                # Notify subscribers
                for callback in self._subscribers.get(project_id, []):
                    try:
                        callback(memory)
                    except Exception as e:
                        logger.warning(f"Subscriber callback failed: {e}")

                return True
            except Exception as e:
                logger.error(f"Failed to save memory for {project_id}: {e}")
                return False

    def get_memory(self, project_id: str) -> ProjectMemory | None:
        """Get project memory without loading."""
        with self._get_lock(project_id):
            return self._memories.get(project_id)

    def update_memory(self, project_id: str, updates: dict[str, Any]) -> bool:
        """Update specific fields in project memory."""
        with self._get_lock(project_id):
            memory = self._memories.get(project_id)
            if not memory:
                return False

            for key, value in updates.items():
                if hasattr(memory, key):
                    setattr(memory, key, value)

            return self.save_memory(project_id)

    def merge_agent_output(self, project_id: str, agent_type: str, output: Any) -> bool:
        """Merge agent output into shared memory."""
        with self._get_lock(project_id):
            memory = self._memories.get(project_id)
            if not memory:
                return False

            memory.agent_outputs[agent_type] = output

            # Update specific fields based on agent type
            if agent_type == "analysis":
                memory.analysis = output
            elif agent_type == "planner":
                memory.plan = output
            elif agent_type == "architect":
                memory.architecture = output
            elif agent_type == "architecture_reviewer":
                memory.architecture_review = output
            elif agent_type in ("coder", "builder", "refactoring"):
                if isinstance(output, dict):
                    files = output.get("generated_files") or output.get(
                        "refactored_files", []
                    )
                    memory.generated_files.extend(
                        f for f in files if f not in memory.generated_files
                    )
            elif agent_type == "tester":
                memory.test_results = output.get("test_results", [])
            elif agent_type == "reviewer":
                memory.code_reviews = output.get("reviews", [])
                memory.review_summary = output.get("summary")
            elif agent_type == "security":
                memory.security_findings = output.get("findings", [])
                memory.security_report = output.get("report")
            elif agent_type == "security_hardening":
                memory.fixes_applied.extend(output.get("fixed_files", []))
            elif agent_type == "dependency":
                memory.dependencies = output.get("dependencies", {})
                memory.dependency_vulnerabilities = output.get("vulnerabilities", [])
                memory.outdated_packages = output.get("outdated", [])
            elif agent_type == "debugger":
                memory.bugs_found.extend(output.get("fixes", []))
            elif agent_type == "git":
                memory.git_commits.extend(output.get("commits", []))
            elif agent_type == "deployer":
                memory.deployment_configs.extend(output.get("deployment_configs", []))
                memory.deployment_artifacts.extend(output.get("artifacts", []))

            return self.save_memory(project_id)

    def add_file_content(self, project_id: str, file_path: str, content: str) -> bool:
        """Add or update file content in memory."""
        with self._get_lock(project_id):
            memory = self._memories.get(project_id)
            if not memory:
                return False

            import hashlib

            memory.file_contents[file_path] = content
            memory.file_hashes[file_path] = hashlib.md5(content.encode()).hexdigest()

            if file_path not in memory.generated_files:
                memory.generated_files.append(file_path)

            return self.save_memory(project_id)

    def get_file_content(self, project_id: str, file_path: str) -> str | None:
        """Get file content from memory."""
        with self._get_lock(project_id):
            memory = self._memories.get(project_id)
            if not memory:
                return None
            return memory.file_contents.get(file_path)

    def has_file_changed(
        self, project_id: str, file_path: str, current_content: str
    ) -> bool:
        """Check if file has changed since last saved."""
        with self._get_lock(project_id):
            memory = self._memories.get(project_id)
            if not memory:
                return True

            import hashlib

            current_hash = hashlib.md5(current_content.encode()).hexdigest()
            return memory.file_hashes.get(file_path) != current_hash

    def add_task(
        self, project_id: str, task_id: str, task_info: dict[str, Any]
    ) -> bool:
        """Add a current task."""
        with self._get_lock(project_id):
            memory = self._memories.get(project_id)
            if not memory:
                return False

            memory.current_tasks[task_id] = task_info
            return self.save_memory(project_id)

    def complete_task(self, project_id: str, task_id: str) -> bool:
        """Mark a task as completed."""
        with self._get_lock(project_id):
            memory = self._memories.get(project_id)
            if not memory:
                return False

            if task_id in memory.current_tasks:
                memory.completed_tasks.append(task_id)
                del memory.current_tasks[task_id]
                return self.save_memory(project_id)
            return False

    def fail_task(self, project_id: str, task_id: str, error: str) -> bool:
        """Mark a task as failed."""
        with self._get_lock(project_id):
            memory = self._memories.get(project_id)
            if not memory:
                return False

            if task_id in memory.current_tasks:
                task_info = memory.current_tasks[task_id]
                memory.failed_tasks.append(
                    {"task_id": task_id, "info": task_info, "error": error}
                )
                del memory.current_tasks[task_id]
                return self.save_memory(project_id)
            return False

    def subscribe(self, project_id: str, callback: callable) -> None:
        """Subscribe to memory changes."""
        self._subscribers[project_id].append(callback)

    def unsubscribe(self, project_id: str, callback: callable) -> None:
        """Unsubscribe from memory changes."""
        if callback in self._subscribers.get(project_id, []):
            self._subscribers[project_id].remove(callback)

    def clear_memory(self, project_id: str) -> bool:
        """Clear all memory for a project."""
        with self._get_lock(project_id):
            if project_id in self._memories:
                del self._memories[project_id]

            memory_path = self._get_memory_path(project_id)
            if memory_path.exists():
                try:
                    memory_path.unlink()
                    return True
                except Exception as e:
                    logger.error(f"Failed to clear memory for {project_id}: {e}")
                    return False
            return True


# Global shared memory manager
shared_memory = SharedMemoryManager()
