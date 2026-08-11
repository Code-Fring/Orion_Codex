"""Dependency Manager agent for dependency analysis and management."""

import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Any

import toml
from backend.agents.base import AgentContext, AgentResult, BaseAgent
from backend.core.model_manager import AgentRole, model_manager
from backend.core.providers.interfaces import ChatMessage

logger = logging.getLogger(__name__)


class DependencyManagerAgent(BaseAgent):
    """Agent for dependency analysis, updates, and management."""

    def __init__(
        self,
        name: str = "dependency_agent",
        description: str = "Manages project dependencies",
        config: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(name=name, description=description, config=config)

    @property
    def agent_type(self) -> str:
        return "dependency"

    async def execute(self, context: AgentContext) -> AgentResult:
        """Analyze and manage project dependencies."""
        builder_output = context.previous_outputs.get(
            "builder"
        ) or context.previous_outputs.get("coder")
        plan = context.previous_outputs.get("planner")
        action = context.config.get(
            "action", "analyze"
        )  # analyze, update, audit, license

        if not builder_output:
            return AgentResult(success=False, error="No project to analyze")

        workspace_path = Path(context.workspace_path)
        tech_stack = plan.get("tech_stack", {}) if plan else {}
        language = tech_stack.get("language", "python")

        provider_info = model_manager.get_model_for_role(AgentRole.DEPENDENCY)
        if not provider_info:
            return AgentResult(
                success=False, error="No model assigned for dependency role"
            )

        provider, model_id = provider_info
        temperature = model_manager.get_temperature_for_role(AgentRole.DEPENDENCY)
        max_tokens = model_manager.get_max_tokens_for_role(AgentRole.DEPENDENCY)

        if action == "analyze":
            return await self._analyze_dependencies(
                workspace_path, language, provider, model_id, temperature, max_tokens
            )
        elif action == "update":
            return await self._update_dependencies(
                workspace_path, language, provider, model_id, temperature, max_tokens
            )
        elif action == "audit":
            return await self._audit_dependencies(workspace_path, language)
        elif action == "license":
            return await self._check_licenses(workspace_path, language)
        else:
            return AgentResult(success=False, error=f"Unknown action: {action}")

    async def _analyze_dependencies(
        self,
        workspace_path: Path,
        language: str,
        provider,
        model_id: str,
        temperature: float,
        max_tokens: int | None,
    ) -> AgentResult:
        """Analyze project dependencies."""
        try:
            # Parse dependency files
            deps = self._parse_dependencies(workspace_path, language)

            # Check for outdated packages
            outdated = await self._check_outdated(workspace_path, language)

            # Check for vulnerabilities
            vulns = await self._check_vulnerabilities(workspace_path, language)

            # Analyze with AI for recommendations
            ai_analysis = await self._ai_dependency_analysis(
                provider,
                model_id,
                deps,
                outdated,
                vulns,
                language,
                temperature,
                max_tokens,
            )

            return AgentResult(
                success=True,
                output={
                    "dependencies": deps,
                    "outdated": outdated,
                    "vulnerabilities": vulns,
                    "analysis": ai_analysis,
                },
                metadata={"model_used": model_id, "provider": provider.provider_name},
            )
        except Exception as e:
            logger.error(f"Dependency analysis failed: {e}")
            return AgentResult(success=False, error=str(e))

    def _parse_dependencies(
        self, workspace_path: Path, language: str
    ) -> dict[str, Any]:
        """Parse dependency files."""
        deps = {"production": {}, "development": {}}

        if language == "python":
            # requirements.txt
            req_file = workspace_path / "requirements.txt"
            if req_file.exists():
                content = req_file.read_text()
                for line in content.splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # Parse package==version or package>=version
                        match = re.match(r"^([a-zA-Z0-9_-]+)([=<>!~]+.*)?$", line)
                        if match:
                            name = match.group(1)
                            version = match.group(2) or "unspecified"
                            deps["production"][name] = version

            # pyproject.toml
            pyproject = workspace_path / "pyproject.toml"
            if pyproject.exists():
                try:
                    data = toml.loads(pyproject.read_text())
                    for dep in data.get("project", {}).get("dependencies", []):
                        match = re.match(r"^([a-zA-Z0-9_-]+)([=<>!~]+.*)?$", dep)
                        if match:
                            name = match.group(1)
                            version = match.group(2) or "unspecified"
                            deps["production"][name] = version

                    for dep in (
                        data.get("project", {})
                        .get("optional-dependencies", {})
                        .get("dev", [])
                    ):
                        match = re.match(r"^([a-zA-Z0-9_-]+)([=<>!~]+.*)?$", dep)
                        if match:
                            name = match.group(1)
                            version = match.group(2) or "unspecified"
                            deps["development"][name] = version
                except Exception:
                    pass

        elif language in ("javascript", "typescript"):
            # package.json
            pkg_file = workspace_path / "package.json"
            if pkg_file.exists():
                try:
                    data = json.loads(pkg_file.read_text())
                    deps["production"] = data.get("dependencies", {})
                    deps["development"] = data.get("devDependencies", {})
                except Exception:
                    pass

        return deps

    async def _check_outdated(
        self, workspace_path: Path, language: str
    ) -> list[dict[str, Any]]:
        """Check for outdated packages."""
        outdated = []

        try:
            if language == "python":
                result = subprocess.run(
                    ["pip", "list", "--outdated", "--format=json"],
                    cwd=workspace_path,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.stdout:
                    outdated = json.loads(result.stdout)

            elif language in ("javascript", "typescript"):
                result = subprocess.run(
                    ["npm", "outdated", "--json"],
                    cwd=workspace_path,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.stdout:
                    data = json.loads(result.stdout)
                    outdated = [
                        {
                            "name": k,
                            "current": v.get("current"),
                            "wanted": v.get("wanted"),
                            "latest": v.get("latest"),
                        }
                        for k, v in data.items()
                    ]
        except Exception as e:
            logger.debug(f"Outdated check failed: {e}")

        return outdated

    async def _check_vulnerabilities(
        self, workspace_path: Path, language: str
    ) -> list[dict[str, Any]]:
        """Check for known vulnerabilities."""
        vulns = []

        try:
            if language == "python":
                result = subprocess.run(
                    ["python", "-m", "safety", "check", "--json"],
                    cwd=workspace_path,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.stdout:
                    data = json.loads(result.stdout)
                    vulns = data.get("vulnerabilities", [])

            elif language in ("javascript", "typescript"):
                result = subprocess.run(
                    ["npm", "audit", "--json"],
                    cwd=workspace_path,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.stdout:
                    data = json.loads(result.stdout)
                    vulns = data.get("vulnerabilities", {})
        except Exception as e:
            logger.debug(f"Vulnerability check failed: {e}")

        return vulns

    async def _ai_dependency_analysis(
        self,
        provider,
        model_id: str,
        deps: dict[str, Any],
        outdated: list[dict[str, Any]],
        vulns: list[dict[str, Any]],
        language: str,
        temperature: float,
        max_tokens: int | None,
    ) -> dict[str, Any]:
        """Get AI analysis of dependencies."""
        try:
            system_prompt = f"""You are a dependency management expert. Analyze the project dependencies and provide recommendations.

Language: {language}

Dependencies:
{json.dumps(deps, indent=2)}

Outdated Packages:
{json.dumps(outdated, indent=2)}

Vulnerabilities:
{json.dumps(vulns, indent=2)}

Provide JSON response:
{{
  "health_score": 85,
  "recommendations": [
    {{
      "priority": "high|medium|low",
      "type": "update|replace|remove|audit",
      "package": "package-name",
      "current_version": "1.0.0",
      "recommended_version": "2.0.0",
      "reason": "Security vulnerability / Major improvements / Deprecated",
      "effort": "low|medium|high",
      "breaking_changes": false
    }}
  ],
  "summary": "Overall dependency health assessment",
  "technical_debt": ["List of technical debt items"],
  "maintenance_burden": "low|medium|high"
}}"""

            messages = [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content="Analyze dependencies"),
            ]

            response = await provider.chat(
                messages=messages,
                model=model_id,
                temperature=temperature,
                max_tokens=max_tokens or 4000,
            )

            return json.loads(response.content)
        except Exception as e:
            logger.error(f"AI dependency analysis failed: {e}")
            return {
                "health_score": 0,
                "recommendations": [],
                "summary": "Analysis failed",
                "technical_debt": [],
                "maintenance_burden": "unknown",
            }

    async def _update_dependencies(
        self,
        workspace_path: Path,
        language: str,
        provider,
        model_id: str,
        temperature: float,
        max_tokens: int | None,
    ) -> AgentResult:
        """Update dependencies based on analysis."""
        # First analyze
        analysis_result = await self._analyze_dependencies(
            workspace_path, language, provider, model_id, temperature, max_tokens
        )
        if not analysis_result.success:
            return analysis_result

        recommendations = analysis_result.output.get("analysis", {}).get(
            "recommendations", []
        )
        high_priority = [r for r in recommendations if r.get("priority") == "high"]

        if not high_priority:
            return AgentResult(
                success=True, output={"message": "No high-priority updates needed"}
            )

        updated = []
        errors = []

        for rec in high_priority:
            package = rec.get("package")
            version = rec.get("recommended_version")

            try:
                if language == "python":
                    result = subprocess.run(
                        ["pip", "install", f"{package}=={version}"],
                        cwd=workspace_path,
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )
                elif language in ("javascript", "typescript"):
                    result = subprocess.run(
                        ["npm", "install", f"{package}@{version}"],
                        cwd=workspace_path,
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )

                if result.returncode == 0:
                    updated.append(f"{package}@{version}")
                else:
                    errors.append(f"{package}: {result.stderr}")
            except Exception as e:
                errors.append(f"{package}: {e}")

        return AgentResult(
            success=len(errors) == 0,
            output={"updated": updated, "errors": errors},
            error="; ".join(errors) if errors else None,
        )

    async def _audit_dependencies(
        self, workspace_path: Path, language: str
    ) -> AgentResult:
        """Perform full dependency audit."""
        vulns = await self._check_vulnerabilities(workspace_path, language)
        outdated = await self._check_outdated(workspace_path, language)

        return AgentResult(
            success=True,
            output={
                "vulnerabilities": vulns,
                "outdated": outdated,
                "total_vulnerabilities": len(vulns)
                if isinstance(vulns, list)
                else len(vulns.get("vulnerabilities", {})),
                "total_outdated": len(outdated),
            },
        )

    async def _check_licenses(self, workspace_path: Path, language: str) -> AgentResult:
        """Check dependency licenses."""
        licenses = []

        try:
            if language == "python":
                result = subprocess.run(
                    ["pip", "licenses", "--format=json"],
                    cwd=workspace_path,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.stdout:
                    licenses = json.loads(result.stdout)

            elif language in ("javascript", "typescript"):
                result = subprocess.run(
                    ["npx", "license-checker", "--json"],
                    cwd=workspace_path,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.stdout:
                    licenses = json.loads(result.stdout)
        except Exception as e:
            logger.debug(f"License check failed: {e}")

        # Categorize licenses
        allowed = [
            "MIT",
            "BSD-2-Clause",
            "BSD-3-Clause",
            "Apache-2.0",
            "ISC",
            "Python-2.0",
        ]
        copyleft = ["GPL-2.0", "GPL-3.0", "LGPL-2.1", "LGPL-3.0", "AGPL-3.0"]
        problematic = []

        for pkg in licenses:
            license_type = pkg.get("License", pkg.get("license", "Unknown"))
            if license_type in copyleft:
                problematic.append(
                    {
                        "package": pkg.get("Name", pkg.get("name")),
                        "license": license_type,
                        "issue": "Copyleft license",
                    }
                )
            elif license_type not in allowed and license_type != "Unknown":
                problematic.append(
                    {
                        "package": pkg.get("Name", pkg.get("name")),
                        "license": license_type,
                        "issue": "Unrecognized license",
                    }
                )

        return AgentResult(
            success=True,
            output={
                "licenses": licenses,
                "problematic": problematic,
                "summary": f"{len(problematic)} packages with potential license issues",
            },
        )
