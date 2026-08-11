"""Memory API for plugins."""

from typing import Any

from backend.memory.store import memory_store, vector_memory


class MemoryAPI:
    """API for memory operations."""

    def __init__(self, project_id: str) -> None:
        self.project_id = project_id

    def save_context(self, context: dict[str, Any]) -> bool:
        """Save agent context."""
        return memory_store.save_context(self.project_id, context)

    def load_context(self) -> dict[str, Any] | None:
        """Load agent context."""
        return memory_store.load_context(self.project_id)

    def save_agent_output(self, agent_type: str, output: Any) -> bool:
        """Save agent output."""
        return memory_store.save_agent_output(self.project_id, agent_type, output)

    def load_agent_output(self, agent_type: str) -> Any | None:
        """Load agent output."""
        return memory_store.load_agent_output(self.project_id, agent_type)

    def save_conversation(self, messages: list[dict[str, Any]]) -> bool:
        """Save conversation history."""
        return memory_store.save_conversation(self.project_id, messages)

    def load_conversation(self) -> list[dict[str, Any]]:
        """Load conversation history."""
        return memory_store.load_conversation(self.project_id)

    def add_to_conversation(self, message: dict[str, Any]) -> bool:
        """Add a message to conversation."""
        return memory_store.add_to_conversation(self.project_id, message)

    def clear_memory(self) -> bool:
        """Clear all memory for project."""
        return memory_store.clear_project_memory(self.project_id)

    # Vector memory
    def add_vector_memory(
        self,
        content: str,
        metadata: dict[str, Any],
        embedding: list[float],
    ) -> bool:
        """Add a memory with embedding."""
        return vector_memory.add_memory(self.project_id, content, metadata, embedding)

    def search_vector_memory(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        threshold: float = 0.7,
    ) -> list[dict[str, Any]]:
        """Search memories by semantic similarity."""
        return vector_memory.search_memories(self.project_id, query_embedding, top_k, threshold)