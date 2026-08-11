"""Code generator for creating project files."""

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class CodeGenerator:
    """Generates code files from templates and specifications."""

    def __init__(self, workspace_path: Path) -> None:
        self.workspace_path = workspace_path
        self.templates_dir = Path(__file__).parent / "templates"

    def generate_project_structure(self, structure: dict[str, Any]) -> list[Path]:
        """Generate project directory structure."""
        created_paths = []

        for path_str in structure.get("directories", []):
            path = self.workspace_path / path_str
            path.mkdir(parents=True, exist_ok=True)
            created_paths.append(path)

        return created_paths

    def generate_file(
        self,
        file_path: Path,
        content: str,
        overwrite: bool = True,
    ) -> bool:
        """Generate a single file."""
        try:
            full_path = self.workspace_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            if full_path.exists() and not overwrite:
                logger.warning(f"File exists, skipping: {file_path}")
                return False

            full_path.write_text(content, encoding="utf-8")
            logger.info(f"Generated file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to generate file {file_path}: {e}")
            return False

    def generate_from_template(
        self,
        template_name: str,
        file_path: Path,
        context: dict[str, Any],
    ) -> bool:
        """Generate a file from a template."""
        template_path = self.templates_dir / template_name
        if not template_path.exists():
            logger.error(f"Template not found: {template_name}")
            return False

        try:
            template_content = template_path.read_text(encoding="utf-8")
            # Simple template substitution
            content = template_content.format(**context)
            return self.generate_file(file_path, content)
        except Exception as e:
            logger.error(f"Failed to generate from template {template_name}: {e}")
            return False
