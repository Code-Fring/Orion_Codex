"""Coder agent for implementing code with high quality."""

import logging
from pathlib import Path
from typing import Any

from backend.agents.base import AgentContext, AgentResult, BaseAgent
from backend.core.model_manager import AgentRole, model_manager
from backend.core.providers.interfaces import ChatMessage

logger = logging.getLogger(__name__)


class CoderAgent(BaseAgent):
    """Agent for writing production-quality code implementations."""

    def __init__(
        self,
        name: str = "coder_agent",
        description: str = "Implements production-quality code",
        config: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(name=name, description=description, config=config)

    @property
    def agent_type(self) -> str:
        return "coder"

    async def execute(self, context: AgentContext) -> AgentResult:
        """Generate code files based on architecture and plan."""
        architecture = context.previous_outputs.get("architect")
        plan = context.previous_outputs.get("planner")

        if not architecture and not plan:
            return AgentResult(success=False, error="No architecture or plan available")

        provider_info = model_manager.get_model_for_role(AgentRole.CODING)
        if not provider_info:
            return AgentResult(success=False, error="No model assigned for coding role")

        provider, model_id = provider_info
        temperature = model_manager.get_temperature_for_role(AgentRole.CODING)
        max_tokens = model_manager.get_max_tokens_for_role(AgentRole.CODING)

        workspace_path = Path(context.workspace_path)
        generated_files = []
        errors = []

        arch_components = (
            architecture.get("architecture", {}).get("components", [])
            if architecture
            else []
        )
        plan_file_structure = plan.get("file_structure", {}) if plan else {}
        tech_stack = plan.get("tech_stack", {}) if plan else {}

        # Generate files for each component
        for component in arch_components:
            comp_name = component.get("name", "")
            comp_type = component.get("type", "")
            comp_desc = component.get("description", "")
            comp_tech = component.get("technology", "")

            # Find relevant files in plan for this component
            comp_files = self._get_component_files(
                plan_file_structure, comp_name, comp_type
            )

            for file_rel in comp_files:
                file_path = workspace_path / file_rel
                result = await self._generate_file(
                    provider,
                    model_id,
                    file_path,
                    component,
                    tech_stack,
                    context,
                    temperature,
                    max_tokens,
                )
                if result.success:
                    generated_files.append(str(file_path.relative_to(workspace_path)))
                else:
                    errors.append(f"{file_rel}: {result.error}")

        # Generate remaining files from plan not covered by components
        all_planned_files = self._flatten_file_structure(plan_file_structure)
        for file_rel in all_planned_files:
            if file_rel not in generated_files:
                file_path = workspace_path / file_rel
                result = await self._generate_file(
                    provider,
                    model_id,
                    file_path,
                    {"name": "general", "type": "utility"},
                    tech_stack,
                    context,
                    temperature,
                    max_tokens,
                )
                if result.success:
                    generated_files.append(str(file_path.relative_to(workspace_path)))
                else:
                    errors.append(f"{file_rel}: {result.error}")

        if errors:
            return AgentResult(
                success=False,
                output={"generated_files": generated_files, "errors": errors},
                error=f"Failed to generate {len(errors)} files",
            )

        return AgentResult(
            success=True,
            output={"generated_files": generated_files},
            metadata={"model_used": model_id, "provider": provider.provider_name},
        )

    def _get_component_files(
        self, file_structure: dict[str, Any], component_name: str, component_type: str
    ) -> list[str]:
        """Get files relevant to a component from the file structure."""
        files = []

        def extract_files(structure: Any, prefix: str = "") -> list[str]:
            result = []
            if isinstance(structure, dict):
                for key, value in structure.items():
                    new_prefix = f"{prefix}/{key}" if prefix else key
                    if isinstance(value, list):
                        for item in value:
                            if isinstance(item, str):
                                result.append(
                                    f"{new_prefix}/{item}"
                                    if not item.endswith("/")
                                    else new_prefix
                                )
                            elif isinstance(item, dict):
                                result.extend(extract_files(item, new_prefix))
                    elif isinstance(value, dict):
                        result.extend(extract_files(value, new_prefix))
                    elif isinstance(value, str) and value:
                        result.append(f"{new_prefix}/{value}")
            elif isinstance(structure, list):
                for item in structure:
                    if isinstance(item, str):
                        result.append(f"{prefix}/{item}" if prefix else item)
            return result

        all_files = extract_files(file_structure)

        # Filter files by component name/type
        for f in all_files:
            f_lower = f.lower()
            if component_name.lower() in f_lower or component_type.lower() in f_lower:
                files.append(f)

        return files

    def _flatten_file_structure(self, structure: dict[str, Any]) -> list[str]:
        """Flatten file structure to list of file paths."""
        files = []

        def extract(structure: Any, prefix: str = ""):
            if isinstance(structure, dict):
                for key, value in structure.items():
                    new_prefix = f"{prefix}/{key}" if prefix else key
                    if isinstance(value, list):
                        for item in value:
                            if isinstance(item, str):
                                files.append(
                                    f"{new_prefix}/{item}"
                                    if not item.endswith("/")
                                    else new_prefix
                                )
                            elif isinstance(item, dict):
                                extract(item, new_prefix)
                    elif isinstance(value, dict):
                        extract(value, new_prefix)
                    elif isinstance(value, str) and value:
                        files.append(f"{new_prefix}/{value}")
            elif isinstance(structure, list):
                for item in structure:
                    if isinstance(item, str):
                        files.append(f"{prefix}/{item}" if prefix else item)

        extract(structure)
        return files

    async def _generate_file(
        self,
        provider,
        model_id: str,
        file_path: Path,
        component: dict[str, Any],
        tech_stack: dict[str, Any],
        context: AgentContext,
        temperature: float,
        max_tokens: int | None,
    ) -> AgentResult:
        """Generate a single file."""
        try:
            system_prompt = self._build_system_prompt(file_path, component, tech_stack)

            messages = [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(
                    role="user",
                    content=f"Generate the complete implementation for {file_path.name}",
                ),
            ]

            response = await provider.chat(
                messages=messages,
                model=model_id,
                temperature=temperature,
                max_tokens=max_tokens or 8000,
            )

            # Write the file
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(response.content, encoding="utf-8")

            return AgentResult(success=True, output=str(file_path))
        except Exception as e:
            logger.error(f"Failed to generate {file_path}: {e}")
            return AgentResult(success=False, error=str(e))

    def _build_system_prompt(
        self, file_path: Path, component: dict[str, Any], tech_stack: dict[str, Any]
    ) -> str:
        """Build system prompt for file generation."""
        language = tech_stack.get("language", "python")
        framework = tech_stack.get("framework", "")

        return f"""You are an expert {language} software engineer. Generate production-quality code for: {file_path.name}

Project Context:
- Language: {language}
- Framework: {framework}
- Component: {component.get("name", "general")} ({component.get("type", "utility")})
- Component Description: {component.get("description", "N/A")}
- Component Responsibilities: {", ".join(component.get("responsibilities", []))}
- Technology: {component.get("technology", "N/A")}

Requirements:
1. Write complete, production-ready code - NO placeholders, TODOs, or stubs
2. Follow {language} best practices and {framework} conventions
3. Include proper error handling, logging, and type hints
4. Follow SOLID principles, clean architecture, and design patterns
5. Add comprehensive docstrings and comments
6. Ensure code is secure, scalable, and maintainable
7. Include all necessary imports and dependencies
8. Handle edge cases and validate inputs
9. Use dependency injection where appropriate
10. Follow the project's coding standards

File: {file_path}
Language: {language}
Framework: {framework}

Generate the complete file content now."""


class CodeRefactoringAgent(BaseAgent):
    """Agent for refactoring existing code."""

    def __init__(
        self,
        name: str = "refactoring_agent",
        description: str = "Code refactoring agent",
        config: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(name=name, description=description, config=config)

    @property
    def agent_type(self) -> str:
        return "refactoring"

    async def execute(self, context: AgentContext) -> AgentResult:
        """Refactor code based on instructions."""
        builder_output = context.previous_outputs.get(
            "builder"
        ) or context.previous_outputs.get("coder")
        plan = context.previous_outputs.get("planner")
        refactor_instructions = context.config.get("refactor_instructions", "")

        if not builder_output:
            return AgentResult(success=False, error="No code to refactor")

        generated_files = builder_output.get("generated_files", [])
        if not generated_files:
            return AgentResult(success=False, error="No files to refactor")

        provider_info = model_manager.get_model_for_role(AgentRole.REFACTORING)
        if not provider_info:
            return AgentResult(
                success=False, error="No model assigned for refactoring role"
            )

        provider, model_id = provider_info
        temperature = model_manager.get_temperature_for_role(AgentRole.REFACTORING)
        max_tokens = model_manager.get_max_tokens_for_role(AgentRole.REFACTORING)

        workspace_path = Path(context.workspace_path)
        refactored_files = []
        errors = []

        for file_rel in generated_files:
            file_path = workspace_path / file_rel
            if not file_path.exists():
                continue

            result = await self._refactor_file(
                provider,
                model_id,
                file_path,
                refactor_instructions,
                plan,
                temperature,
                max_tokens,
            )
            if result.success:
                refactored_files.append(str(file_path.relative_to(workspace_path)))
            else:
                errors.append(f"{file_rel}: {result.error}")

        return AgentResult(
            success=len(errors) == 0,
            output={"refactored_files": refactored_files, "errors": errors},
            error="; ".join(errors) if errors else None,
            metadata={"model_used": model_id, "provider": provider.provider_name},
        )

    async def _refactor_file(
        self,
        provider,
        model_id: str,
        file_path: Path,
        instructions: str,
        plan: dict[str, Any],
        temperature: float,
        max_tokens: int | None,
    ) -> AgentResult:
        """Refactor a single file."""
        try:
            source_code = file_path.read_text(encoding="utf-8")
            tech_stack = plan.get("tech_stack", {}) if plan else {}
            language = tech_stack.get("language", "python")

            system_prompt = f"""You are an expert software engineer specializing in code refactoring. 
Refactor the following code according to the instructions.

Language: {language}
Framework: {tech_stack.get("framework", "N/A")}

Refactoring Instructions:
{instructions}

Requirements:
1. Maintain exact same functionality
2. Improve code quality, readability, and maintainability
3. Apply appropriate design patterns
4. Reduce complexity and duplication
5. Improve performance where possible
6. Add/update tests if needed
7. Keep all public APIs compatible
8. Follow {language} best practices

Source Code ({language}):
```{language}
{source_code}
```

Return the complete refactored file content."""

            messages = [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=f"Refactor {file_path.name}"),
            ]

            response = await provider.chat(
                messages=messages,
                model=model_id,
                temperature=temperature,
                max_tokens=max_tokens or 8000,
            )

            file_path.write_text(response.content, encoding="utf-8")
            return AgentResult(success=True, output=str(file_path))
        except Exception as e:
            logger.error(f"Failed to refactor {file_path}: {e}")
            return AgentResult(success=False, error=str(e))
