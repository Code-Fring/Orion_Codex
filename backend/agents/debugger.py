"""Debugger agent for finding and fixing bugs."""

import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Any

from backend.agents.base import AgentContext, AgentResult, BaseAgent
from backend.core.model_manager import AgentRole, model_manager
from backend.core.providers.interfaces import ChatMessage

logger = logging.getLogger(__name__)


class DebuggerAgent(BaseAgent):
    """Agent for debugging code, analyzing errors, and fixing bugs."""

    def __init__(
        self,
        name: str = "debugger_agent",
        description: str = "Finds and fixes bugs",
        config: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(name=name, description=description, config=config)

    @property
    def agent_type(self) -> str:
        return "debugger"

    async def execute(self, context: AgentContext) -> AgentResult:
        """Debug and fix issues in the codebase."""
        builder_output = context.previous_outputs.get(
            "builder"
        ) or context.previous_outputs.get("coder")
        tester_output = context.previous_outputs.get("tester")
        plan = context.previous_outputs.get("planner")
        error_logs = context.config.get("error_logs", "")
        specific_issue = context.config.get("issue", "")

        if not builder_output:
            return AgentResult(success=False, error="No code to debug")

        generated_files = builder_output.get("generated_files", [])
        if not generated_files:
            return AgentResult(success=False, error="No files to debug")

        provider_info = model_manager.get_model_for_role(AgentRole.DEBUGGING)
        if not provider_info:
            return AgentResult(
                success=False, error="No model assigned for debugging role"
            )

        provider, model_id = provider_info
        temperature = model_manager.get_temperature_for_role(AgentRole.DEBUGGING)
        max_tokens = model_manager.get_max_tokens_for_role(AgentRole.DEBUGGING)

        workspace_path = Path(context.workspace_path)
        fixed_files = []
        errors = []
        all_fixes = []

        # Collect error information from test results
        test_errors = self._extract_test_errors(tester_output)

        # Also run build/lint to find issues
        build_errors = await self._run_build_checks(workspace_path, plan)

        for file_rel in generated_files:
            file_path = workspace_path / file_rel
            if not file_path.exists():
                continue

            # Get relevant errors for this file
            file_test_errors = [e for e in test_errors if e.get("file") == file_rel]
            file_build_errors = [e for e in build_errors if e.get("file") == file_rel]

            if file_test_errors or file_build_errors or specific_issue or error_logs:
                result = await self._debug_file(
                    provider,
                    model_id,
                    file_path,
                    file_test_errors,
                    file_build_errors,
                    specific_issue,
                    error_logs,
                    plan,
                    temperature,
                    max_tokens,
                )
                if result.success:
                    fixed_files.append(str(file_path.relative_to(workspace_path)))
                    all_fixes.append(result.output)
                else:
                    errors.append(f"{file_rel}: {result.error}")

        # If no specific errors but we have error logs, do a general pass
        if not fixed_files and (error_logs or specific_issue):
            for file_rel in generated_files:
                file_path = workspace_path / file_rel
                if not file_path.exists():
                    continue
                result = await self._debug_file(
                    provider,
                    model_id,
                    file_path,
                    [],
                    [],
                    specific_issue,
                    error_logs,
                    plan,
                    temperature,
                    max_tokens,
                )
                if result.success:
                    fixed_files.append(str(file_path.relative_to(workspace_path)))
                    all_fixes.append(result.output)

        return AgentResult(
            success=len(errors) == 0,
            output={
                "fixed_files": fixed_files,
                "fixes": all_fixes,
                "errors": errors,
            },
            error="; ".join(errors) if errors else None,
            metadata={"model_used": model_id, "provider": provider.provider_name},
        )

    def _extract_test_errors(
        self, tester_output: dict[str, Any] | None
    ) -> list[dict[str, Any]]:
        """Extract error information from test results."""
        errors = []
        if not tester_output:
            return errors

        test_results = tester_output.get("test_results", [])
        for result in test_results:
            if not result.get("success", False):
                errors.append(
                    {
                        "file": result.get(
                            "source_file", result.get("test_file", "unknown")
                        ),
                        "type": "test_failure",
                        "error": result.get("error", "Test failed"),
                        "output": result.get("output", ""),
                    }
                )
        return errors

    async def _run_build_checks(
        self, workspace_path: Path, plan: dict[str, Any] | None
    ) -> list[dict[str, Any]]:
        """Run build/lint checks to find issues."""
        errors = []
        tech_stack = plan.get("tech_stack", {}) if plan else {}
        language = tech_stack.get("language", "python")

        try:
            if language == "python":
                # Run mypy for type checking
                result = subprocess.run(
                    ["python", "-m", "mypy", ".", "--ignore-missing-imports"],
                    cwd=workspace_path,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if result.returncode != 0:
                    for line in result.stdout.splitlines():
                        match = re.match(r"(.+):(\d+):\s*(error|warning):\s*(.+)", line)
                        if match:
                            file_path, line_num, severity, message = match.groups()
                            try:
                                rel_path = str(
                                    Path(file_path).relative_to(workspace_path)
                                )
                            except ValueError:
                                rel_path = file_path
                            errors.append(
                                {
                                    "file": rel_path,
                                    "type": "type_error",
                                    "line": int(line_num),
                                    "severity": severity,
                                    "message": message,
                                }
                            )

                # Run ruff for linting
                result = subprocess.run(
                    ["python", "-m", "ruff", "check", "."],
                    cwd=workspace_path,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.returncode != 0:
                    for line in result.stdout.splitlines():
                        match = re.match(r"(.+):(\d+):(\d+):\s*(.+)", line)
                        if match:
                            file_path, line_num, col_num, message = match.groups()
                            try:
                                rel_path = str(
                                    Path(file_path).relative_to(workspace_path)
                                )
                            except ValueError:
                                rel_path = file_path
                            errors.append(
                                {
                                    "file": rel_path,
                                    "type": "lint_error",
                                    "line": int(line_num),
                                    "message": message,
                                }
                            )

            elif language in ("javascript", "typescript"):
                # Run eslint
                result = subprocess.run(
                    ["npx", "eslint", ".", "--ext", ".js,.ts,.jsx,.tsx"],
                    cwd=workspace_path,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if result.returncode != 0:
                    # Parse eslint output
                    for line in result.stdout.splitlines():
                        if ":" in line and (
                            "error" in line.lower() or "warning" in line.lower()
                        ):
                            parts = line.split(":", 3)
                            if len(parts) >= 4:
                                file_path = parts[0]
                                line_num = parts[1]
                                try:
                                    rel_path = str(
                                        Path(file_path).relative_to(workspace_path)
                                    )
                                except ValueError:
                                    rel_path = file_path
                                errors.append(
                                    {
                                        "file": rel_path,
                                        "type": "lint_error",
                                        "line": int(line_num)
                                        if line_num.isdigit()
                                        else 0,
                                        "message": parts[3].strip(),
                                    }
                                )

        except subprocess.TimeoutExpired:
            errors.append(
                {
                    "file": "unknown",
                    "type": "timeout",
                    "message": "Build check timed out",
                }
            )
        except Exception as e:
            logger.debug(f"Build check failed: {e}")

        return errors

    async def _debug_file(
        self,
        provider,
        model_id: str,
        file_path: Path,
        test_errors: list[dict[str, Any]],
        build_errors: list[dict[str, Any]],
        specific_issue: str,
        error_logs: str,
        plan: dict[str, Any] | None,
        temperature: float,
        max_tokens: int | None,
    ) -> AgentResult:
        """Debug and fix a single file."""
        try:
            source_code = file_path.read_text(encoding="utf-8")
            tech_stack = plan.get("tech_stack", {}) if plan else {}
            language = tech_stack.get("language", "python")

            # Build error context
            error_context = ""
            if test_errors:
                error_context += "TEST ERRORS:\n"
                for err in test_errors:
                    error_context += f"  - {err.get('error', 'Unknown error')}\n"
                    if err.get("output"):
                        error_context += f"    Output: {err['output'][:500]}\n"

            if build_errors:
                error_context += "\nBUILD/LINT ERRORS:\n"
                for err in build_errors:
                    line_info = f" (line {err['line']})" if err.get("line") else ""
                    error_context += f"  - {err['file']}{line_info}: {err['message']}\n"

            if specific_issue:
                error_context += f"\nSPECIFIC ISSUE TO FIX:\n{specific_issue}\n"

            if error_logs:
                error_context += f"\nERROR LOGS:\n{error_logs}\n"

            system_prompt = f"""You are an expert debugger. Analyze the code and fix all issues.

Language: {language}
Framework: {tech_stack.get("framework", "N/A")}

{error_context}

Requirements:
1. Fix ALL identified issues
2. Maintain existing functionality
3. Add proper error handling
4. Fix type errors and lint issues
5. Ensure tests would pass
6. Follow {language} best practices
7. DO NOT change public APIs unless necessary
8. Return the COMPLETE fixed file content

Source Code ({language}):
```{language}
{source_code}
```

Return the complete fixed file content."""

            messages = [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=f"Debug and fix {file_path.name}"),
            ]

            response = await provider.chat(
                messages=messages,
                model=model_id,
                temperature=temperature,
                max_tokens=max_tokens or 8000,
            )

            file_path.write_text(response.content, encoding="utf-8")
            return AgentResult(
                success=True,
                output={"file": str(file_path), "fixes_applied": error_context[:200]},
            )
        except Exception as e:
            logger.error(f"Failed to debug {file_path}: {e}")
            return AgentResult(success=False, error=str(e))


class ErrorRecoveryAgent(BaseAgent):
    """Agent for automated error recovery and retry logic."""

    def __init__(
        self,
        name: str = "error_recovery_agent",
        description: str = "Recovers from pipeline failures",
        config: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(name=name, description=description, config=config)

    @property
    def agent_type(self) -> str:
        return "error_recovery"

    async def execute(self, context: AgentContext) -> AgentResult:
        """Implement error recovery for failed pipeline stages."""
        failed_stage = context.config.get("failed_stage")
        error_message = context.config.get("error_message")
        attempt = context.config.get("attempt", 1)
        max_attempts = context.config.get("max_attempts", 3)

        if not failed_stage or not error_message:
            return AgentResult(
                success=False, error="No failed stage or error message provided"
            )

        provider_info = model_manager.get_model_for_role(AgentRole.DEBUGGING)
        if not provider_info:
            return AgentResult(
                success=False, error="No model assigned for debugging role"
            )

        provider, model_id = provider_info
        temperature = model_manager.get_temperature_for_role(AgentRole.DEBUGGING)
        max_tokens = model_manager.get_max_tokens_for_role(AgentRole.DEBUGGING)

        # Get the output from the failed stage
        failed_output = context.previous_outputs.get(failed_stage, {})

        system_prompt = f"""You are an expert at error recovery. Analyze the failure and provide a fix.

Failed Stage: {failed_stage}
Attempt: {attempt}/{max_attempts}
Error: {error_message}

Previous Output: {json.dumps(failed_output, indent=2)[:3000]}

Provide a JSON response with:
{{
  "root_cause": "Analysis of the root cause",
  "fix_strategy": "Strategy to fix the issue",
  "code_changes": [
    {{"file": "path/to/file", "change": "Description of change", "new_content": "Full new content"}}
  ],
  "configuration_changes": ["Description of config changes needed"],
  "retry_recommended": true,
  "confidence": 0.8
}}"""

        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content="Analyze and provide recovery plan"),
        ]

        try:
            response = await provider.chat(
                messages=messages,
                model=model_id,
                temperature=temperature,
                max_tokens=max_tokens or 4000,
            )

            recovery_plan = json.loads(response.content)

            return AgentResult(
                success=True,
                output=recovery_plan,
                metadata={"model_used": model_id, "provider": provider.provider_name},
            )
        except Exception as e:
            logger.error(f"Error recovery failed: {e}")
            return AgentResult(success=False, error=str(e))
