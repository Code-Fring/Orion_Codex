"""Workspace manager for project isolation and management."""

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.config.settings import settings

logger = logging.getLogger(__name__)


class WorkspaceManager:
    """Manages project workspaces."""

    def __init__(self, root_path: Path | None = None) -> None:
        self.root_path = root_path or Path(settings.WORKSPACE_ROOT)
        self.root_path.mkdir(parents=True, exist_ok=True)
        self._workspaces: dict[str, Path] = {}

    def create_workspace(self, project_id: str, name: str) -> Path:
        """Create a new workspace for a project."""
        workspace_name = f"{name}_{project_id[:8]}"
        workspace_path = self.root_path / workspace_name

        # Create standard directory structure
        directories = [
            "source",
            "tests",
            "assets",
            "logs",
            "exports",
        ]

        for dir_name in directories:
            (workspace_path / dir_name).mkdir(parents=True, exist_ok=True)

        # Create workspace metadata
        metadata = {
            "project_id": project_id,
            "name": name,
            "created_at": datetime.utcnow().isoformat(),
            "version": "1.0",
        }

        import json

        (workspace_path / "workspace.json").write_text(json.dumps(metadata, indent=2))

        self._workspaces[project_id] = workspace_path
        logger.info(f"Created workspace: {workspace_path}")

        return workspace_path

    def get_workspace(self, project_id: str) -> Path | None:
        """Get workspace path for a project."""
        if project_id in self._workspaces:
            return self._workspaces[project_id]

        # Try to find existing workspace
        for workspace_dir in self.root_path.iterdir():
            if workspace_dir.is_dir():
                metadata_file = workspace_dir / "workspace.json"
                if metadata_file.exists():
                    import json

                    metadata = json.loads(metadata_file.read_text())
                    if metadata.get("project_id") == project_id:
                        self._workspaces[project_id] = workspace_dir
                        return workspace_dir

        return None

    def delete_workspace(self, project_id: str) -> bool:
        """Delete a workspace."""
        workspace_path = self.get_workspace(project_id)
        if not workspace_path:
            return False

        try:
            shutil.rmtree(workspace_path)
            del self._workspaces[project_id]
            logger.info(f"Deleted workspace: {workspace_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete workspace {workspace_path}: {e}")
            return False

    def list_workspaces(self) -> list[dict[str, Any]]:
        """List all workspaces."""
        workspaces = []
        for workspace_dir in self.root_path.iterdir():
            if workspace_dir.is_dir():
                metadata_file = workspace_dir / "workspace.json"
                if metadata_file.exists():
                    import json

                    try:
                        metadata = json.loads(metadata_file.read_text())
                        metadata["path"] = str(workspace_dir)
                        metadata["size_mb"] = self._get_directory_size(workspace_dir)
                        workspaces.append(metadata)
                    except Exception:
                        pass
        return workspaces

    def _get_directory_size(self, path: Path) -> float:
        """Get directory size in MB."""
        total_size = 0
        for file_path in path.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return round(total_size / (1024 * 1024), 2)

    def get_workspace_structure(self, project_id: str) -> dict[str, Any] | None:
        """Get workspace directory structure."""
        workspace_path = self.get_workspace(project_id)
        if not workspace_path:
            return None

        structure = {}
        for item in workspace_path.rglob("*"):
            rel_path = item.relative_to(workspace_path)
            if item.is_dir():
                structure[str(rel_path)] = {"type": "directory", "children": {}}
            else:
                structure[str(rel_path)] = {
                    "type": "file",
                    "size": item.stat().st_size,
                    "modified": datetime.fromtimestamp(
                        item.stat().st_mtime
                    ).isoformat(),
                }
        return structure

    def read_file(self, project_id: str, file_path: str) -> str | None:
        """Read a file from workspace."""
        workspace_path = self.get_workspace(project_id)
        if not workspace_path:
            return None

        full_path = workspace_path / file_path
        if not full_path.exists() or not full_path.is_file():
            return None

        try:
            return full_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return None

    def write_file(self, project_id: str, file_path: str, content: str) -> bool:
        """Write a file to workspace."""
        workspace_path = self.get_workspace(project_id)
        if not workspace_path:
            return False

        full_path = workspace_path / file_path
        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            return True
        except Exception as e:
            logger.error(f"Failed to write file {file_path}: {e}")
            return False

    def archive_workspace(self, project_id: str, output_path: Path) -> bool:
        """Archive workspace to a zip file."""
        workspace_path = self.get_workspace(project_id)
        if not workspace_path:
            return False

        try:
            import zipfile

            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for file_path in workspace_path.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(workspace_path)
                        zipf.write(file_path, arcname)
            return True
        except Exception as e:
            logger.error(f"Failed to archive workspace: {e}")
            return False


# Global workspace manager
workspace_manager = WorkspaceManager()
