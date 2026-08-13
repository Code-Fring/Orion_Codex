"""Task router for directing tasks to appropriate agents."""

import logging
from enum import Enum
from typing import Any

from backend.agents.analysis import AnalysisAgent
from backend.agents.architect import ArchitectAgent, ArchitectureReviewerAgent
from backend.agents.base import AgentContext, AgentPipeline, AgentResult, BaseAgent
from backend.agents.builder import BuilderAgent
from backend.agents.coder import CoderAgent, CodeRefactoringAgent
from backend.agents.debugger import DebuggerAgent, ErrorRecoveryAgent
from backend.agents.dependency import DependencyManagerAgent
from backend.agents.deployer import DeployerAgent
from backend.agents.git import GitAgent
from backend.agents.planner import PlannerAgent
from backend.agents.reviewer import ReviewerAgent
from backend.agents.security import SecurityAgent, SecurityHardeningAgent
from backend.agents.tester import TesterAgent
from backend.tasks.queue import broadcast_progress, log_message

logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    """Pipeline stages."""

    ANALYSIS = "analysis"
    PLANNING = "planner"
    ARCHITECTURE = "architect"
    ARCHITECTURE_REVIEW = "architecture_reviewer"
    CODING = "coder"
    REFACTORING = "refactoring"
    BUILDING = "builder"
    TESTING = "tester"
    REVIEW = "reviewer"
    SECURITY = "security"
    SECURITY_HARDENING = "security_hardening"
    DEPENDENCY = "dependency"
    DEBUGGING = "debugging"
    ERROR_RECOVERY = "error_recovery"
    GIT = "git"
    DEPLOYMENT = "deployer"


