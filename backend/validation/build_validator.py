"""Build validation pipeline for ensuring code quality."""

import json
import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation step."""

    name: str
    success: bool
    output: str = ""
    error: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 0


@dataclass
class BuildValidationReport:
    """Complete build validation report."""

    project_path: str
    overall_success: bool
    results: list[ValidationResult] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_path": self.project_path,
            "overall_success": self.overall_success,
            "results": [
                {
                    "name": r.name,
                    "success": r.success,
                    "output": r.output,
                    "error": r.error,
                    "details": r.details,
                    "duration_ms": r.duration_ms,
                }
                for r in self.results
            ],
            "summary": self.summary,
        }


class BuildValidator:
    """Validates that a project builds, passes linting, and tests pass."""

    def __init__(self) -> None:
        self.validators: dict[str, callable] = {
            "python": self._validate_python,
            "javascript": self._validate_javascript,
            "typescript": self._validate_typescript,
            "go": self._validate_go,
            "rust": self._validate_rust,
        }

    def validate(
        self, project_path: Path, language: str = None
    ) -> BuildValidationReport:
        """Run full validation pipeline."""
        if language is None:
            language = self._detect_language(project_path)

        validator = self.validators.get(language)
        if not validator:
            return BuildValidationReport(
                project_path=str(project_path),
                overall_success=False,
                results=[
                    ValidationResult(
                        name="validator",
                        success=False,
                        error=f"No validator for language: {language}",
                    )
                ],
            )

        return validator(project_path)

    def _detect_language(self, project_path: Path) -> str:
        """Detect project language."""
        if (project_path / "pyproject.toml").exists() or (
            project_path / "requirements.txt"
        ).exists():
            return "python"
        elif (project_path / "package.json").exists():
            # Check if TypeScript
            if (project_path / "tsconfig.json").exists():
                return "typescript"
            return "javascript"
        elif (project_path / "go.mod").exists():
            return "go"
        elif (project_path / "Cargo.toml").exists():
            return "rust"
        return "python"  # Default

    def _validate_python(self, project_path: Path) -> BuildValidationReport:
        """Validate Python project."""
        results = []

        # 1. Check if dependencies can be installed
        results.append(
            self._run_step(
                "dependency_install",
                project_path,
                ["pip", "install", "-q", "-r", "requirements.txt"]
                if (project_path / "requirements.txt").exists()
                else ["pip", "install", "-q", "-e", "."]
                if (project_path / "pyproject.toml").exists()
                else ["echo", "No dependency file found"],
            )
        )

        # 2. Run type checking (mypy)
        results.append(
            self._run_step(
                "type_check",
                project_path,
                [
                    "python",
                    "-m",
                    "mypy",
                    ".",
                    "--ignore-missing-imports",
                    "--no-error-summary",
                ],
            )
        )

        # 3. Run linting (ruff)
        results.append(
            self._run_step("lint", project_path, ["python", "-m", "ruff", "check", "."])
        )

        # 4. Run formatting check (ruff format)
        results.append(
            self._run_step(
                "format_check",
                project_path,
                ["python", "-m", "ruff", "format", "--check", "."],
            )
        )

        # 5. Run tests
        results.append(
            self._run_step(
                "test",
                project_path,
                ["python", "-m", "pytest", "tests/", "-v", "--tb=short", "-x"],
            )
        )

        # 6. Check for security issues (bandit)
        results.append(
            self._run_step(
                "security_check",
                project_path,
                ["python", "-m", "bandit", "-r", ".", "-f", "json", "-q"],
                optional=True,
            )
        )

        # 7. Check for dependency vulnerabilities (safety)
        results.append(
            self._run_step(
                "vulnerability_check",
                project_path,
                ["python", "-m", "safety", "check", "--json"],
                optional=True,
            )
        )

        overall_success = all(
            r.success
            for r in results
            if r.name not in ["security_check", "vulnerability_check"]
        )

        return BuildValidationReport(
            project_path=str(project_path),
            overall_success=overall_success,
            results=results,
            summary=self._generate_summary(results),
        )

    def _validate_javascript(self, project_path: Path) -> BuildValidationReport:
        """Validate JavaScript project."""
        results = []

        # 1. Install dependencies
        results.append(
            self._run_step("dependency_install", project_path, ["npm", "ci"])
        )

        # 2. Run linting (eslint)
        results.append(
            self._run_step(
                "lint", project_path, ["npx", "eslint", ".", "--ext", ".js,.jsx"]
            )
        )

        # 3. Run tests
        results.append(
            self._run_step(
                "test",
                project_path,
                ["npm", "test", "--", "--coverage", "--watchAll=false"],
            )
        )

        # 4. Build check
        if (project_path / "package.json").exists():
            pkg = json.loads((project_path / "package.json").read_text())
            if "build" in pkg.get("scripts", {}):
                results.append(
                    self._run_step("build", project_path, ["npm", "run", "build"])
                )

        overall_success = all(r.success for r in results)

        return BuildValidationReport(
            project_path=str(project_path),
            overall_success=overall_success,
            results=results,
            summary=self._generate_summary(results),
        )

    def _validate_typescript(self, project_path: Path) -> BuildValidationReport:
        """Validate TypeScript project."""
        results = []

        # 1. Install dependencies
        results.append(
            self._run_step("dependency_install", project_path, ["npm", "ci"])
        )

        # 2. Type check (tsc)
        results.append(
            self._run_step("type_check", project_path, ["npx", "tsc", "--noEmit"])
        )

        # 3. Run linting
        results.append(
            self._run_step(
                "lint", project_path, ["npx", "eslint", ".", "--ext", ".ts,.tsx"]
            )
        )

        # 4. Run tests
        results.append(
            self._run_step(
                "test",
                project_path,
                ["npm", "test", "--", "--coverage", "--watchAll=false"],
            )
        )

        # 5. Build check
        if (project_path / "package.json").exists():
            pkg = json.loads((project_path / "package.json").read_text())
            if "build" in pkg.get("scripts", {}):
                results.append(
                    self._run_step("build", project_path, ["npm", "run", "build"])
                )

        overall_success = all(r.success for r in results)

        return BuildValidationReport(
            project_path=str(project_path),
            overall_success=overall_success,
            results=results,
            summary=self._generate_summary(results),
        )

    def _validate_go(self, project_path: Path) -> BuildValidationReport:
        """Validate Go project."""
        results = []

        # 1. Download dependencies
        results.append(
            self._run_step(
                "dependency_install", project_path, ["go", "mod", "download"]
            )
        )

        # 2. Run vet
        results.append(self._run_step("vet", project_path, ["go", "vet", "./..."]))

        # 3. Run linting (golangci-lint if available)
        if shutil.which("golangci-lint"):
            results.append(
                self._run_step("lint", project_path, ["golangci-lint", "run"])
            )

        # 4. Run tests
        results.append(
            self._run_step("test", project_path, ["go", "test", "./...", "-v"])
        )

        # 5. Build
        results.append(self._run_step("build", project_path, ["go", "build", "./..."]))

        overall_success = all(r.success for r in results)

        return BuildValidationReport(
            project_path=str(project_path),
            overall_success=overall_success,
            results=results,
            summary=self._generate_summary(results),
        )

    def _validate_rust(self, project_path: Path) -> BuildValidationReport:
        """Validate Rust project."""
        results = []

        # 1. Check formatting
        results.append(
            self._run_step(
                "format_check", project_path, ["cargo", "fmt", "--", "--check"]
            )
        )

        # 2. Run clippy
        results.append(
            self._run_step(
                "lint", project_path, ["cargo", "clippy", "--", "-D", "warnings"]
            )
        )

        # 3. Run tests
        results.append(self._run_step("test", project_path, ["cargo", "test", "--all"]))

        # 4. Build
        results.append(
            self._run_step("build", project_path, ["cargo", "build", "--release"])
        )

        overall_success = all(r.success for r in results)

        return BuildValidationReport(
            project_path=str(project_path),
            overall_success=overall_success,
            results=results,
            summary=self._generate_summary(results),
        )

    def _run_step(
        self,
        name: str,
        project_path: Path,
        command: list[str],
        optional: bool = False,
        timeout: int = 300,
    ) -> ValidationResult:
        """Run a validation step."""
        import time

        start = time.time()

        try:
            result = subprocess.run(
                command,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            duration = int((time.time() - start) * 1000)
            success = result.returncode == 0

            if not success and optional:
                success = True  # Optional steps don't fail the build

            return ValidationResult(
                name=name,
                success=success,
                output=result.stdout[-5000:] if result.stdout else "",
                error=result.stderr[-5000:] if result.stderr else "",
                duration_ms=duration,
                details={"returncode": result.returncode, "command": " ".join(command)},
            )
        except subprocess.TimeoutExpired:
            return ValidationResult(
                name=name,
                success=False,
                error=f"Timeout after {timeout}s",
                duration_ms=int((time.time() - start) * 1000),
            )
        except Exception as e:
            return ValidationResult(
                name=name,
                success=False,
                error=str(e),
                duration_ms=int((time.time() - start) * 1000),
            )

    def _generate_summary(self, results: list[ValidationResult]) -> dict[str, Any]:
        """Generate summary from results."""
        passed = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)
        total_duration = sum(r.duration_ms for r in results)

        return {
            "total_steps": len(results),
            "passed": passed,
            "failed": failed,
            "success_rate": passed / len(results) if results else 0,
            "total_duration_ms": total_duration,
            "failed_steps": [r.name for r in results if not r.success],
        }


class AutoFixer:
    """Automatically fixes common validation issues."""

    def __init__(self) -> None:
        self.fixers: dict[str, dict[str, callable]] = {
            "python": {
                "format": self._fix_python_format,
                "lint": self._fix_python_lint,
                "imports": self._fix_python_imports,
            },
            "javascript": {
                "format": self._fix_js_format,
                "lint": self._fix_js_lint,
            },
            "typescript": {
                "format": self._fix_js_format,
                "lint": self._fix_js_lint,
            },
        }

    def fix(
        self, project_path: Path, language: str, issue_types: list[str] = None
    ) -> dict[str, Any]:
        """Auto-fix issues."""
        if language not in self.fixers:
            return {"success": False, "error": f"No fixer for language: {language}"}

        fixers = self.fixers[language]
        if issue_types is None:
            issue_types = list(fixers.keys())

        results = {}
        for issue_type in issue_types:
            if issue_type in fixers:
                try:
                    results[issue_type] = fixers[issue_type](project_path)
                except Exception as e:
                    results[issue_type] = {"success": False, "error": str(e)}

        return {"success": True, "results": results}

    def _fix_python_format(self, project_path: Path) -> dict[str, Any]:
        """Fix Python formatting with ruff."""
        result = subprocess.run(
            ["python", "-m", "ruff", "format", "."],
            cwd=project_path,
            capture_output=True,
            text=True,
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
        }

    def _fix_python_lint(self, project_path: Path) -> dict[str, Any]:
        """Fix Python lint issues with ruff."""
        result = subprocess.run(
            ["python", "-m", "ruff", "check", ".", "--fix"],
            cwd=project_path,
            capture_output=True,
            text=True,
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
        }

    def _fix_python_imports(self, project_path: Path) -> dict[str, Any]:
        """Fix Python imports with ruff."""
        result = subprocess.run(
            ["python", "-m", "ruff", "check", ".", "--select", "I", "--fix"],
            cwd=project_path,
            capture_output=True,
            text=True,
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
        }

    def _fix_js_format(self, project_path: Path) -> dict[str, Any]:
        """Fix JS/TS formatting with prettier."""
        result = subprocess.run(
            ["npx", "prettier", "--write", "."],
            cwd=project_path,
            capture_output=True,
            text=True,
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
        }

    def _fix_js_lint(self, project_path: Path) -> dict[str, Any]:
        """Fix JS/TS lint issues with eslint."""
        result = subprocess.run(
            ["npx", "eslint", ".", "--fix"],
            cwd=project_path,
            capture_output=True,
            text=True,
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
        }


# Global instances
build_validator = BuildValidator()
auto_fixer = AutoFixer()
