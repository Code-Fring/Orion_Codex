"""Analysis agent for understanding user prompts."""

import json
import logging
from typing import Any

from backend.agents.base import AgentContext, AgentResult, BaseAgent
from backend.core.providers.interfaces import ChatMessage
from backend.core.providers.registry import provider_registry

logger = logging.getLogger(__name__)


class AnalysisAgent(BaseAgent):
    """Agent for analyzing user prompts and extracting requirements."""

    def __init__(
        self,
        name: str = "analysis_agent",
        description: str = "Analyzes user prompts and extracts requirements",
        config: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(name=name, description=description, config=config)

    @property
    def agent_type(self) -> str:
        return "analysis"

    async def execute(self, context: AgentContext) -> AgentResult:
        """Analyze the user prompt and extract structured requirements."""
        prompt = context.config.get("prompt", "")
        if not prompt:
            return AgentResult(success=False, error="No prompt provided")

        # Get a chat provider
        chat_providers = provider_registry.get_chat_providers()
        if not chat_providers:
            return AgentResult(success=False, error="No chat providers available")

        provider = chat_providers[0]
        models = provider_registry.get_cached_models(provider.provider_name)
        if not models:
            models = await provider.list_models()

        # Select a model good at analysis
        model = next(
            (
                m
                for m in models
                if "gpt-4" in m.id or "claude-3" in m.id or "nemotron" in m.id
            ),
            models[0],
        )

        system_prompt = """You are an expert software architect. Analyze the user's prompt and extract structured requirements.
Return a JSON object with the following structure:
{
  "project_type": "web_app|mobile_app|desktop_app|api|cli|library|game|ml_pipeline|automation|saas|other",
  "description": "Clear description of what to build",
  "features": ["feature1", "feature2", ...],
  "tech_stack_preferences": {
    "language": "preferred language or null",
    "framework": "preferred framework or null",
    "database": "preferred database or null",
    "deployment": "preferred deployment or null"
  },
  "constraints": ["constraint1", "constraint2", ...],
  "complexity": "simple|moderate|complex",
  "estimated_files": 0,
  "key_requirements": ["req1", "req2", ...]
}"""

        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=prompt),
        ]

        try:
            response = await provider.chat(
                messages=messages,
                model=model.id,
                temperature=0.3,
                max_tokens=2000,
            )

            # Parse the JSON response
            analysis = json.loads(response.content)

            return AgentResult(
                success=True,
                output=analysis,
                metadata={"model_used": model.id, "provider": provider.provider_name},
            )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse analysis response: {e}")
            return AgentResult(success=False, error=f"Failed to parse analysis: {e}")
        except Exception as e:
            logger.error(f"Analysis agent failed: {e}")
            return AgentResult(success=False, error=str(e))
