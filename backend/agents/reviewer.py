"""Reviewer agent for code review and quality assurance."""

import json
import logging
from pathlib import Path
from typing import Any

from backend.agents.base import AgentContext, AgentResult, BaseAgent
from backend.core.providers.interfaces import ChatMessage
from backend.core.providers.registry import provider_registry

logger = logging.getLogger(__name__)


class ReviewerAgent(BaseAgent):
    """Agent for reviewing code quality and suggesting improvements."""

    def __init__(
        self,
        name: str = "reviewer_agent",
        description: str = "Reviews code quality",
        config: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(name=name, description=description, config=config)

    @property
    def agent_type(self) -> str:
        return "reviewer"

    async def execute(self, context: AgentContext) -> AgentResult:
        """Review generated code for quality, security, and best practices."""
        builder_output = context.previous_outputs.get("builder")
        plan = context.previous_outputs.get("planner")

        if not builder_output:
            return AgentResult(success=False, error="No builder output available")

        generated_files = builder_output.get("generated_files", [])
        if not generated_files:
            return AgentResult(success=False, error="No files to review")

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

        workspace_path = Path(context.workspace_path)
        reviews = []
        issues_found = 0

        for file_rel in generated_files:
            file_path = workspace_path / file_rel
            if not file_path.exists():
                continue

            if self._should_review(file_path):
                result = await self._review_file(
                    provider, model, file_path, plan, workspace_path
                )
                reviews.append(result)
                if result.get("issues"):
                    issues_found += len(result["issues"])

        # Generate summary report
        summary = self._generate_summary(reviews, issues_found)

        return AgentResult(
            success=True,
            output={
                "reviews": reviews,
                "summary": summary,
                "total_files_reviewed": len(reviews),
                "total_issues": issues_found,
            },
            metadata={"model_used": model.id, "provider": provider.provider_name},
        )

    def _should_review(self, file_path: Path) -> bool:
        """Determine if a file should be reviewed."""
        # Skip non-code files
        code_extensions = {
            ".py",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".go",
            ".rs",
            ".java",
            ".cpp",
            ".c",
            ".h",
        }
        return file_path.suffix in code_extensions

    async def _review_file(
        self,
        provider,
        model,
        file_path: Path,
        plan: dict[str, Any],
        workspace_path: Path,
    ) -> dict[str, Any]:
        """Review a single file."""
        try:
            source_code = file_path.read_text(encoding="utf-8")

            tech_stack = plan.get("tech_stack", {}) if plan else {}
            language = tech_stack.get("language", "python")

            system_prompt = f"""You are an expert code reviewer. Review the following code for:
1. Code quality and best practices
2. Security vulnerabilities
3. Performance issues
4. Maintainability and readability
5. Adherence to {language} conventions and {tech_stack.get("framework", "the framework")} patterns
6. SOLID principles and clean architecture
7. Error handling and edge cases
8. Testability

Return a JSON object with the following structure:
{{
  "file": "path/to/file",
  "score": 85,
  "issues": [
    {{
      "severity": "critical|high|medium|low|info",
      "category": "security|performance|style|bug|maintainability",
      "line": 42,
      "message": "Description of the issue",
      "suggestion": "How to fix it"
    }}
  ],
  "strengths": ["Good practice 1", "Good practice 2"],
  "summary": "Overall assessment"
}}

Source Code ({language}):
```{language}
{source_code}
```"""

            messages = [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=f"Review {file_path.name}"),
            ]

            response = await provider.chat(
                messages=messages,
                model=model.id,
                temperature=0.1,
                max_tokens=3000,
            )

            review = json.loads(response.content)
            review["file"] = str(file_path.relative_to(workspace_path))

            return review
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse review response: {e}")
            return {
                "file": str(file_path.relative_to(workspace_path)),
                "score": 0,
                "issues": [
                    {
                        "severity": "high",
                        "category": "parse_error",
                        "message": f"Failed to parse review: {e}",
                    }
                ],
                "strengths": [],
                "summary": "Review parsing failed",
            }
        except Exception as e:
            logger.error(f"Failed to review {file_path}: {e}")
            return {
                "file": str(file_path.relative_to(workspace_path)),
                "score": 0,
                "issues": [
                    {"severity": "high", "category": "error", "message": str(e)}
                ],
                "strengths": [],
                "summary": "Review failed",
            }

    def _generate_summary(
        self, reviews: list[dict[str, Any]], total_issues: int
    ) -> dict[str, Any]:
        """Generate a summary of all reviews."""
        if not reviews:
            return {
                "overall_score": 0,
                "grade": "F",
                "critical_issues": 0,
                "recommendations": [],
            }

        scores = [r.get("score", 0) for r in reviews]
        avg_score = sum(scores) / len(scores)

        # Count issues by severity
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for review in reviews:
            for issue in review.get("issues", []):
                severity = issue.get("severity", "info")
                if severity in severity_counts:
                    severity_counts[severity] += 1

        # Determine grade
        if avg_score >= 90:
            grade = "A"
        elif avg_score >= 80:
            grade = "B"
        elif avg_score >= 70:
            grade = "C"
        elif avg_score >= 60:
            grade = "D"
        else:
            grade = "F"

        # Generate recommendations
        recommendations = []
        if severity_counts["critical"] > 0:
            recommendations.append(
                f"Fix {severity_counts['critical']} critical issue(s) immediately"
            )
        if severity_counts["high"] > 0:
            recommendations.append(
                f"Address {severity_counts['high']} high-severity issue(s)"
            )
        if avg_score < 70:
            recommendations.append("Consider refactoring for better code quality")

        return {
            "overall_score": round(avg_score, 1),
            "grade": grade,
            "severity_breakdown": severity_counts,
            "total_issues": total_issues,
            "files_reviewed": len(reviews),
            "recommendations": recommendations,
        }
