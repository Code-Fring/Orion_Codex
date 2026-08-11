"""Agent API for plugins."""

from typing import Any

from backend.agents.base import BaseAgent, AgentContext, AgentResult, AgentPipeline, AgentStatus
from backend.agents import (
    planner,
    architect,
    coder,
    reviewer,
    tester,
    security,
    debugger,
    deployer,
    git as git_agent,
    dependency,
    builder,
    analysis,
)


class AgentAPI:
    """API for agent operations."""

    def __init__(self, project_id: str, workspace_path: str) -> None:
        self.project_id = project_id
        self.workspace_path = workspace_path

    def create_context(self, config: dict[str, Any] | None = None) -> AgentContext:
        """Create an agent context."""
        return AgentContext(
            project_id=self.project_id,
            workspace_path=self.workspace_path,
            config=config or {},
        )

    def get_available_agents(self) -> dict[str, type]:
        """Get all available agent types."""
        return {
            "planner": planner.ProjectPlanner,
            "architect": architect.SystemArchitect,
            "coder": coder.CoderAgent,
            "reviewer": reviewer.CodeReviewer,
            "tester": tester.TestAgent,
            "security": security.SecurityAgent,
            "debugger": debugger.DebugAgent,
            "deployer": deployer.DeployAgent,
            "git": git_agent.GitAgent,
            "dependency": dependency.DependencyAgent,
            "builder": builder.BuilderAgent,
            "analysis": analysis.AnalysisAgent,
        }

    async def run_agent(
        self,
        agent_type: str,
        context: AgentContext,
        config: dict[str, Any] | None = None,
    ) -> AgentResult:
        """Run a specific agent."""
        agents = self.get_available_agents()
        agent_class = agents.get(agent_type)
        if not agent_class:
            return AgentResult(success=False, error=f"Unknown agent type: {agent_type}")

        agent = agent_class(config=config)
        return await agent.execute(context)

    async def run_pipeline(
        self,
        agent_types: list[str],
        context: AgentContext,
        configs: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, AgentResult]:
        """Run a pipeline of agents."""
        agents = self.get_available_agents()
        pipeline_agents = []

        for agent_type in agent_types:
            agent_class = agents.get(agent_type)
            if not agent_class:
                return {agent_type: AgentResult(success=False, error=f"Unknown agent: {agent_type}")}

            config = configs.get(agent_type) if configs else None
            pipeline_agents.append(agent_class(config=config))

        pipeline = AgentPipeline(f"pipeline_{self.project_id}", pipeline_agents)
        return await pipeline.execute(context)

    def create_custom_agent(
        self,
        name: str,
        agent_type: str,
        execute_fn,
        validate_fn=None,
    ) -> BaseAgent:
        """Create a custom agent."""
        from backend.agents.base import BaseAgent

        class CustomAgent(BaseAgent):
            @property
            def agent_type(self) -> str:
                return agent_type

            async def execute(self, context: AgentContext) -> AgentResult:
                return await execute_fn(context)

            async def validate_context(self, context: AgentContext) -> bool:
                if validate_fn:
                    return await validate_fn(context)
                return True

        return CustomAgent(name=name)