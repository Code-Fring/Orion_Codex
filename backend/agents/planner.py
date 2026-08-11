"""Planner agent for creating project plans."""

import json
import logging
from typing import Any

from backend.agents.base import AgentContext, AgentResult, BaseAgent
from backend.core.providers.interfaces import ChatMessage
from backend.core.providers.registry import provider_registry

logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent):
    """Agent for creating detailed project plans."""

    def __init__(
        self,
        name: str = "planner_agent",
        description: str = "Creates detailed project plans",
        config: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(name=name, description=description, config=config)

    @property
    def agent_type(self) -> str:
        return "planner"

    async def execute(self, context: AgentContext) -> AgentResult:
        """Create a detailed project plan based on analysis."""
        analysis = context.previous_outputs.get("analysis")
        if not analysis:
            return AgentResult(success=False, error="No analysis available")

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

        system_prompt = """You are an expert software architect and project planner. Create a detailed project plan based on the analysis.
Return a JSON object with the following structure:
{
  "architecture": {
    "pattern": "layered|microservices|monolithic|serverless|event-driven",
    "components": [
      {"name": "component_name", "type": "frontend|backend|database|service|api", "description": "..."}
    ],
    "data_flow": "Description of data flow"
  },
  "tech_stack": {
    "language": "python|javascript|typescript|go|rust|...",
    "framework": "fastapi|react|nextjs|django|...",
    "database": "sqlite|postgresql|mongodb|...",
    "orm": "sqlalchemy|prisma|...",
    "testing": "pytest|jest|...",
    "deployment": "docker|kubernetes|vercel|...",
    "additional": ["tool1", "tool2", ...]
  },
  "file_structure": {
    "root": ["file1", "file2", "dir1/"],
    "src": {"component1": ["file1", "file2"], "component2": ["file1"]}
  },
  "tasks": [
    {
      "name": "task_name",
      "description": "Task description",
      "agent_type": "builder|tester|reviewer|deployer",
      "dependencies": ["task_name"],
      "priority": 1,
      "estimated_duration": "30m"
    }
  ],
  "milestones": [
    {"name": "Setup", "tasks": ["task1", "task2"]},
    {"name": "Core Implementation", "tasks": ["task3", "task4"]}
  ]
}"""

        analysis_json = json.dumps(analysis, indent=2)

        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=f"Analysis:\n{analysis_json}"),
        ]

        try:
            response = await provider.chat(
                messages=messages,
                model=model.id,
                temperature=0.3,
                max_tokens=4000,
            )

            plan = json.loads(response.content)

            return AgentResult(
                success=True,
                output=plan,
                metadata={"model_used": model.id, "provider": provider.provider_name},
            )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse plan response: {e}")
            return AgentResult(success=False, error=f"Failed to parse plan: {e}")
        except Exception as e:
            logger.error(f"Planner agent failed: {e}")
            return AgentResult(success=False, error=str(e))
