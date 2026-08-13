"""Builder agent for generating code files."""

import logging
from pathlib import Path
from typing import Any

from backend.agents.base import AgentContext, AgentResult, BaseAgent
from backend.core.providers.interfaces import ChatMessage
from backend.core.providers.registry import provider_registry

logger = logging.getLogger(__name__)


class BuilderAgent(BaseAgent):
    """Agent for generating code files based on the plan."""

    def __init__(
        self,
        name: str = "builder_agent",
        description: str = "Generates code files",
        config: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(name=name, description=description, config=config)

    @property
    def agent_type(self) -> str:
        return "builder"

    async def execute(self, context: AgentContext) -> AgentResult:
        """Generate code files for the project."""
        plan = context.previous_outputs.get("planner")
        if not plan:
            return AgentResult(success=False, error="No plan available")

        chat_providers = provider_registry.get_chat_providers()
        if not chat_providers:
            return AgentResult(success=False, error="No chat providers available")

        # Prefer code-specialized providers
        code_providers = provider_registry.get_code_providers()
        provider = code_providers[0] if code_providers else chat_providers[0]

        models = provider_registry.get_cached_models(provider.provider_name)
        if not models:
            models = await provider.list_models()

        model = next(
            (
                m
                for m in models
                if "code" in m.id.lower()
                or "coder" in m.id.lower()
                or "nemotron" in m.id
            ),
            models[0],
        )

        workspace_path = Path(context.workspace_path)
        generated_files = []
        errors = []

        # Generate files based on file_structure
        file_structure = plan.get("file_structure", {})

        for directory, files in file_structure.items():
            if directory == "root":
                continue
            dir_path = workspace_path / directory
            dir_path.mkdir(parents=True, exist_ok=True)

            if isinstance(files, list):
                # Simple list of files
                for file_name in files:
                    file_path = dir_path / file_name
                    result = await self._generate_file(
                        provider, model, file_path, plan, context, ""
                    )
                    if result.success:
                        generated_files.append(
                            str(file_path.relative_to(workspace_path))
                        )
                    else:
                        errors.append(f"{file_path}: {result.error}")
            elif isinstance(files, dict):
                # Nested structure
                for sub_dir, sub_files in files.items():
                    sub_dir_path = dir_path / sub_dir
                    sub_dir_path.mkdir(parents=True, exist_ok=True)
                    for file_name in sub_files:
                        file_path = sub_dir_path / file_name
                        result = await self._generate_file(
                            provider, model, file_path, plan, context, sub_dir
                        )
                        if result.success:
                            generated_files.append(
                                str(file_path.relative_to(workspace_path))
                            )
                        else:
                            errors.append(f"{file_path}: {result.error}")

        # Generate root files
        root_files = file_structure.get("root", [])
        for file_name in root_files:
            file_path = workspace_path / file_name
            result = await self._generate_file(
                provider, model, file_path, plan, context, "root"
            )
            if result.success:
                generated_files.append(str(file_path.relative_to(workspace_path)))
            else:
                errors.append(f"{file_path}: {result.error}")

        if errors:
            return AgentResult(
                success=False,
                output={"generated_files": generated_files, "errors": errors},
                error=f"Failed to generate {len(errors)} files",
            )

        return AgentResult(
            success=True,
            output={"generated_files": generated_files},
            metadata={"model_used": model.id, "provider": provider.provider_name},
        )

    async def _generate_file(
        self,
        provider,
        model,
        file_path: Path,
        plan: dict[str, Any],
        context: AgentContext,
        component: str,
    ) -> AgentResult:
        """Generate a single file."""
        try:
            system_prompt = self._get_system_prompt(file_path, plan, component)

            messages = [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(
                    role="user",
                    content=f"Generate the complete content for {file_path.name}",
                ),
            ]

            response = await provider.chat(
                messages=messages,
                model=model.id,
                temperature=0.2,
                max_tokens=4000,
            )

            # Write the file
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(response.content, encoding="utf-8")

            return AgentResult(success=True, output=str(file_path))
        except Exception as e:
            logger.error(f"Failed to generate {file_path}: {e}")
            return AgentResult(success=False, error=str(e))

    def _get_system_prompt(
        self, file_path: Path, plan: dict[str, Any], component: str
    ) -> str:
        """Generate system prompt for file generation."""
        tech_stack = plan.get("tech_stack", {})
        architecture = plan.get("architecture", {})

        return f"""You are an expert software engineer. Generate production-quality code for the file: {file_path.name}

Project Context:
- Tech Stack: {tech_stack}
- Architecture: {architecture.get("pattern", "unknown")}
- Component: {component}

Requirements:
1. Write complete, production-ready code
2. Follow best practices for {tech_stack.get("language", "the language")}
3. Use {tech_stack.get("framework", "the framework")} conventions
4. Include proper error handling, logging, and type hints
5. Follow SOLID principles and clean architecture
6. Add docstrings and comments where necessary
7. Ensure code is secure, scalable, and maintainable
8. DO NOT include placeholder code or TODOs
9. Include all necessary imports

File: {file_path}
Component: {component}

Generate the complete file content now."""
