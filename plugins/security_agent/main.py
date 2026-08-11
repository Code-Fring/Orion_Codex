"""Security Analysis Agent Plugin."""

import asyncio
import logging
import os
import re
from pathlib import Path
from typing import Any

from backend.plugins.sdk.base import AgentPlugin, PluginContext, PluginManifest
from backend.agents.base import BaseAgent, AgentContext, AgentResult, AgentStatus
from backend.events import publish_event, EventType

logger = logging.getLogger(__name__)


# Security patterns for different vulnerability types
SECURITY_PATTERNS = {
    "sql_injection": [
        r"execute\s*\(\s*[\"'].*[%s].*[\"']\s*%",
        r"cursor\.execute\s*\(\s*[\"'].*\+.*[\"']",
        r"\.raw\s*\(\s*[\"'].*\+.*[\"']",
    ],
    "xss": [
        r"innerHTML\s*=",
        r"dangerouslySetInnerHTML",
        r"v-html\s*=",
        r"@Html\.Raw",
    ],
    "hardcoded_secrets": [
        r"(api[_-]?key|secret[_-]?key|password|token)\s*[=:]\s*[\"'][^\"']+[\"']",
        r"(aws[_-]?access[_-]?key|aws[_-]?secret[_-]?key)\s*[=:]\s*[\"'][^\"']+[\"']",
    ],
    "path_traversal": [
        r"\.\./",
        r"os\.path\.join.*\.\.",
    ],
    "command_injection": [
        r"subprocess\.(call|run|Popen).*shell=True",
        r"os\.system\s*\(",
        r"eval\s*\(",
        r"exec\s*\(",
    ],
    "insecure_random": [
        r"random\.random\s*\(",
        r"Math\.random\s*\(",
    ],
    "weak_crypto": [
        r"md5\s*\(",
        r"sha1\s*\(",
        r"DES\s*\(",
        r"RC4\s*\(",
    ],
}


class SecurityAgentPlugin(AgentPlugin):
    """Security Analysis Agent Plugin."""

    def __init__(self, manifest: PluginManifest, context: PluginContext) -> None:
        super().__init__(manifest, context)
        self._deep_scan = False
        self._scan_types = ["sast", "secrets", "dependencies", "config"]

    async def _on_initialize(self) -> None:
        """Initialize the agent."""
        self._deep_scan = self.get_config("deep_scan", False)
        scan_types = self.get_config("scan_types")
        if scan_types:
            self._scan_types = scan_types

    async def _on_shutdown(self) -> None:
        """Shutdown the agent."""
        pass

    def get_agent_schema(self) -> dict[str, Any]:
        """Get agent schema for registration."""
        return {
            "name": "security_analyzer",
            "description": "Security analysis agent for vulnerability scanning",
            "capabilities": ["sast", "secrets_detection", "dependency_scan", "config_audit"],
        }

    async def create_agent(self, config: dict[str, Any] | None = None) -> BaseAgent:
        """Create an agent instance."""
        return SecurityAnalysisAgent(config=config or {})


