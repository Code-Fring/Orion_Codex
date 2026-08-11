"""Documentation Generation Agent Plugin."""

import asyncio
import logging
import ast
import re
from pathlib import Path
from typing import Any

from backend.plugins.sdk.base import AgentPlugin, PluginContext, PluginManifest
from backend.agents.base import BaseAgent, AgentContext, AgentResult, AgentStatus
from backend.events import publish_event, EventType

logger = logging.getLogger(__name__)


class DocumentationAgentPlugin(AgentPlugin):
    """Documentation Generation Agent Plugin."""

    def __init__(self, manifest: PluginManifest, context: PluginContext) -> None:
        super().__init__(manifest, context)
        self._output_format = "markdown"
        self._include_private = False
        self._generate_readme = True
        self._generate_api_docs = True

    async def _on_initialize(self) -> None:
        """Initialize the agent."""
        self._output_format = self.get_config("output_format", "markdown")
        self._include_private = self.get_config("include_private", False)
        self._generate_readme = self.get_config("generate_readme", True)
        self._generate_api_docs = self.get_config("generate_api_docs", True)

    async def _on_shutdown(self) -> None:
        """Shutdown the agent."""
        pass

    def get_agent_schema(self) -> dict[str, Any]:
        """Get agent schema for registration."""
        return {
            "name": "documentation_generator",
            "description": "Documentation generation agent for code projects",
            "capabilities": ["readme_generation", "api_docs", "code_comments", "architecture_docs"],
        }

    async def create_agent(self, config: dict[str, Any] | None = None) -> BaseAgent:
        """Create an agent instance."""
        return DocumentationAgent(config=config or {})