class TaskRouter:
    """Routes tasks to appropriate agents and manages pipelines."""

    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}
        self._pipelines: dict[str, AgentPipeline] = {}
        self._initialize_default_agents()

    def _initialize_default_agents(self) -> None:
        """Initialize default agents."""
        self._agents = {
            "analysis": AnalysisAgent(
                "Analysis Agent", "Analyzes user prompts and extracts requirements"
            ),
            "planner": PlannerAgent("Planner Agent", "Creates detailed project plans"),
            "architect": ArchitectAgent(
                "Architect Agent", "Designs system architecture"
            ),
            "architecture_reviewer": ArchitectureReviewerAgent(
                "Architecture Reviewer", "Reviews architecture decisions"
            ),
            "coder": CoderAgent("Coder Agent", "Implements production-quality code"),
            "refactoring": CodeRefactoringAgent(
                "Refactoring Agent", "Refactors and improves code"
            ),
            "builder": BuilderAgent("Builder Agent", "Generates code files"),
            "tester": TesterAgent("Tester Agent", "Generates and runs tests"),
            "reviewer": ReviewerAgent("Reviewer Agent", "Reviews code quality"),
            "debugger": DebuggerAgent("Debugger Agent", "Finds and fixes bugs"),
            "error_recovery": ErrorRecoveryAgent(
                "Error Recovery Agent", "Recovers from pipeline failures"
            ),
            "security": SecurityAgent(
                "Security Agent", "Analyzes security vulnerabilities"
            ),
            "security_hardening": SecurityHardeningAgent(
                "Security Hardening Agent", "Applies security fixes"
            ),
            "dependency": DependencyManagerAgent(
                "Dependency Manager", "Manages project dependencies"
            ),
            "git": GitAgent("Git Agent", "Manages version control"),
            "deployer": DeployerAgent(
                "Deployer Agent", "Packages and deploys projects"
            ),
        }

    def register_agent(self, agent: BaseAgent) -> None:
        """Register a custom agent."""
        self._agents[agent.agent_type] = agent
        logger.info(f"Registered agent: {agent.agent_type}")

    def get_agent(self, agent_type: str) -> BaseAgent | None:
        """Get an agent by type."""
        return self._agents.get(agent_type)

    def create_pipeline(self, name: str, stages: list[PipelineStage]) -> AgentPipeline:
        """Create a pipeline with specified stages."""
        agents = []
        for stage in stages:
            agent = self._agents.get(stage.value)
            if agent:
                agents.append(agent)
            else:
                logger.warning(f"No agent found for stage: {stage.value}")

        pipeline = AgentPipeline(name, agents)
        self._pipelines[name] = pipeline
        return pipeline

    def get_pipeline(self, name: str) -> AgentPipeline | None:
        """Get a pipeline by name."""
        return self._pipelines.get(name)

    async def execute_pipeline(
        self,
        pipeline_name: str,
        context: AgentContext,
    ) -> dict[str, AgentResult]:
        """Execute a pipeline by name."""
        pipeline = self.get_pipeline(pipeline_name)
        if not pipeline:
            raise ValueError(f"Pipeline not found: {pipeline_name}")

        logger.info(f"Executing pipeline: {pipeline_name}")

        # Broadcast initial progress
        await broadcast_progress(context.project_id, 0, "starting")

        results = {}
        total_stages = len(pipeline.agents)

        for i, agent in enumerate(pipeline.agents):
            stage_name = agent.agent_type
            logger.info(f"Executing stage: {stage_name}")

            # Broadcast stage start
            await broadcast_progress(
                context.project_id, int((i / total_stages) * 100), stage_name
            )

            # Log stage start
            await log_message(
                context.project_id,
                "info",
                f"Starting stage: {stage_name}",
                {"stage": stage_name, "step": i + 1, "total": total_stages},
            )

            if not await agent.validate_context(context):
                error_msg = f"Context validation failed for stage: {stage_name}"
                results[stage_name] = AgentResult(success=False, error=error_msg)

                await log_message(
                    context.project_id, "error", error_msg, {"stage": stage_name}
                )
                break

            await agent.pre_execute(context)
            result = await agent.execute(context)
            await agent.post_execute(result)

            results[stage_name] = result

            # Broadcast stage completion
            progress = int(((i + 1) / total_stages) * 100)
            await broadcast_progress(context.project_id, progress, stage_name)

            if result.success:
                await log_message(
                    context.project_id,
                    "info",
                    f"Completed stage: {stage_name}",
                    {
                        "stage": stage_name,
                        "output_keys": list(result.output_data.keys())
                        if result.output_data
                        else [],
                    },
                )
            else:
                await log_message(
                    context.project_id,
                    "error",
                    f"Stage failed: {stage_name} - {result.error}",
                    {"stage": stage_name, "error": result.error},
                )
                break

        # Final progress
        await broadcast_progress(context.project_id, 100, "completed")

        return results

    async def execute_stage(
        self,
        stage: PipelineStage,
        context: AgentContext,
    ) -> AgentResult:
        """Execute a single pipeline stage."""
        agent = self._agents.get(stage.value)
        if not agent:
            return AgentResult(
                success=False,
                error=f"No agent found for stage: {stage.value}",
            )

        if not await agent.validate_context(context):
            return AgentResult(
                success=False,
                error=f"Context validation failed for stage: {stage.value}",
            )

        await agent.pre_execute(context)
        result = await agent.execute(context)
        await agent.post_execute(result)

        return result

    def get_default_pipeline(self) -> AgentPipeline:
        """Get the default full generation pipeline."""
        return self.create_pipeline(
            "full_generation",
            [
                PipelineStage.ANALYSIS,
                PipelineStage.PLANNING,
                PipelineStage.ARCHITECTURE,
                PipelineStage.ARCHITECTURE_REVIEW,
                PipelineStage.CODING,
                PipelineStage.BUILDING,
                PipelineStage.TESTING,
                PipelineStage.REVIEW,
                PipelineStage.SECURITY,
            ],
        )

    def get_quick_pipeline(self) -> AgentPipeline:
        """Get a quick pipeline (analysis, planning, coding only)."""
        return self.create_pipeline(
            "quick_generation",
            [
                PipelineStage.ANALYSIS,
                PipelineStage.PLANNING,
                PipelineStage.CODING,
            ],
        )

    def get_secure_pipeline(self) -> AgentPipeline:
        """Get a security-focused pipeline."""
        return self.create_pipeline(
            "secure_generation",
            [
                PipelineStage.ANALYSIS,
                PipelineStage.PLANNING,
                PipelineStage.ARCHITECTURE,
                PipelineStage.CODING,
                PipelineStage.BUILDING,
                PipelineStage.TESTING,
                PipelineStage.REVIEW,
                PipelineStage.SECURITY,
                PipelineStage.SECURITY_HARDENING,
                PipelineStage.DEPENDENCY,
            ],
        )

    def get_refactor_pipeline(self) -> AgentPipeline:
        """Get a refactoring pipeline."""
        return self.create_pipeline(
            "refactor_pipeline",
            [
                PipelineStage.ANALYSIS,
                PipelineStage.REFACTORING,
                PipelineStage.TESTING,
                PipelineStage.REVIEW,
                PipelineStage.GIT,
            ],
        )

    def list_agents(self) -> list[dict[str, Any]]:
        """List all registered agents."""
        return [
            {
                "type": agent.agent_type,
                "name": agent.name,
                "description": agent.description,
                "status": agent.status.value,
            }
            for agent in self._agents.values()
        ]

    def list_pipelines(self) -> list[dict[str, Any]]:
        """List all pipelines."""
        return [
            {
                "name": name,
                "stages": [agent.agent_type for agent in pipeline.agents],
            }
            for name, pipeline in self._pipelines.items()
        ]


# Global router instance
task_router = TaskRouter()
