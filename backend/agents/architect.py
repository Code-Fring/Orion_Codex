"""Architect agent for system design and architecture decisions."""

import json
import logging
from typing import Any

from backend.agents.base import AgentContext, AgentResult, BaseAgent
from backend.core.model_manager import AgentRole, model_manager
from backend.core.providers.interfaces import ChatMessage

logger = logging.getLogger(__name__)


class ArchitectAgent(BaseAgent):
    """Agent for system architecture design and technical decisions."""

    def __init__(
        self,
        name: str = "architect_agent",
        description: str = "Designs system architecture",
        config: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(name=name, description=description, config=config)

    @property
    def agent_type(self) -> str:
        return "architect"

    async def execute(self, context: AgentContext) -> AgentResult:
        """Design system architecture based on requirements and constraints."""
        analysis = context.previous_outputs.get("analysis")
        plan = context.previous_outputs.get("planner")

        if not analysis:
            return AgentResult(success=False, error="No analysis available")

        provider_info = model_manager.get_model_for_role(AgentRole.ARCHITECT)
        if not provider_info:
            return AgentResult(
                success=False, error="No model assigned for architect role"
            )

        provider, model_id = provider_info
        temperature = model_manager.get_temperature_for_role(AgentRole.ARCHITECT)
        max_tokens = model_manager.get_max_tokens_for_role(AgentRole.ARCHITECT)

        system_prompt = """You are an expert software architect. Design a comprehensive system architecture based on the analysis and plan.

Return a JSON object with the following structure:
{
  "architecture": {
    "pattern": "layered|microservices|modular_monolith|serverless|event-driven|clean_architecture|hexagonal",
    "description": "High-level architecture description",
    "components": [
      {
        "name": "component_name",
        "type": "frontend|backend|database|service|api|message_queue|cache|auth|storage",
        "description": "Component description",
        "responsibilities": ["resp1", "resp2"],
        "technology": "specific technology/framework",
        "interfaces": ["interface1", "interface2"]
      }
    ],
    "data_flow": "Description of how data flows through the system",
    "communication": "sync|async|event-driven|mixed",
    "scalability_strategy": "horizontal|vertical|both",
    "deployment_topology": "single|distributed|edge|hybrid"
  },
  "technical_decisions": [
    {
      "decision": "Decision description",
      "rationale": "Why this decision was made",
      "alternatives_considered": ["alt1", "alt2"],
      "trade_offs": "Trade-offs of this decision"
    }
  ],
  "api_design": {
    "style": "REST|GraphQL|gRPC|tRPC|WebSocket",
    "versioning": "URL|header|none",
    "authentication": "JWT|API_KEY|OAuth|session",
    "rate_limiting": "token_bucket|sliding_window|fixed_window",
    "endpoints": [
      {"path": "/api/v1/resource", "method": "GET", "description": "..."}
    ]
  },
  "database_design": {
    "type": "relational|document|graph|key_value|time_series|multi_model",
    "schema_strategy": "migrations|schemaless|hybrid",
    "tables_collections": [
      {"name": "users", "description": "User accounts", "key_fields": ["id", "email"]}
    ],
    "indexing_strategy": "Description of indexing approach"
  },
  "security_design": {
    "authentication": "Strategy for authentication",
    "authorization": "RBAC|ABAC|ACL|custom",
    "data_protection": "encryption|tokenization|masking",
    "audit_logging": true,
    "compliance": ["GDPR", "HIPAA", "SOC2"]
  },
  "observability": {
    "logging": "structured|json|text",
    "metrics": "prometheus|datadog|cloudwatch",
    "tracing": "opentelemetry|jaeger|zipkin",
    "alerting": "pagerduty|opsgenie|custom"
  },
  "infrastructure": {
    "containerization": "docker|podman",
    "orchestration": "kubernetes|docker_swarm|ecs|nomad",
    "ci_cd": "github_actions|gitlab_ci|jenkins|argocd",
    "cloud_provider": "aws|gcp|azure|multi_cloud|on_premise",
    "iac": "terraform|pulumi|cloudformation"
  }
}"""

        analysis_json = json.dumps(analysis, indent=2)
        plan_json = json.dumps(plan, indent=2) if plan else "{}"

        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(
                role="user", content=f"Analysis:\n{analysis_json}\n\nPlan:\n{plan_json}"
            ),
        ]

        try:
            response = await provider.chat(
                messages=messages,
                model=model_id,
                temperature=temperature,
                max_tokens=max_tokens or 8000,
            )

            architecture = json.loads(response.content)

            return AgentResult(
                success=True,
                output=architecture,
                metadata={"model_used": model_id, "provider": provider.provider_name},
            )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse architecture response: {e}")
            return AgentResult(
                success=False, error=f"Failed to parse architecture: {e}"
            )
        except Exception as e:
            logger.error(f"Architect agent failed: {e}")
            return AgentResult(success=False, error=str(e))


class ArchitectureReviewerAgent(BaseAgent):
    """Agent for reviewing architecture decisions."""

    def __init__(
        self,
        name: str = "architecture_reviewer_agent",
        description: str = "Reviews architecture decisions",
        config: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(name=name, description=description, config=config)

    @property
    def agent_type(self) -> str:
        return "architecture_reviewer"

    async def execute(self, context: AgentContext) -> AgentResult:
        """Review architecture for quality, scalability, and best practices."""
        architecture = context.previous_outputs.get("architect")
        if not architecture:
            return AgentResult(success=False, error="No architecture to review")

        provider_info = model_manager.get_model_for_role(AgentRole.REVIEW)
        if not provider_info:
            return AgentResult(success=False, error="No model assigned for review role")

        provider, model_id = provider_info
        temperature = model_manager.get_temperature_for_role(AgentRole.REVIEW)

        system_prompt = """You are an expert architecture reviewer. Review the architecture for:
1. Scalability and performance
2. Security vulnerabilities
3. Maintainability and extensibility
4. Technology choices appropriateness
5. Compliance with best practices
6. Potential single points of failure
7. Data consistency and integrity
8. Operational complexity

Return a JSON object with the following structure:
{
  "overall_score": 85,
  "grade": "B",
  "strengths": ["Strength 1", "Strength 2"],
  "concerns": [
    {
      "severity": "critical|high|medium|low",
      "category": "scalability|security|maintainability|performance|cost|operations",
      "description": "Detailed description",
      "recommendation": "How to address",
      "affected_components": ["comp1", "comp2"]
    }
  ],
  "recommendations": [
    {
      "priority": "high|medium|low",
      "area": "Area name",
      "description": "Detailed recommendation",
      "effort": "low|medium|high",
      "impact": "high|medium|low"
    }
  ],
  "approval": "approved|approved_with_conditions|rejected",
  "conditions": ["Condition 1", "Condition 2"]
}"""

        arch_json = json.dumps(architecture, indent=2)

        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=f"Architecture to review:\n{arch_json}"),
        ]

        try:
            response = await provider.chat(
                messages=messages,
                model=model_id,
                temperature=temperature,
                max_tokens=6000,
            )

            review = json.loads(response.content)

            return AgentResult(
                success=True,
                output=review,
                metadata={"model_used": model_id, "provider": provider.provider_name},
            )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse architecture review: {e}")
            return AgentResult(success=False, error=f"Failed to parse review: {e}")
        except Exception as e:
            logger.error(f"Architecture reviewer failed: {e}")
            return AgentResult(success=False, error=str(e))