class DocumentationAgent(BaseAgent):
    """Documentation generation agent implementation."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__("DocumentationGenerator", "Code documentation generator", config)
        self._output_format = config.get("output_format", "markdown")
        self._include_private = config.get("include_private", False)
        self._generate_readme = config.get("generate_readme", True)
        self._generate_api_docs = config.get("generate_api_docs", True)

    @property
    def agent_type(self) -> str:
        return "documentation_generator"

    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute documentation generation."""
        self.status = AgentStatus.RUNNING

        try:
            workspace_path = Path(context.workspace_path)
            if not workspace_path.exists():
                return AgentResult(
                    success=False,
                    error=f"Workspace not found: {workspace_path}"
                )

            generated_files = []

            # Analyze project structure
            project_info = self._analyze_project(workspace_path)

            # Generate README
            if self._generate_readme:
                readme_path = workspace_path / "README.md"
                readme_content = self._generate_readme_content(project_info)
                readme_path.write_text(readme_content, encoding="utf-8")
                generated_files.append(str(readme_path.relative_to(workspace_path)))

            # Generate API docs
            if self._generate_api_docs:
                api_docs = self._generate_api_docs(project_info)
                for doc_path, content in api_docs.items():
                    full_path = workspace_path / doc_path
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(content, encoding="utf-8")
                    generated_files.append(doc_path)

            # Generate architecture docs
            arch_path = workspace_path / "docs" / "architecture.md"
            arch_content = self._generate_architecture_docs(project_info)
            arch_path.parent.mkdir(parents=True, exist_ok=True)
            arch_path.write_text(arch_content, encoding="utf-8")
            generated_files.append(str(arch_path.relative_to(workspace_path)))

            # Publish event
            await publish_event(EventType.AGENT_COMPLETED, {
                "agent_type": "documentation_generator",
                "project_id": context.project_id,
                "generated_files": generated_files,
            })

            return AgentResult(
                success=True,
                output={
                    "generated_files": generated_files,
                    "project_info": project_info,
                },
                metadata={"output_format": self._output_format}
            )

        except Exception as e:
            logger.error(f"Documentation generation failed: {e}")
            return AgentResult(success=False, error=str(e))

    def _analyze_project(self, workspace_path: Path) -> dict[str, Any]:
        """Analyze project structure and extract information."""
        project_info = {
            "name": workspace_path.name,
            "description": "",
            "language": "unknown",
            "framework": "unknown",
            "files": [],
            "modules": [],
            "classes": [],
            "functions": [],
            "dependencies": [],
            "entry_points": [],
        }

        # Detect language and framework
        if (workspace_path / "package.json").exists():
            project_info["language"] = "javascript"
            project_info["framework"] = self._detect_js_framework(workspace_path)
        elif (workspace_path / "pyproject.toml").exists() or (workspace_path / "requirements.txt").exists():
            project_info["language"] = "python"
            project_info["framework"] = self._detect_py_framework(workspace_path)
        elif (workspace_path / "Cargo.toml").exists():
            project_info["language"] = "rust"
        elif (workspace_path / "go.mod").exists():
            project_info["language"] = "go"
        elif (workspace_path / "pom.xml").exists():
            project_info["language"] = "java"
        elif (workspace_path / "composer.json").exists():
            project_info["language"] = "php"

        # Extract code information based on language
        if project_info["language"] == "python":
            self._analyze_python(workspace_path, project_info)
        elif project_info["language"] == "javascript":
            self._analyze_javascript(workspace_path, project_info)

        return project_info

    def _detect_py_framework(self, path: Path) -> str:
        """Detect Python framework."""
        for file in ["pyproject.toml", "requirements.txt", "setup.py"]:
            fpath = path / file
            if fpath.exists():
                content = fpath.read_text()
                if "fastapi" in content.lower():
                    return "FastAPI"
                elif "django" in content.lower():
                    return "Django"
                elif "flask" in content.lower():
                    return "Flask"
        return "Unknown"

    def _detect_js_framework(self, path: Path) -> str:
        """Detect JavaScript framework."""
        pkg_path = path / "package.json"
        if pkg_path.exists():
            import json
            try:
                pkg = json.loads(pkg_path.read_text())
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                if "next" in deps:
                    return "Next.js"
                elif "react" in deps:
                    return "React"
                elif "vue" in deps:
                    return "Vue"
                elif "express" in deps:
                    return "Express"
                elif "svelte" in deps:
                    return "Svelte"
            except Exception:
                pass
        return "Unknown"

    def _analyze_python(self, path: Path, info: dict) -> None:
        """Analyze Python project."""
        for py_file in path.rglob("*.py"):
            if py_file.name.startswith(".") or "__pycache__" in str(py_file):
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content)

                rel_path = str(py_file.relative_to(path))
                info["files"].append(rel_path)

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        if self._include_private or not node.name.startswith("_"):
                            methods = []
                            for item in node.body:
                                if isinstance(item, ast.FunctionDef):
                                    if self._include_private or not item.name.startswith("_"):
                                        methods.append({
                                            "name": item.name,
                                            "args": [arg.arg for arg in item.args.args],
                                            "docstring": ast.get_docstring(item),
                                        })
                            info["classes"].append({
                                "name": node.name,
                                "file": rel_path,
                                "methods": methods,
                                "docstring": ast.get_docstring(node),
                            })

                    elif isinstance(node, ast.FunctionDef):
                        if self._include_private or not node.name.startswith("_"):
                            info["functions"].append({
                                "name": node.name,
                                "file": rel_path,
                                "args": [arg.arg for arg in node.args.args],
                                "docstring": ast.get_docstring(node),
                            })

                    elif isinstance(node, (ast.Import, ast.ImportFrom)):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                info["dependencies"].append(alias.name)
                        else:
                            module = node.module or ""
                            for alias in node.names:
                                info["dependencies"].append(f"{module}.{alias.name}")

            except Exception:
                pass

    def _analyze_javascript(self, path: Path, info: dict) -> None:
        """Analyze JavaScript/TypeScript project."""
        for js_file in path.rglob("*.js"):
            if "node_modules" in str(js_file) or ".git" in str(js_file):
                continue

            try:
                content = js_file.read_text(encoding="utf-8")
                rel_path = str(js_file.relative_to(path))
                info["files"].append(rel_path)

                # Simple regex-based extraction
                class_matches = re.finditer(r'class\s+(\w+)', content)
                for match in class_matches:
                    info["classes"].append({
                        "name": match.group(1),
                        "file": rel_path,
                        "methods": [],
                    })

                function_matches = re.finditer(r'(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>)', content)
                for match in function_matches:
                    name = match.group(1) or match.group(2)
                    if name and (self._include_private or not name.startswith("_")):
                        info["functions"].append({
                            "name": name,
                            "file": rel_path,
                        })

            except Exception:
                pass

    def _generate_readme_content(self, info: dict) -> str:
        """Generate README.md content."""
        lines = [
            f"# {info['name']}",
            "",
        ]

        if info.get("description"):
            lines.append(info["description"])
            lines.append("")

        # Badges
        lines.append("## Badges")
        lines.append(f"![Language](https://img.shields.io/badge/Language-{info['language']}-blue)")
        lines.append(f"![Framework](https://img.shields.io/badge/Framework-{info['framework']}-green)")
        lines.append("")

        # Features
        lines.append("## Features")
        lines.append("- Feature 1")
        lines.append("- Feature 2")
        lines.append("- Feature 3")
        lines.append("")

        # Installation
        lines.append("## Installation")
        lines.append("```bash")
        if info["language"] == "python":
            lines.append("pip install -r requirements.txt")
        elif info["language"] == "javascript":
            lines.append("npm install")
        lines.append("```")
        lines.append("")

        # Usage
        lines.append("## Usage")
        lines.append("```bash")
        if info["language"] == "python":
            lines.append("python main.py")
        elif info["language"] == "javascript":
            lines.append("npm start")
        lines.append("```")
        lines.append("")

        # API Reference
        if info["classes"] or info["functions"]:
            lines.append("## API Reference")
            lines.append("")

            for cls in info["classes"][:10]:
                lines.append(f"### Class: `{cls['name']}`")
                lines.append(f"**File:** `{cls['file']}`")
                if cls.get("docstring"):
                    lines.append(cls["docstring"])
                if cls.get("methods"):
                    lines.append("**Methods:**")
                    for method in cls["methods"][:5]:
                        lines.append(f"- `{method['name']}({', '.join(method['args'])})`")
                        if method.get("docstring"):
                            lines.append(f"  {method['docstring']}")
                lines.append("")

            for func in info["functions"][:10]:
                lines.append(f"### Function: `{func['name']}`")
                lines.append(f"**File:** `{func['file']}`")
                if func.get("docstring"):
                    lines.append(func["docstring"])
                lines.append("")

        # Contributing
        lines.append("## Contributing")
        lines.append("1. Fork the repository")
        lines.append("2. Create a feature branch")
        lines.append("3. Commit your changes")
        lines.append("4. Push to the branch")
        lines.append("5. Open a Pull Request")
        lines.append("")

        # License
        lines.append("## License")
        lines.append("MIT License")
        lines.append("")

        return "\n".join(lines)

    def _generate_api_docs(self, info: dict) -> dict[str, str]:
        """Generate API documentation files."""
        docs = {}

        # Main API index
        lines = [
            "# API Documentation",
            "",
            f"Auto-generated API documentation for {info['name']}.",
            "",
        ]

        if info["classes"]:
            lines.append("## Classes")
            for cls in info["classes"]:
                lines.append(f"- [{cls['name']}]({cls['name'].lower()}.md)")
            lines.append("")

        if info["functions"]:
            lines.append("## Functions")
            for func in info["functions"]:
                lines.append(f"- [{func['name']}](#{func['name'].lower()})")
            lines.append("")

        docs["docs/api/index.md"] = "\n".join(lines)

        # Class documentation
        for cls in info["classes"]:
            lines = [
                f"# {cls['name']}",
                "",
                f"**File:** `{cls['file']}`",
                "",
            ]
            if cls.get("docstring"):
                lines.append(cls["docstring"])
                lines.append("")

            if cls.get("methods"):
                lines.append("## Methods")
                for method in cls["methods"]:
                    lines.append(f"### {method['name']}({', '.join(method['args'])})")
                    if method.get("docstring"):
                        lines.append(method["docstring"])
                    lines.append("")

            docs[f"docs/api/{cls['name'].lower()}.md"] = "\n".join(lines)

        return docs

    def _generate_architecture_docs(self, info: dict) -> str:
        """Generate architecture documentation."""
        lines = [
            "# Architecture Documentation",
            "",
            f"Auto-generated architecture documentation for {info['name']}.",
            "",
            "## Overview",
            "",
            f"This project is written in **{info['language']}** using the **{info['framework']}** framework.",
            "",
            "## Project Structure",
            "",
            "```",
            self._generate_tree(info["files"]),
            "```",
            "",
            "## Modules",
            "",
        ]

        # Group files by directory
        modules = {}
        for f in info["files"]:
            parts = f.split("/")
            if len(parts) > 1:
                module = parts[0]
                if module not in modules:
                    modules[module] = []
                modules[module].append(f)

        for module, files in modules.items():
            lines.append(f"### {module}/")
            for f in files:
                lines.append(f"- `{f}`")
            lines.append("")

        lines.extend([
            "## Dependencies",
            "",
        ])

        unique_deps = sorted(set(info["dependencies"]))
        for dep in unique_deps[:50]:
            lines.append(f"- {dep}")

        if len(unique_deps) > 50:
            lines.append(f"- ... and {len(unique_deps) - 50} more")

        lines.extend([
            "",
            "## Classes",
            "",
        ])

        for cls in info["classes"]:
            lines.append(f"### {cls['name']}")
            lines.append(f"- **File:** `{cls['file']}`")
            if cls.get("methods"):
                lines.append("- **Methods:**")
                for method in cls["methods"]:
                    lines.append(f"  - `{method['name']}({', '.join(method['args'])})`")
            lines.append("")

        return "\n".join(lines)

    def _generate_tree(self, files: list[str]) -> str:
        """Generate a tree representation of files."""
        tree = {}
        for f in files:
            parts = f.split("/")
            node = tree
            for part in parts[:-1]:
                if part not in node:
                    node[part] = {}
                node = node[part]
            if parts[-1]:
                node[parts[-1]] = None

        def render(node: dict, prefix: str = "") -> list[str]:
            lines = []
            items = sorted(node.keys())
            for i, item in enumerate(items):
                is_last = i == len(items) - 1
                connector = "└── " if is_last else "├── "
                lines.append(f"{prefix}{connector}{item}")
                if node[item] is not None:
                    extension = "    " if is_last else "│   "
                    lines.extend(render(node[item], prefix + extension))
            return lines

        return "\n".join(render(tree))