"""Model Manager for role-based model assignment."""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from backend.core.providers.interfaces import ModelCapability
from backend.core.providers.registry import provider_registry

logger = logging.getLogger(__name__)


class AgentRole(Enum):
    """Agent roles that can have dedicated models."""

    PLANNING = "planning"
    ARCHITECT = "architect"
    CODING = "coding"
    REASONING = "reasoning"
    REFACTORING = "refactoring"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    VISION = "vision"
    LONG_CONTEXT = "long_context"
    REVIEW = "review"
    TOOL_CALLING = "tool_calling"
    DEBUGGING = "debugging"
    SECURITY = "security"
    DEPENDENCY = "dependency"
    GIT = "git"
    DEFAULT = "default"


@dataclass
class ModelAssignment:
    """Model assignment for a specific role."""

    role: AgentRole
    provider_name: str
    model_id: str
    temperature: float = 0.3
    max_tokens: int | None = None
    capabilities: list[ModelCapability] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelRoleConfig:
    """Configuration for model-role assignments."""

    assignments: dict[str, ModelAssignment] = field(default_factory=dict)
    fallback_provider: str | None = None
    fallback_model: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "assignments": {
                role: {
                    "role": assignment.role.value,
                    "provider_name": assignment.provider_name,
                    "model_id": assignment.model_id,
                    "temperature": assignment.temperature,
                    "max_tokens": assignment.max_tokens,
                    "capabilities": [c.value for c in assignment.capabilities],
                    "metadata": assignment.metadata,
                }
                for role, assignment in self.assignments.items()
            },
            "fallback_provider": self.fallback_provider,
            "fallback_model": self.fallback_model,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelRoleConfig":
        config = cls()
        config.fallback_provider = data.get("fallback_provider")
        config.fallback_model = data.get("fallback_model")

        for role_str, assignment_data in data.get("assignments", {}).items():
            role = AgentRole(role_str)
            capabilities = [
                ModelCapability(c) for c in assignment_data.get("capabilities", [])
            ]
            assignment = ModelAssignment(
                role=role,
                provider_name=assignment_data["provider_name"],
                model_id=assignment_data["model_id"],
                temperature=assignment_data.get("temperature", 0.3),
                max_tokens=assignment_data.get("max_tokens"),
                capabilities=capabilities,
                metadata=assignment_data.get("metadata", {}),
            )
            config.assignments[role_str] = assignment

        return config


