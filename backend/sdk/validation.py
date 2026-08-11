"""Validation API for plugins."""

from typing import Any

from backend.validation.build_validator import BuildValidationReport, BuildValidator


class ValidationAPI:
    """API for validation operations."""

    def __init__(self, project_id: str, workspace_path: str) -> None:
        self.project_id = project_id
        self.workspace_path = workspace_path
        self._validator = BuildValidator()

    def create_validator(self) -> BuildValidator:
        """Create a new validator instance."""
        return BuildValidator()

    def validate_file(self, file_path: str, language: str) -> dict[str, Any]:
        """Validate a single file."""
        # This would need implementation in build_validator
        return {"success": True, "message": "File validation not yet implemented"}

    def validate_project(self, language: str | None = None) -> BuildValidationReport:
        """Validate entire project."""
        from backend.validation.build_validator import build_validator
        if language is None:
            language = build_validator._detect_language(self.workspace_path)
        return build_validator.validate(self.workspace_path, language)

    def get_validation_rules(self, language: str) -> list[dict[str, Any]]:
        """Get validation rules for a language."""
        # Return available rules
        return [
            {"name": "build", "description": "Build the project"},
            {"name": "lint", "description": "Run linter"},
            {"name": "test", "description": "Run tests"},
            {"name": "typecheck", "description": "Run type checker"},
            {"name": "security_check", "description": "Security scan"},
            {"name": "vulnerability_check", "description": "Dependency vulnerability check"},
        ]
