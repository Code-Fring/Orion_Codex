"""Memory management for agent context and history."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class MemoryStore:
    """Persistent memory store for agents."""

    def __init__(self, storage_path: Path | None = None) -> None:
        self.storage_path = storage_path or Path("./memory")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, Any] = {}

    def _get_project_path(self, project_id: str) -> Path:
        """Get storage path for a project."""
        return self.storage_path / project_id

    def save_context(self, project_id: str, context: dict[str, Any]) -> bool:
        """Save agent context for a project."""
        try:
            project_path = self._get_project_path(project_id)
            project_path.mkdir(parents=True, exist_ok=True)

            context_file = project_path / "context.json"
            context["updated_at"] = datetime.utcnow().isoformat()

            context_file.write_text(json.dumps(context, indent=2))
            self._cache[project_id] = context
            return True
        except Exception as e:
            logger.error(f"Failed to save context for {project_id}: {e}")
            return False

    def load_context(self, project_id: str) -> dict[str, Any] | None:
        """Load agent context for a project."""
        if project_id in self._cache:
            return self._cache[project_id]

        try:
            project_path = self._get_project_path(project_id)
            context_file = project_path / "context.json"

            if not context_file.exists():
                return None

            context = json.loads(context_file.read_text())
            self._cache[project_id] = context
            return context
        except Exception as e:
            logger.error(f"Failed to load context for {project_id}: {e}")
            return None

    def save_agent_output(self, project_id: str, agent_type: str, output: Any) -> bool:
        """Save agent output."""
        try:
            project_path = self._get_project_path(project_id)
            project_path.mkdir(parents=True, exist_ok=True)

            outputs_file = project_path / "agent_outputs.json"

            outputs = {}
            if outputs_file.exists():
                outputs = json.loads(outputs_file.read_text())

            outputs[agent_type] = {
                "output": output,
                "timestamp": datetime.utcnow().isoformat(),
            }

            outputs_file.write_text(json.dumps(outputs, indent=2))
            return True
        except Exception as e:
            logger.error(
                f"Failed to save agent output for {project_id}/{agent_type}: {e}"
            )
            return False

    def load_agent_output(self, project_id: str, agent_type: str) -> Any | None:
        """Load agent output."""
        try:
            project_path = self._get_project_path(project_id)
            outputs_file = project_path / "agent_outputs.json"

            if not outputs_file.exists():
                return None

            outputs = json.loads(outputs_file.read_text())
            return outputs.get(agent_type, {}).get("output")
        except Exception as e:
            logger.error(
                f"Failed to load agent output for {project_id}/{agent_type}: {e}"
            )
            return None

    def save_conversation(
        self, project_id: str, messages: list[dict[str, Any]]
    ) -> bool:
        """Save conversation history."""
        try:
            project_path = self._get_project_path(project_id)
            project_path.mkdir(parents=True, exist_ok=True)

            conv_file = project_path / "conversation.json"
            conv_file.write_text(
                json.dumps(
                    {
                        "messages": messages,
                        "updated_at": datetime.utcnow().isoformat(),
                    },
                    indent=2,
                )
            )
            return True
        except Exception as e:
            logger.error(f"Failed to save conversation for {project_id}: {e}")
            return False

    def load_conversation(self, project_id: str) -> list[dict[str, Any]]:
        """Load conversation history."""
        try:
            project_path = self._get_project_path(project_id)
            conv_file = project_path / "conversation.json"

            if not conv_file.exists():
                return []

            data = json.loads(conv_file.read_text())
            return data.get("messages", [])
        except Exception as e:
            logger.error(f"Failed to load conversation for {project_id}: {e}")
            return []

    def add_to_conversation(self, project_id: str, message: dict[str, Any]) -> bool:
        """Add a message to conversation history."""
        messages = self.load_conversation(project_id)
        messages.append(
            {
                **message,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        return self.save_conversation(project_id, messages)

    def clear_project_memory(self, project_id: str) -> bool:
        """Clear all memory for a project."""
        try:
            project_path = self._get_project_path(project_id)
            if project_path.exists():
                import shutil

                shutil.rmtree(project_path)
            if project_id in self._cache:
                del self._cache[project_id]
            return True
        except Exception as e:
            logger.error(f"Failed to clear memory for {project_id}: {e}")
            return False


class VectorMemory:
    """Vector-based semantic memory for long-term storage."""

    def __init__(self, storage_path: Path | None = None) -> None:
        self.storage_path = storage_path or Path("./vector_memory")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._embeddings_cache: dict[str, list[float]] = {}

    def add_memory(
        self,
        project_id: str,
        content: str,
        metadata: dict[str, Any],
        embedding: list[float],
    ) -> bool:
        """Add a memory with its embedding."""
        try:
            project_path = self.storage_path / project_id
            project_path.mkdir(parents=True, exist_ok=True)

            memory_file = project_path / "memories.jsonl"

            memory_entry = {
                "content": content,
                "metadata": metadata,
                "embedding": embedding,
                "timestamp": datetime.utcnow().isoformat(),
            }

            with open(memory_file, "a") as f:
                f.write(json.dumps(memory_entry) + "\n")

            return True
        except Exception as e:
            logger.error(f"Failed to add memory: {e}")
            return False

    def search_memories(
        self,
        project_id: str,
        query_embedding: list[float],
        top_k: int = 5,
        threshold: float = 0.7,
    ) -> list[dict[str, Any]]:
        """Search memories by semantic similarity."""
        try:
            project_path = self.storage_path / project_id
            memory_file = project_path / "memories.jsonl"

            if not memory_file.exists():
                return []

            memories = []
            with open(memory_file, "r") as f:
                for line in f:
                    if line.strip():
                        memories.append(json.loads(line))

            # Calculate cosine similarity
            import numpy as np

            query_vec = np.array(query_embedding)
            results = []

            for mem in memories:
                mem_vec = np.array(mem["embedding"])
                similarity = np.dot(query_vec, mem_vec) / (
                    np.linalg.norm(query_vec) * np.linalg.norm(mem_vec)
                )
                if similarity >= threshold:
                    results.append(
                        {
                            **mem,
                            "similarity": float(similarity),
                        }
                    )

            # Sort by similarity and return top_k
            results.sort(key=lambda x: x["similarity"], reverse=True)
            return results[:top_k]
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []


# Global memory instances
memory_store = MemoryStore()
vector_memory = VectorMemory()
