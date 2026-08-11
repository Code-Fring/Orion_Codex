"""Workspace API for plugins."""

from pathlib import Path
from typing import Any

from backend.workspace.manager import workspace_manager


class WorkspaceAPI:
    """API for workspace operations."""

    def __init__(self, project_id: str) -> None:
        self.project_id = project_id

    def get_workspace_path(self) -> Path | None:
        """Get workspace path for current project."""
        return workspace_manager.get_workspace(self.project_id)

    def create_workspace(self, name: str) -> Path:
        """Create a new workspace."""
        return workspace_manager.create_workspace(self.project_id, name)

    def read_file(self, file_path: str) -> str | None:
        """Read a file from workspace."""
        return workspace_manager.read_file(self.project_id, file_path)

    def write_file(self, file_path: str, content: str) -> bool:
        """Write a file to workspace."""
        return workspace_manager.write_file(self.project_id, file_path, content)

    def list_files(self, directory: str = "") -> list[dict[str, Any]]:
        """List files in workspace."""
        structure = workspace_manager.get_workspace_structure(self.project_id)
        if not structure:
            return []

        results = []
        base_path = Path(directory) if directory else Path(".")

        def walk(node: dict[str, Any], current_path: Path) -> None:
            for name, info in node.items():
                full_path = current_path / name
                if info["type"] == "file":
                    results.append({
                        "path": str(full_path),
                        "size": info.get("size", 0),
                        "modified": info.get("modified"),
                    })
                else:
                    walk(info.get("children", {}), full_path)

        walk(structure, base_path)
        return results

    def get_structure(self) -> dict[str, Any] | None:
        """Get workspace directory structure."""
        return workspace_manager.get_workspace_structure(self.project_id)

    def file_exists(self, file_path: str) -> bool:
        """Check if file exists."""
        ws = workspace_manager.get_workspace(self.project_id)
        if not ws:
            return False
        return (ws / file_path).exists()

    def delete_file(self, file_path: str) -> bool:
        """Delete a file from workspace."""
        ws = workspace_manager.get_workspace(self.project_id)
        if not ws:
            return False
        full_path = ws / file_path
        try:
            full_path.unlink()
            return True
        except Exception:
            return False

    def create_directory(self, dir_path: str) -> bool:
        """Create a directory in workspace."""
        ws = workspace_manager.get_workspace(self.project_id)
        if not ws:
            return False
        try:
            (ws / dir_path).mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False

    def archive_workspace(self, output_path: Path) -> bool:
        """Archive workspace to zip."""
        return workspace_manager.archive_workspace(self.project_id, output_path)