class SecurityAnalysisAgent(BaseAgent):
    """Security analysis agent implementation."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__("SecurityAnalyzer", "Security vulnerability scanner", config)
        self._deep_scan = config.get("deep_scan", False)
        self._scan_types = config.get("scan_types", ["sast", "secrets", "dependencies", "config"])

    @property
    def agent_type(self) -> str:
        return "security_analyzer"

    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute security analysis."""
        self.status = AgentStatus.RUNNING

        try:
            workspace_path = Path(context.workspace_path)
            if not workspace_path.exists():
                return AgentResult(
                    success=False,
                    error=f"Workspace not found: {workspace_path}"
                )

            findings = []

            # Run different scan types
            if "secrets" in self._scan_types:
                secrets_findings = await self._scan_secrets(workspace_path)
                findings.extend(secrets_findings)

            if "sast" in self._scan_types:
                sast_findings = await self._scan_sast(workspace_path)
                findings.extend(sast_findings)

            if "dependencies" in self._scan_types:
                dep_findings = await self._scan_dependencies(workspace_path)
                findings.extend(dep_findings)

            if "config" in self._scan_types:
                config_findings = await self._scan_config(workspace_path)
                findings.extend(config_findings)

            # Generate report
            report = self._generate_report(findings)

            # Publish event
            await publish_event(EventType.AGENT_COMPLETED, {
                "agent_type": "security_analyzer",
                "project_id": context.project_id,
                "findings_count": len(findings),
            })

            return AgentResult(
                success=True,
                output={"findings": findings, "report": report},
                metadata={"scan_types": self._scan_types}
            )

        except Exception as e:
            logger.error(f"Security analysis failed: {e}")
            return AgentResult(success=False, error=str(e))

    async def _scan_secrets(self, workspace_path: Path) -> list[dict[str, Any]]:
        """Scan for hardcoded secrets."""
        findings = []
        patterns = SECURITY_PATTERNS.get("hardcoded_secrets", [])

        for file_path in workspace_path.rglob("*"):
            if file_path.is_file() and file_path.suffix in [".py", ".js", ".ts", ".json", ".yaml", ".yml", ".env", ".config"]:
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    for i, line in enumerate(content.splitlines(), 1):
                        for pattern in patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                findings.append({
                                    "type": "secret",
                                    "severity": "high",
                                    "file": str(file_path.relative_to(workspace_path)),
                                    "line": i,
                                    "description": "Potential hardcoded secret detected",
                                    "code": line.strip()[:100],
                                })
                except Exception:
                    pass

        return findings

    async def _scan_sast(self, workspace_path: Path) -> list[dict[str, Any]]:
        """Static application security testing."""
        findings = []

        for category, patterns in SECURITY_PATTERNS.items():
            if category == "hardcoded_secrets":
                continue

            for file_path in workspace_path.rglob("*"):
                if file_path.is_file() and file_path.suffix in [".py", ".js", ".ts", ".java", ".go", ".php"]:
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        for i, line in enumerate(content.splitlines(), 1):
                            for pattern in patterns:
                                if re.search(pattern, line):
                                    severity = self._get_severity(category)
                                    findings.append({
                                        "type": category,
                                        "severity": severity,
                                        "file": str(file_path.relative_to(workspace_path)),
                                        "line": i,
                                        "description": f"Potential {category.replace('_', ' ')} vulnerability",
                                        "code": line.strip()[:100],
                                    })
                    except Exception:
                        pass

        return findings

    async def _scan_dependencies(self, workspace_path: Path) -> list[dict[str, Any]]:
        """Scan dependencies for vulnerabilities."""
        findings = []

        # Check for common vulnerable patterns in dependency files
        dep_files = [
            "requirements.txt", "pyproject.toml", "setup.py", "Pipfile",
            "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
            "Cargo.toml", "Cargo.lock", "go.mod", "go.sum",
            "pom.xml", "build.gradle", "build.gradle.kts",
            "composer.json", "composer.lock",
        ]

        for dep_file in dep_files:
            file_path = workspace_path / dep_file
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding="utf-8")
                    # Check for known vulnerable patterns
                    if "version" in content.lower() or '"' in content:
                        findings.append({
                            "type": "dependency",
                            "severity": "info",
                            "file": dep_file,
                            "line": 0,
                            "description": f"Dependency file found: {dep_file}. Run dependency audit tool for detailed analysis.",
                            "code": "",
                        })
                except Exception:
                    pass

        return findings

    async def _scan_config(self, workspace_path: Path) -> list[dict[str, Any]]:
        """Scan configuration files for security issues."""
        findings = []

        config_files = [
            ".env", ".env.local", ".env.production", ".env.development",
            "docker-compose.yml", "docker-compose.yaml",
            "Dockerfile", "dockerfile",
            "kubernetes/", "k8s/", ".kube/",
            ".github/workflows/", ".gitlab-ci.yml",
            "terraform/", "*.tf",
            "ansible/", "*.yml", "*.yaml",
        ]

        for pattern in config_files:
            for file_path in workspace_path.rglob(pattern):
                if file_path.is_file():
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        # Check for secrets in config
                        for i, line in enumerate(content.splitlines(), 1):
                            for pat in SECURITY_PATTERNS["hardcoded_secrets"]:
                                if re.search(pat, line, re.IGNORECASE):
                                    findings.append({
                                        "type": "config_secret",
                                        "severity": "high",
                                        "file": str(file_path.relative_to(workspace_path)),
                                        "line": i,
                                        "description": "Secret found in configuration file",
                                        "code": line.strip()[:100],
                                    })
                    except Exception:
                        pass

        return findings

    def _get_severity(self, category: str) -> str:
        """Get severity for vulnerability category."""
        severity_map = {
            "sql_injection": "critical",
            "xss": "high",
            "command_injection": "critical",
            "path_traversal": "high",
            "weak_crypto": "medium",
            "insecure_random": "low",
        }
        return severity_map.get(category, "medium")

    def _generate_report(self, findings: list[dict[str, Any]]) -> dict[str, Any]:
        """Generate security report."""
        by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        by_type = {}

        for finding in findings:
            severity = finding.get("severity", "medium")
            by_severity[severity] = by_severity.get(severity, 0) + 1

            ftype = finding.get("type", "unknown")
            by_type[ftype] = by_type.get(ftype, 0) + 1

        # Determine overall rating
        if by_severity["critical"] > 0:
            overall_rating = "Critical"
        elif by_severity["high"] > 0:
            overall_rating = "High"
        elif by_severity["medium"] > 0:
            overall_rating = "Medium"
        elif by_severity["low"] > 0:
            overall_rating = "Low"
        else:
            overall_rating = "Clean"

        return {
            "total_findings": len(findings),
            "by_severity": by_severity,
            "by_type": by_type,
            "overall_rating": overall_rating,
            "scan_timestamp": __import__('datetime').datetime.utcnow().isoformat(),
        }