class ModelManager:
    """Manages model assignments for different agent roles."""

    DEFAULT_ROLE_CAPABILITIES = {
        AgentRole.PLANNING: [ModelCapability.CHAT, ModelCapability.REASONING],
        AgentRole.ARCHITECT: [
            ModelCapability.CHAT,
            ModelCapability.REASONING,
            ModelCapability.CODE,
        ],
        AgentRole.CODING: [
            ModelCapability.CODE,
            ModelCapability.CHAT,
            ModelCapability.FUNCTION_CALLING,
        ],
        AgentRole.REASONING: [ModelCapability.CHAT, ModelCapability.REASONING],
        AgentRole.REFACTORING: [
            ModelCapability.CODE,
            ModelCapability.CHAT,
            ModelCapability.REASONING,
        ],
        AgentRole.TESTING: [ModelCapability.CODE, ModelCapability.CHAT],
        AgentRole.DOCUMENTATION: [ModelCapability.CHAT],
        AgentRole.VISION: [ModelCapability.VISION, ModelCapability.CHAT],
        AgentRole.LONG_CONTEXT: [ModelCapability.CHAT],
        AgentRole.REVIEW: [
            ModelCapability.CODE,
            ModelCapability.CHAT,
            ModelCapability.REASONING,
            ModelCapability.SECURITY,
        ],
        AgentRole.TOOL_CALLING: [
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.CHAT,
        ],
        AgentRole.DEBUGGING: [
            ModelCapability.CODE,
            ModelCapability.CHAT,
            ModelCapability.REASONING,
        ],
        AgentRole.SECURITY: [
            ModelCapability.CODE,
            ModelCapability.CHAT,
            ModelCapability.SECURITY,
        ],
        AgentRole.DEPENDENCY: [ModelCapability.CODE, ModelCapability.CHAT],
        AgentRole.GIT: [ModelCapability.CHAT],
        AgentRole.DEFAULT: [ModelCapability.CHAT],
    }

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or Path.home() / ".orion" / "model_roles.json"
        self.config = ModelRoleConfig()
        self._load_config()

    def _load_config(self) -> None:
        """Load model role configuration from file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    data = json.load(f)
                self.config = ModelRoleConfig.from_dict(data)
                logger.info(f"Loaded model role config from {self.config_path}")
            except Exception as e:
                logger.warning(f"Failed to load model role config: {e}")
                self._create_default_config()
        else:
            self._create_default_config()

    def _create_default_config(self) -> None:
        """Create default configuration with sensible defaults."""
        self.config = ModelRoleConfig()
        self.save_config()

    def save_config(self) -> None:
        """Save model role configuration to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.config.to_dict(), f, indent=2)
            logger.info(f"Saved model role config to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save model role config: {e}")

    def assign_model(
        self,
        role: AgentRole,
        provider_name: str,
        model_id: str,
        temperature: float = 0.3,
        max_tokens: int | None = None,
    ) -> bool:
        """Assign a model to a role."""
        # Verify provider exists
        provider = provider_registry.get_provider(provider_name)
        if not provider:
            logger.error(f"Provider not found: {provider_name}")
            return False

        # Verify model exists for provider
        models = provider_registry.get_cached_models(provider_name)
        if not models:
            # Try to fetch models
            import asyncio

            models = asyncio.run(provider.list_models())

        model_exists = any(m.id == model_id for m in models)
        if not model_exists:
            logger.warning(
                f"Model {model_id} not found for provider {provider_name}, but assigning anyway"
            )

        # Get recommended capabilities for this role
        capabilities = self.DEFAULT_ROLE_CAPABILITIES.get(role, [ModelCapability.CHAT])

        assignment = ModelAssignment(
            role=role,
            provider_name=provider_name,
            model_id=model_id,
            temperature=temperature,
            max_tokens=max_tokens,
            capabilities=capabilities,
        )

        self.config.assignments[role.value] = assignment
        self.save_config()
        logger.info(f"Assigned {provider_name}/{model_id} to role {role.value}")
        return True

    def get_assignment(self, role: AgentRole) -> ModelAssignment | None:
        """Get model assignment for a role."""
        return self.config.assignments.get(role.value)

    def get_model_for_role(self, role: AgentRole) -> tuple | None:
        """Get (provider, model_id) for a role, with fallback."""
        assignment = self.get_assignment(role)
        if assignment:
            provider = provider_registry.get_provider(assignment.provider_name)
            if provider:
                return (provider, assignment.model_id)

        # Fallback to default role
        default_assignment = self.get_assignment(AgentRole.DEFAULT)
        if default_assignment:
            provider = provider_registry.get_provider(default_assignment.provider_name)
            if provider:
                return (provider, default_assignment.model_id)

        # Fallback to config fallback
        if self.config.fallback_provider:
            provider = provider_registry.get_provider(self.config.fallback_provider)
            if provider:
                return (provider, self.config.fallback_model or "default")

        # Last resort: first available chat provider
        chat_providers = provider_registry.get_chat_providers()
        if chat_providers:
            return (chat_providers[0], "default")

        return None

    def get_temperature_for_role(self, role: AgentRole) -> float:
        """Get temperature for a role."""
        assignment = self.get_assignment(role)
        if assignment:
            return assignment.temperature
        return 0.3

    def get_max_tokens_for_role(self, role: AgentRole) -> int | None:
        """Get max tokens for a role."""
        assignment = self.get_assignment(role)
        if assignment:
            return assignment.max_tokens
        return None

    def remove_assignment(self, role: AgentRole) -> bool:
        """Remove model assignment for a role."""
        if role.value in self.config.assignments:
            del self.config.assignments[role.value]
            self.save_config()
            return True
        return False

    def list_assignments(self) -> dict[str, ModelAssignment]:
        """List all model assignments."""
        return dict(self.config.assignments)

    def auto_assign_best_models(self) -> dict[AgentRole, bool]:
        """Automatically assign best available models to each role."""
        results = {}
        chat_providers = provider_registry.get_chat_providers()
        code_providers = provider_registry.get_code_providers()

        all_providers = list(
            {p.provider_name: p for p in chat_providers + code_providers}.values()
        )

        if not all_providers:
            logger.warning("No providers available for auto-assignment")
            return {role: False for role in AgentRole}

        for role in AgentRole:
            if role == AgentRole.DEFAULT:
                continue

            # Find best provider for this role
            capabilities = self.DEFAULT_ROLE_CAPABILITIES.get(
                role, [ModelCapability.CHAT]
            )
            best_provider = None
            best_model = None

            for provider in all_providers:
                models = provider_registry.get_cached_models(provider.provider_name)
                if not models:
                    continue

                # Score models based on capabilities
                for model in models:
                    score = 0
                    for cap in capabilities:
                        if cap in model.capabilities:
                            score += 10

                    # Prefer larger context windows for certain roles
                    if role in (
                        AgentRole.LONG_CONTEXT,
                        AgentRole.ARCHITECT,
                        AgentRole.PLANNING,
                    ):
                        score += min(model.context_window / 10000, 20)

                    # Prefer code-capable models for coding roles
                    if role in (
                        AgentRole.CODING,
                        AgentRole.REFACTORING,
                        AgentRole.TESTING,
                        AgentRole.REVIEW,
                    ):
                        if ModelCapability.CODE in model.capabilities:
                            score += 15

                    # Prefer function calling for tool calling
                    if role == AgentRole.TOOL_CALLING:
                        if ModelCapability.FUNCTION_CALLING in model.capabilities:
                            score += 20

                    if score > 0 and (best_model is None or score > best_score):
                        best_provider = provider
                        best_model = model.id
                        best_score = score

            if best_provider and best_model:
                results[role] = self.assign_model(
                    role, best_provider.provider_name, best_model
                )
            else:
                results[role] = False

        # Set default to first available
        if all_providers:
            first_provider = all_providers[0]
            first_models = provider_registry.get_cached_models(
                first_provider.provider_name
            )
            if first_models:
                self.assign_model(
                    AgentRole.DEFAULT, first_provider.provider_name, first_models[0].id
                )
                results[AgentRole.DEFAULT] = True

        return results

    def get_provider_for_role(self, role: AgentRole):
        """Get provider instance for a role."""
        assignment = self.get_assignment(role)
        if assignment:
            return provider_registry.get_provider(assignment.provider_name)
        return None


# Global model manager instance
model_manager = ModelManager()
