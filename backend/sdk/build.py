"""Build API for plugins."""

from pathlib import Path
from typing import Any

from backend.validation.build_validator import BuildValidationReport, auto_fixer, build_validator


class BuildAPI:
    """API for build operations."""

    def __init__(self, project_id: str, workspace_path: str) -> None:
        self.project_id = project_id
        self.workspace_path = workspace_path

    def detect_language(self) -> str:
        """Detect project language."""
        return build_validator._detect_language(Path(self.workspace_path))

    def validate(self, language: str | None = None) -> BuildValidationReport:
        """Validate project build."""
        lang = language or self.detect_language()
        return build_validator.validate(Path(self.workspace_path), lang)

    def auto_fix(self, language: str | None = None) -> dict[str, Any]:
        """Auto-fix build issues."""
        lang = language or self.detect_language()
        return auto_fixer.fix(Path(self.workspace_path), lang)

    def get_build_command(self, language: str) -> str | None:
        """Get build command for language."""
        return build_validator._get_build_command(language)

    def get_test_command(self, language: str) -> str | None:
        """Get test command for language."""
        return build_validator._get_test_command(language)

    def get_lint_command(self, language: str) -> str | None:
        """Get lint command for language."""
        return build_validator._get_lint_command(language)
