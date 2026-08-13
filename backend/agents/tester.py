"""Tester agent for generating and running tests."""

import logging
import subprocess
from pathlib import Path
from typing import Any

from backend.agents.base import AgentContext, AgentResult, BaseAgent
from backend.core.providers.interfaces import ChatMessage
from backend.core.providers.registry import provider_registry

logger = logging.getLogger(__name__)


class TesterAgent(BaseAgent):
    """Agent for generating and running tests."""

    def __init__(
        self,
        name: str = "tester_agent",
        description: str = "Generates and runs tests",
        config: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(name=name, description=description, config=config)

    @property
    def agent_type(self) -> str:
        return "tester"

    async def execute(self, context: AgentContext) -> AgentResult:
        """Generate and run tests for the project."""
        plan = context.previous_outputs.get("planner")
        builder_output = context.previous_outputs.get("builder")

        if not plan or not builder_output:
            return AgentResult(success=False, error="Missing plan or builder output")

        generated_files = builder_output.get("generated_files", [])
        if not generated_files:
            return AgentResult(success=False, error="No files to test")

        chat_providers = provider_registry.get_chat_providers()
        if not chat_providers:
            return AgentResult(success=False, error="No chat providers available")

        provider = chat_providers[0]
        models = provider_registry.get_cached_models(provider.provider_name)
        if not models:
            models = await provider.list_models()

        model = next(
            (
                m
                for m in models
                if "gpt-4" in m.id or "claude-3" in m.id or "nemotron" in m.id
            ),
            models[0],
        )

        workspace_path = Path(context.workspace_path)
        test_results = []
        errors = []

        # Generate tests for each source file
        for file_rel in generated_files:
            file_path = workspace_path / file_rel
            if not file_path.exists():
                continue

            # Only test source files, not config files
            if self._should_test(file_path):
                result = await self._generate_and_run_test(
                    provider, model, file_path, plan, workspace_path
                )
                test_results.append(result)
                if not result.get("success", False):
                    errors.append(result.get("error", "Unknown error"))

        # Run the test suite
        suite_result = await self._run_test_suite(workspace_path, plan)
        test_results.append(suite_result)
        if not suite_result.get("success", False):
            errors.append(suite_result.get("error", "Test suite failed"))

        return AgentResult(
            success=len(errors) == 0,
            output={"test_results": test_results},
            error="; ".join(errors) if errors else None,
            metadata={"model_used": model.id, "provider": provider.provider_name},
        )

    def _should_test(self, file_path: Path) -> bool:
        """Determine if a file should be tested."""
        # Skip test files, config files, documentation
        skip_patterns = [
            "test_",
            "_test.py",
            ".test.",
            ".spec.",
            "conftest.py",
            "pytest.ini",
            "pyproject.toml",
            "package.json",
            "tsconfig.json",
            "vite.config",
            ".md",
            ".txt",
            ".json",
            ".yaml",
            ".yml",
            ".env",
            ".gitignore",
            "Dockerfile",
            "docker-compose",
        ]

        file_str = str(file_path).lower()
        return not any(pattern in file_str for pattern in skip_patterns)

    async def _generate_and_run_test(
        self,
        provider,
        model,
        source_file: Path,
        plan: dict[str, Any],
        workspace_path: Path,
    ) -> dict[str, Any]:
        """Generate and run tests for a source file."""
        try:
            # Read source file
            source_code = source_file.read_text(encoding="utf-8")

            # Determine test framework
            tech_stack = plan.get("tech_stack", {})
            language = tech_stack.get("language", "python")
            test_framework = tech_stack.get(
                "testing", "pytest" if language == "python" else "jest"
            )

            # Generate test
            system_prompt = f"""You are an expert test engineer. Generate comprehensive tests for the following code.
Language: {language}
Test Framework: {test_framework}
Source File: {source_file.name}

Requirements:
1. Write complete, production-quality tests
2. Cover happy paths, edge cases, and error conditions
3. Use {test_framework} best practices
4. Include unit tests and integration tests where appropriate
5. Mock external dependencies
6. Follow AAA pattern (Arrange, Act, Assert)
7. Add descriptive test names
8. DO NOT include placeholder tests

Source Code:
```{language}
{source_code}
```

Generate the complete test file content now."""

            messages = [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(
                    role="user", content=f"Generate tests for {source_file.name}"
                ),
            ]

            response = await provider.chat(
                messages=messages,
                model=model.id,
                temperature=0.2,
                max_tokens=4000,
            )

            # Write test file
            test_file = self._get_test_file_path(source_file, workspace_path, language)
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_text(response.content, encoding="utf-8")

            # Run the test
            run_result = await self._run_single_test(
                test_file, workspace_path, language, test_framework
            )

            return {
                "source_file": str(source_file.relative_to(workspace_path)),
                "test_file": str(test_file.relative_to(workspace_path)),
                "success": run_result["success"],
                "output": run_result.get("output", ""),
                "error": run_result.get("error"),
            }
        except Exception as e:
            logger.error(f"Failed to generate/run test for {source_file}: {e}")
            return {
                "source_file": str(source_file.relative_to(workspace_path)),
                "success": False,
                "error": str(e),
            }

    def _get_test_file_path(
        self, source_file: Path, workspace_path: Path, language: str
    ) -> Path:
        """Get the test file path for a source file."""
        rel_path = source_file.relative_to(workspace_path)

        if language == "python":
            # tests/unit/test_module.py
            test_dir = workspace_path / "tests" / "unit"
            test_name = f"test_{rel_path.stem}.py"
            return test_dir / test_name
        elif language in ("javascript", "typescript"):
            # tests/unit/module.test.ts
            test_dir = workspace_path / "tests" / "unit"
            test_name = f"{rel_path.stem}.test.{rel_path.suffix[1:]}"
            return test_dir / test_name
        else:
            # Generic
            test_dir = workspace_path / "tests"
            test_name = f"test_{rel_path.name}"
            return test_dir / test_name

    async def _run_single_test(
        self,
        test_file: Path,
        workspace_path: Path,
        language: str,
        test_framework: str,
    ) -> dict[str, Any]:
        """Run a single test file."""
        try:
            if language == "python" and test_framework == "pytest":
                cmd = ["python", "-m", "pytest", str(test_file), "-v", "--tb=short"]
            elif language in ("javascript", "typescript") and test_framework == "jest":
                cmd = ["npx", "jest", str(test_file), "--verbose"]
            else:
                return {
                    "success": False,
                    "error": f"Unsupported language/framework: {language}/{test_framework}",
                }

            result = subprocess.run(
                cmd,
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=120,
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Test timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _run_test_suite(
        self,
        workspace_path: Path,
        plan: dict[str, Any],
    ) -> dict[str, Any]:
        """Run the full test suite."""
        try:
            tech_stack = plan.get("tech_stack", {})
            language = tech_stack.get("language", "python")
            test_framework = tech_stack.get(
                "testing", "pytest" if language == "python" else "jest"
            )

            if language == "python" and test_framework == "pytest":
                cmd = [
                    "python",
                    "-m",
                    "pytest",
                    "tests/",
                    "-v",
                    "--tb=short",
                ]
            elif language in ("javascript", "typescript") and test_framework == "jest":
                cmd = ["npx", "jest", "--verbose", "--coverage"]
            else:
                return {"success": True, "output": "No test suite configured"}

            result = subprocess.run(
                cmd,
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=300,
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Test suite timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}
