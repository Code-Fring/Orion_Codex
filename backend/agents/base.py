"""Base agent classes for Orion Codex."""

import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent execution status."""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentContext:
    """Context passed to agents during execution."""

    project_id: str
    workspace_path: str
    config: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    previous_outputs: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Result of agent execution."""

    success: bool
    output: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    artifacts: list[str] = field(default_factory=list)


class BaseAgent(ABC):
    """Base class for all agents."""

    def __init__(
        self,
        name: str,
        description: str = "",
        config: dict[str, Any] | None = None,
    ) -> None:
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.config = config or {}
        self.status = AgentStatus.IDLE
        self._context: AgentContext | None = None

    @property
    @abstractmethod
    def agent_type(self) -> str:
        """Return the agent type identifier."""

    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute the agent with the given context."""

    async def validate_context(self, context: AgentContext) -> bool:
        """Validate the context before execution."""
        return True

    def set_context(self, context: AgentContext) -> None:
        """Set the execution context."""
        self._context = context

    def get_context(self) -> AgentContext | None:
        """Get the current context."""
        return self._context

    async def pre_execute(self, context: AgentContext) -> None:
        """Pre-execution hook."""
        self.status = AgentStatus.RUNNING
        logger.info(f"Agent {self.name} ({self.agent_type}) started")

    async def post_execute(self, result: AgentResult) -> None:
        """Post-execution hook."""
        if result.success:
            self.status = AgentStatus.COMPLETED
            logger.info(f"Agent {self.name} ({self.agent_type}) completed successfully")
        else:
            self.status = AgentStatus.FAILED
            logger.error(
                f"Agent {self.name} ({self.agent_type}) failed: {result.error}"
            )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name}, type={self.agent_type}, status={self.status})>"


class AgentPipeline:
    """Pipeline for executing multiple agents in sequence."""

    def __init__(self, name: str, agents: list[BaseAgent]) -> None:
        self.name = name
        self.agents = agents
        self.results: dict[str, AgentResult] = {}

    async def execute(self, context: AgentContext) -> dict[str, AgentResult]:
        """Execute all agents in sequence."""
        logger.info(f"Starting pipeline: {self.name}")

        for agent in self.agents:
            if not await agent.validate_context(context):
                result = AgentResult(
                    success=False,
                    error=f"Context validation failed for agent {agent.name}",
                )
                self.results[agent.name] = result
                break

            await agent.pre_execute(context)
            result = await agent.execute(context)
            await agent.post_execute(result)

            self.results[agent.name] = result
            context.previous_outputs[agent.name] = result.output

            if not result.success:
                logger.error(
                    f"Pipeline {self.name} stopped at agent {agent.name}: {result.error}"
                )
                break

        return self.results

    def get_result(self, agent_name: str) -> AgentResult | None:
        """Get result for a specific agent."""
        return self.results.get(agent_name)

    def all_successful(self) -> bool:
        """Check if all agents completed successfully."""
        return all(r.success for r in self.results.values())
