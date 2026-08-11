"""Security agent for security analysis and hardening."""

import json
import logging
import subprocess
from pathlib import Path
from typing import Any

from backend.agents.base import AgentContext, AgentResult, BaseAgent
from backend.core.model_manager import AgentRole, model_manager
from backend.core.providers.interfaces import ChatMessage

logger = logging.getLogger(__name__)


class SecurityAgent(BaseAgent):
    """Agent for security analysis, vulnerability detection, and hardening."""

    def __init__(
        self,
        name: str = "security_agent",
        description: str = "Security analysis and hardening agent",
        config: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(name=name, description=description, config=config)

    @property
    def agent_type(self) -> str:
        return "security"

    async def execute(self, context: AgentContext) -> AgentResult:
        """Perform security analysis on the codebase."""
        builder_output = context.previous_outputs.get(
            "builder"
        ) or context.previous_outputs.get("coder")
        plan = context.previous_outputs.get("planner")
        deep_scan = context.config.get("deep_scan", False)

        if not builder_output:
            return AgentResult(success=False, error="No code to analyze")

        generated_files = builder_output.get("generated_files", [])
        if not generated_files:
            return AgentResult(success=False, error="No files to analyze")

        provider_info = model_manager.get_model_for_role(AgentRole.SECURITY)
        if not provider_info:
            return AgentResult(
                success=False, error="No model assigned for security role"
            )

        provider, model_id = provider_info
        temperature = model_manager.get_temperature_for_role(AgentRole.SECURITY)
        max_tokens = model_manager.get_max_tokens_for_role(AgentRole.SECURITY)

        workspace_path = Path(context.workspace_path)
        all_findings = []
        tools_output = {}

        # Run automated security tools
        if deep_scan:
            tools_output["bandit"] = await self._run_bandit(workspace_path)
            tools_output["safety"] = await self._run_safety(workspace_path)
            tools_output["semgrep"] = await self._run_semgrep(workspace_path)

        # Analyze each file with AI
        for file_rel in generated_files:
            file_path = workspace_path / file_rel
            if not file_path.exists():
                continue

            if self._should_analyze_security(file_path):
                result = await self._analyze_file_security(
                    provider,
                    model_id,
                    file_path,
                    plan,
                    tools_output,
                    temperature,
                    max_tokens,
                )
                if result.success:
                    findings = result.output.get("findings", [])
                    all_findings.extend(findings)

        # Generate security report
        report = self._generate_security_report(all_findings, tools_output)

        return AgentResult(
            success=True,
            output={
                "findings": all_findings,
                "report": report,
                "tools_output": tools_output,
                "files_analyzed": len(generated_files),
            },
            metadata={"model_used": model_id, "provider": provider.provider_name},
        )

    def _should_analyze_security(self, file_path: Path) -> bool:
        """Determine if a file should be analyzed for security."""
        # Skip test files, config files, documentation
        skip_patterns = [
            "test_",
            "_test.py",
            ".test.",
            ".spec.",
            "conftest.py",
            "pytest.ini",
            ".md",
            ".txt",
            ".json",
            ".yaml",
            ".yml",
            ".env",
            ".gitignore",
            "Dockerfile",
            "docker-compose",
            "requirements.txt",
            "package.json",
            "pyproject.toml",
        ]

        file_str = str(file_path).lower()
        return not any(pattern in file_str for pattern in skip_patterns)

    async def _run_bandit(self, workspace_path: Path) -> dict[str, Any]:
        """Run Bandit security linter for Python."""
        try:
            result = subprocess.run(
                ["python", "-m", "bandit", "-r", ".", "-f", "json"],
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.stdout:
                return json.loads(result.stdout)
        except Exception as e:
            logger.debug(f"Bandit failed: {e}")
        return {}

    async def _run_safety(self, workspace_path: Path) -> dict[str, Any]:
        """Run Safety for dependency vulnerabilities."""
        try:
            result = subprocess.run(
                ["python", "-m", "safety", "check", "--json"],
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.stdout:
                return json.loads(result.stdout)
        except Exception as e:
            logger.debug(f"Safety failed: {e}")
        return {}

    async def _run_semgrep(self, workspace_path: Path) -> dict[str, Any]:
        """Run Semgrep for security patterns."""
        try:
            result = subprocess.run(
                ["semgrep", "scan", "--config=auto", "--json", "."],
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=180,
            )
            if result.stdout:
                return json.loads(result.stdout)
        except Exception as e:
            logger.debug(f"Semgrep failed: {e}")
        return {}

    async def _analyze_file_security(
        self,
        provider,
        model_id: str,
        file_path: Path,
        plan: dict[str, Any] | None,
        tools_output: dict[str, Any],
        temperature: float,
        max_tokens: int | None,
    ) -> AgentResult:
        """Analyze a single file for security issues."""
        try:
            source_code = file_path.read_text(encoding="utf-8")
            tech_stack = plan.get("tech_stack", {}) if plan else {}
            language = tech_stack.get("language", "python")

            # Get tool findings for this file
            file_findings = self._extract_file_findings(file_path, tools_output)

            system_prompt = f"""You are a security expert. Perform a thorough security analysis of the code.

Language: {language}
Framework: {tech_stack.get("framework", "N/A")}

Automated Tool Findings for this file:
{json.dumps(file_findings, indent=2) if file_findings else "None"}

Analyze for:
1. Injection vulnerabilities (SQL, command, LDAP, XPath)
2. Authentication/Authorization flaws
3. Cryptographic issues (weak algorithms, hardcoded secrets)
4. Input validation failures
5. Insecure deserialization
6. XXE, SSRF, CSRF vulnerabilities
7. Path traversal and file inclusion
8. Information disclosure
9. Insecure dependencies
10. Business logic flaws
11. OWASP Top 10 issues

Return JSON:
{{
  "file": "path/to/file",
  "findings": [
    {{
      "severity": "critical|high|medium|low|info",
      "category": "injection|auth|crypto|validation|deserialization|xxe|ssrf|csrf|path_traversal|info_disclosure|dependency|logic",
      "cwe": "CWE-XXX",
      "owasp": "A0X:2021",
      "line": 42,
      "description": "Detailed description",
      "impact": "Potential impact",
      "recommendation": "How to fix",
      "code_snippet": "Vulnerable code snippet",
      "fixed_code": "Suggested fix"
    }}
  ],
  "summary": "Overall security assessment"
}}"""

            messages = [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(
                    role="user", content=f"Security analysis for {file_path.name}"
                ),
            ]

            response = await provider.chat(
                messages=messages,
                model=model_id,
                temperature=temperature,
                max_tokens=max_tokens or 6000,
            )

            analysis = json.loads(response.content)
            analysis["file"] = str(file_path)

            return AgentResult(success=True, output=analysis)
        except Exception as e:
            logger.error(f"Security analysis failed for {file_path}: {e}")
            return AgentResult(success=False, error=str(e))

    def _extract_file_findings(
        self, file_path: Path, tools_output: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Extract findings relevant to a specific file from tool outputs."""
        findings = []
        rel_path = str(file_path)

        # Bandit findings
        bandit = tools_output.get("bandit", {})
        for result in bandit.get("results", []):
            if result.get("filename", "").endswith(rel_path) or rel_path in result.get(
                "filename", ""
            ):
                findings.append(
                    {
                        "tool": "bandit",
                        "severity": result.get("issue_severity", "").lower(),
                        "confidence": result.get("issue_confidence", "").lower(),
                        "message": result.get("issue_text", ""),
                        "line": result.get("line_number", 0),
                        "code": result.get("code", ""),
                    }
                )

        # Semgrep findings
        semgrep = tools_output.get("semgrep", {})
        for result in semgrep.get("results", []):
            if result.get("path", "").endswith(rel_path) or rel_path in result.get(
                "path", ""
            ):
                findings.append(
                    {
                        "tool": "semgrep",
                        "severity": result.get("extra", {}).get("severity", "").lower(),
                        "message": result.get("extra", {}).get("message", ""),
                        "line": result.get("start", {}).get("line", 0),
                        "rule_id": result.get("check_id", ""),
                    }
                )

        return findings

    def _generate_security_report(
        self, findings: list[dict[str, Any]], tools_output: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate a comprehensive security report."""
        if not findings:
            return {
                "overall_rating": "A",
                "total_findings": 0,
                "by_severity": {
                    "critical": 0,
                    "high": 0,
                    "medium": 0,
                    "low": 0,
                    "info": 0,
                },
                "by_category": {},
                "recommendations": ["No security issues found"],
                "compliance": {"owasp_top_10": "passed", "cwe_top_25": "passed"},
            }

        by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        by_category = {}

        for finding in findings:
            severity = finding.get("severity", "info")
            if severity in by_severity:
                by_severity[severity] += 1

            category = finding.get("category", "other")
            by_category[category] = by_category.get(category, 0) + 1

        # Determine overall rating
        if by_severity["critical"] > 0:
            rating = "F"
        elif by_severity["high"] > 5:
            rating = "D"
        elif by_severity["high"] > 0 or by_severity["medium"] > 10:
            rating = "C"
        elif by_severity["medium"] > 0:
            rating = "B"
        else:
            rating = "A"

        recommendations = []
        if by_severity["critical"] > 0:
            recommendations.append(
                f"URGENT: Fix {by_severity['critical']} critical vulnerability(ies) immediately"
            )
        if by_severity["high"] > 0:
            recommendations.append(
                f"Address {by_severity['high']} high-severity issue(s) before deployment"
            )
        if by_severity["medium"] > 0:
            recommendations.append(
                f"Plan to fix {by_severity['medium']} medium-severity issue(s)"
            )

        recommendations.extend(
            [
                "Implement security headers (CSP, HSTS, X-Frame-Options)",
                "Enable rate limiting on all API endpoints",
                "Use parameterized queries for all database operations",
                "Implement proper input validation and sanitization",
                "Store secrets in secure vault, never in code",
                "Enable audit logging for security events",
                "Regularly update dependencies and run security scans",
            ]
        )

        return {
            "overall_rating": rating,
            "total_findings": len(findings),
            "by_severity": by_severity,
            "by_category": by_category,
            "recommendations": recommendations,
            "compliance": {
                "owasp_top_10": "passed"
                if by_severity["critical"] == 0 and by_severity["high"] == 0
                else "failed",
                "cwe_top_25": "passed" if by_severity["critical"] == 0 else "failed",
            },
        }


class SecurityHardeningAgent(BaseAgent):
    """Agent for applying security fixes and hardening."""

    def __init__(
        self,
        name: str = "security_hardening_agent",
        description: str = "Security hardening agent",
        config: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(name=name, description=description, config=config)

    @property
    def agent_type(self) -> str:
        return "security_hardening"

    async def execute(self, context: AgentContext) -> AgentResult:
        """Apply security fixes based on security analysis."""
        security_output = context.previous_outputs.get("security")
        if not security_output:
            return AgentResult(success=False, error="No security analysis available")

        findings = security_output.get("findings", [])
        if not findings:
            return AgentResult(
                success=True, output={"message": "No security issues to fix"}
            )

        provider_info = model_manager.get_model_for_role(AgentRole.SECURITY)
        if not provider_info:
            return AgentResult(
                success=False, error="No model assigned for security role"
            )

        provider, model_id = provider_info
        temperature = model_manager.get_temperature_for_role(AgentRole.SECURITY)
        max_tokens = model_manager.get_max_tokens_for_role(AgentRole.SECURITY)

        workspace_path = Path(context.workspace_path)
        fixed_files = []
        errors = []

        # Group findings by file
        findings_by_file = {}
        for finding in findings:
            file_path = finding.get("file", "")
            if file_path:
                if file_path not in findings_by_file:
                    findings_by_file[file_path] = []
                findings_by_file[file_path].append(finding)

        for file_rel, file_findings in findings_by_file.items():
            file_path = workspace_path / file_rel
            if not file_path.exists():
                continue

            result = await self._apply_security_fixes(
                provider, model_id, file_path, file_findings, temperature, max_tokens
            )
            if result.success:
                fixed_files.append(file_rel)
            else:
                errors.append(f"{file_rel}: {result.error}")

        return AgentResult(
            success=len(errors) == 0,
            output={"fixed_files": fixed_files, "errors": errors},
            error="; ".join(errors) if errors else None,
            metadata={"model_used": model_id, "provider": provider.provider_name},
        )

    async def _apply_security_fixes(
        self,
        provider,
        model_id: str,
        file_path: Path,
        findings: list[dict[str, Any]],
        temperature: float,
        max_tokens: int | None,
    ) -> AgentResult:
        """Apply security fixes to a file."""
        try:
            source_code = file_path.read_text(encoding="utf-8")

            findings_json = json.dumps(findings, indent=2)

            system_prompt = f"""You are a security expert. Fix all security vulnerabilities in the code.

Security Findings:
{findings_json}

Requirements:
1. Fix ALL identified vulnerabilities
2. Maintain exact same functionality
3. Use secure coding practices
4. Don't introduce new issues
5. Follow OWASP secure coding guidelines
6. Return the COMPLETE fixed file content

Source Code:
{source_code}

Return the complete fixed file content."""

            messages = [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(
                    role="user", content=f"Fix security issues in {file_path.name}"
                ),
            ]

            response = await provider.chat(
                messages=messages,
                model=model_id,
                temperature=temperature,
                max_tokens=max_tokens or 8000,
            )

            file_path.write_text(response.content, encoding="utf-8")
            return AgentResult(success=True, output=str(file_path))
        except Exception as e:
            logger.error(f"Failed to apply security fixes to {file_path}: {e}")
            return AgentResult(success=False, error=str(e))
