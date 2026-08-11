"""Model API for plugins."""


from backend.core.model_manager import AgentRole, ModelAssignment, model_manager


class ModelAPI:
    """API for model operations."""

    def __init__(self) -> None:
        pass

    def get_assignment(self, role: AgentRole) -> ModelAssignment | None:
        """Get model assignment for a role."""
        return model_manager.get_assignment(role)

    def assign_model(
        self,
        role: AgentRole,
        provider_name: str,
        model_id: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> bool:
        """Assign a model to a role."""
        return model_manager.assign_model(role, provider_name, model_id, temperature, max_tokens)

    def auto_assign_best_models(self) -> dict[str, bool]:
        """Auto-assign best models for all roles."""
        return model_manager.auto_assign_best_models()

    def get_model_for_role(self, role: AgentRole) -> tuple[str, str] | None:
        """Get provider and model for a role."""
        return model_manager.get_model_for_role(role)

    def get_temperature_for_role(self, role: AgentRole) -> float:
        """Get temperature for a role."""
        return model_manager.get_temperature_for_role(role)

    def get_max_tokens_for_role(self, role: AgentRole) -> int | None:
        """Get max tokens for a role."""
        return model_manager.get_max_tokens_for_role(role)

    def list_roles(self) -> list[AgentRole]:
        """List all agent roles."""
        return list(AgentRole)

    def get_all_assignments(self) -> dict[AgentRole, ModelAssignment]:
        """Get all model assignments."""
        return model_manager.get_all_assignments()
