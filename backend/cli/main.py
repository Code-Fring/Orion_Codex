"""Main CLI entry point for Orion Codex."""

import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path


def run_async(coro):
    """Run an async coroutine safely."""
    # Just use asyncio.run - the commands are not async themselves
    return asyncio.run(coro)


import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

# Fix import warning
if __name__ == "__main__":

    sys.modules.pop("backend.cli.main", None)

app = typer.Typer(
    name="orion",
    help="Orion Codex - Terminal-first AI Coding Agent",
    add_completion=False,
    no_args_is_help=False,
)

console = Console()

# Global state
_current_session = {"project_id": None, "workspace": None, "history": []}


class OutputFormat(str, Enum):
    """Output format options."""

    MARKDOWN = "markdown"
    PLAIN = "plain"
    JSON = "json"


# Import new agents and systems
from backend.agents.base import AgentContext
from backend.agents.coder import CodeRefactoringAgent
from backend.agents.git import GitAgent
from backend.agents.security import SecurityAgent, SecurityHardeningAgent
from backend.analysis.dependency_graph import dependency_analyzer
from backend.builder.generator import CodeGenerator

# Import file commands (after app is defined)
from backend.cli.files import app as files_app

# Import TUI
from backend.cli.tui import run_tui
from backend.config.settings import settings
from backend.core.model_manager import AgentRole, model_manager
from backend.core.providers.factory import ProviderFactory
from backend.core.providers.interfaces import ChatMessage
from backend.core.providers.registry import provider_registry
from backend.memory.shared import shared_memory
from backend.memory.store import memory_store
from backend.planner.planner import ProjectPlanner, ProjectType
from backend.validation.build_validator import (
    auto_fixer,
    build_validator,
)

# Add file subcommands
app.add_typer(files_app, name="file")


def get_provider():
    """Get the default chat provider."""
    providers = provider_registry.get_chat_providers()
    if not providers:
        # Try to load from config file first
        _load_providers_from_config()
        providers = provider_registry.get_chat_providers()

    if not providers:
        # Try to initialize from environment
        from backend.config.settings import settings

        provider_configs = {
            "openai": {
                "api_key": settings.OPENAI_API_KEY,
                "base_url": "https://api.openai.com/v1",
            },
            "anthropic": {
                "api_key": settings.ANTHROPIC_API_KEY,
                "base_url": "https://api.anthropic.com",
            },
            "google": {
                "api_key": settings.GOOGLE_API_KEY,
                "base_url": "https://generativelanguage.googleapis.com/v1beta",
            },
            "nvidia": {
                "api_key": settings.NVIDIA_API_KEY,
                "base_url": "https://integrate.api.nvidia.com/v1",
            },
            "deepseek": {
                "api_key": settings.DEEPSEEK_API_KEY,
                "base_url": "https://api.deepseek.com/v1",
            },
            "groq": {
                "api_key": settings.GROQ_API_KEY,
                "base_url": "https://api.groq.com/openai/v1",
            },
            "openrouter": {
                "api_key": settings.OPENROUTER_API_KEY,
                "base_url": "https://openrouter.ai/api/v1",
            },
            "omniroute": {
                "api_key": settings.OMNIROUTE_API_KEY,
                "base_url": "https://api.omniroute.ai/v1",
            },
            "claude_cli": {
                "cli_path": "claude",
                "working_dir": settings.WORKSPACE_ROOT,
            },
        }

        async def init_providers():
            for provider_type, config in provider_configs.items():
                filtered_config = {k: v for k, v in config.items() if v is not None}
                if provider_type == "claude_cli" or filtered_config.get("api_key"):
                    try:
                        await ProviderFactory.create_provider(
                            provider_type, filtered_config, validate=False
                        )
                    except Exception:
                        pass

        run_async(init_providers())
        providers = provider_registry.get_chat_providers()
        if not providers:
            console.print(
                "[red]No AI providers configured. Run 'orion providers --add type:key' to set up.[/red]"
            )
            raise typer.Exit(1)
    return providers[0]


def _get_config_path():
    """Get the provider config file path."""
    return Path.home() / ".orion" / "providers.json"


def _load_providers_from_config():
    """Load provider configurations from file."""
    config_path = _get_config_path()
    if not config_path.exists():
        return

    import json

    try:
        config = json.loads(config_path.read_text())
        for provider_config in config.get("providers", []):
            ptype = provider_config.get("type")
            api_key = provider_config.get("api_key")
            base_url = provider_config.get("base_url")
            if ptype and api_key:
                config_dict = {"api_key": api_key}
                if base_url:
                    config_dict["base_url"] = base_url

                async def load_provider():
                    await ProviderFactory.create_provider(
                        ptype, config_dict, validate=False
                    )

                run_async(load_provider())
    except Exception:
        pass


def _save_providers_to_config():
    """Save provider configurations to file."""
    config_path = _get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    import json

    providers = provider_registry.list_all_providers()
    config = {
        "providers": [
            {
                "type": p.provider_name,
                "api_key": getattr(p, "api_key", ""),
                "base_url": getattr(p, "base_url", ""),
            }
            for p in providers
        ]
    }
    config_path.write_text(json.dumps(config, indent=2))


def print_banner():
    """Print the Orion Codex banner."""
    banner = Text()
    banner.append("Orion Codex", style="bold cyan")
    banner.append(" - Terminal-first AI Coding Agent\n", style="dim")
    banner.append("Autonomous Software Engineering Platform", style="italic green")
    console.print(Panel(banner, border_style="cyan"))


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Show version"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug mode"),
    tui_mode: bool = typer.Option(False, "--tui/--no-tui", help="Launch terminal UI"),
):
    """Orion Codex - Terminal-first AI Coding Agent"""
    if version:
        console.print(f"Orion Codex v{settings.APP_VERSION}")
        raise typer.Exit()

    if debug:
        os.environ["LOG_LEVEL"] = "DEBUG"
        console.print("[yellow]Debug mode enabled[/yellow]")

    if ctx.invoked_subcommand is None:
        if tui_mode:
            # Launch TUI
            try:
                run_tui()
            except KeyboardInterrupt:
                console.print("\n[yellow]TUI closed[/yellow]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                raise typer.Exit(1)
        else:
            print_banner()
            console.print("\nRun 'orion --help' for available commands.\n")
            console.print(
                "[dim]Tip: Use 'orion --tui' to launch the full terminal UI[/dim]\n"
            )


@app.command()
def ask(
    question: str = typer.Argument(..., help="Question to ask the AI"),
    project: str | None = typer.Option(
        None, "--project", "-p", help="Project directory"
    ),
    model: str | None = typer.Option(None, "--model", "-m", help="Model to use"),
    stream: bool = typer.Option(True, "--stream/--no-stream", help="Stream response"),
    context_files: list[str] = typer.Option(
        [], "--context", "-c", help="Files to include as context"
    ),
):
    """Ask the AI a question about your code."""
    print_banner()

    provider = get_provider()

    # Build context from files
    context = ""
    if context_files:
        for file_path in context_files:
            path = Path(file_path)
            if path.exists():
                content = path.read_text(encoding="utf-8")
                context += f"\n--- {file_path} ---\n{content}\n"
            else:
                console.print(f"[yellow]Warning: File not found: {file_path}[/yellow]")

    messages = []
    if context:
        messages.append(ChatMessage(role="system", content=f"Context:\n{context}"))
    messages.append(ChatMessage(role="user", content=question))

    console.print(f"\n[bold cyan]Question:[/bold cyan] {question}\n")
    console.print("[bold green]Answer:[/bold green]\n")

    async def run_query():
        if stream:
            response_text = ""
            async for chunk in provider.chat_stream(
                messages, model or "default", stream=True
            ):
                console.print(chunk, end="")
                response_text += chunk
            console.print()
        else:
            response = await provider.chat(messages, model or "default")
            console.print(response.content)

    run_async(run_query())


@app.command()
def build(
    spec: str = typer.Argument(..., help="Build specification or feature description"),
    project: str | None = typer.Option(
        None, "--project", "-p", help="Project directory"
    ),
    project_type: ProjectType = typer.Option(
        ProjectType.WEB_APP, "--type", "-t", help="Project type"
    ),
    language: str = typer.Option(
        "python", "--language", "-l", help="Programming language"
    ),
    framework: str = typer.Option("fastapi", "--framework", "-f", help="Framework"),
    auto_approve: bool = typer.Option(
        False, "--yes", "-y", help="Auto-approve all actions"
    ),
):
    """Build a new feature or project from specification."""
    print_banner()

    project_path = Path(project) if project else Path.cwd()
    console.print(f"[bold]Building in:[/bold] {project_path}")

    # Initialize planner
    planner = ProjectPlanner()

    # Create analysis from spec
    analysis = {
        "project_type": project_type.value,
        "description": spec,
        "features": [spec],
        "tech_stack_preferences": {
            "language": language,
            "framework": framework,
        },
        "complexity": "moderate",
        "estimated_files": 10,
    }

    console.print("\n[bold cyan]Generating project plan...[/bold cyan]")
    plan = planner.create_plan_from_analysis(analysis)

    # Display plan
    console.print("\n[bold]Project Plan:[/bold]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Component", style="cyan")
    table.add_column("Details")

    table.add_row("Type", plan.project_type.value)
    table.add_row("Language", plan.tech_stack.language)
    table.add_row("Framework", plan.tech_stack.framework)
    table.add_row("Database", plan.tech_stack.database)
    table.add_row("Complexity", plan.complexity.value)
    table.add_row("Est. Files", str(plan.estimated_files))

    console.print(table)

    console.print("\n[bold]Tasks:[/bold]")
    for i, task in enumerate(plan.tasks, 1):
        console.print(
            f"  {i}. [cyan]{task.name}[/cyan] - {task.description} ({task.estimated_duration})"
        )

    if not auto_approve:
        if not Confirm.ask("\nProceed with build?"):
            console.print("[yellow]Build cancelled.[/yellow]")
            raise typer.Exit()

    # Generate code
    console.print("\n[bold cyan]Generating code...[/bold cyan]")
    generator = CodeGenerator(project_path)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Generating project structure...", total=None)
        generator.generate_project_structure(plan.file_structure)
        progress.update(task, description="Done!")

    console.print(f"\n[green]✓ Build complete in {project_path}[/green]")


@app.command()
def fix(
    target: str = typer.Argument(..., help="File or directory to fix"),
    issue: str | None = typer.Option(
        None, "--issue", "-i", help="Specific issue to fix"
    ),
    project: str | None = typer.Option(
        None, "--project", "-p", help="Project directory"
    ),
    auto_approve: bool = typer.Option(False, "--yes", "-y", help="Auto-approve fixes"),
):
    """Fix bugs or issues in code."""
    print_banner()

    project_path = Path(project) if project else Path.cwd()
    target_path = project_path / target

    if not target_path.exists():
        console.print(f"[red]Target not found: {target_path}[/red]")
        raise typer.Exit(1)

    provider = get_provider()

    # Read target files
    files_content = {}
    if target_path.is_file():
        files_content[target] = target_path.read_text(encoding="utf-8")
    else:
        for file_path in target_path.rglob("*"):
            if file_path.is_file() and file_path.suffix in [
                ".py",
                ".js",
                ".ts",
                ".jsx",
                ".tsx",
                ".go",
                ".rs",
                ".java",
            ]:
                rel_path = file_path.relative_to(project_path)
                try:
                    files_content[str(rel_path)] = file_path.read_text(encoding="utf-8")
                except Exception:
                    pass

    if not files_content:
        console.print("[yellow]No code files found to fix.[/yellow]")
        raise typer.Exit()

    console.print(f"[bold]Analyzing {len(files_content)} file(s)...[/bold]")

    # Build fix prompt
    context = "\n\n".join(
        [f"--- {name} ---\n{content}" for name, content in files_content.items()]
    )

    prompt = f"""Analyze the following code and fix any issues.

{f"Specific issue to fix: {issue}" if issue else "Fix any bugs, errors, or issues you find."}

Code:
{context}

Provide the fixed code for each file that needs changes."""

    messages = [
        ChatMessage(
            role="system",
            content="You are an expert software engineer. Fix bugs and issues in the provided code.",
        ),
        ChatMessage(role="user", content=prompt),
    ]

    console.print("\n[bold green]AI Analysis & Fixes:[/bold green]\n")

    async def run_fix():
        response = await provider.chat(messages, temperature=0.2)
        console.print(Markdown(response.content))

    run_async(run_fix())

    if not auto_approve:
        if Confirm.ask("\nApply fixes?"):
            # TODO: Parse response and apply fixes
            console.print(
                "[yellow]Auto-apply not yet implemented. Please apply manually.[/yellow]"
            )


@app.command()
def run(
    command: str = typer.Argument(..., help="Command to run"),
    project: str | None = typer.Option(
        None, "--project", "-p", help="Project directory"
    ),
    watch: bool = typer.Option(
        False, "--watch", "-w", help="Watch for changes and re-run"
    ),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Auto-approve command execution"
    ),
):
    """Run a command in the project."""
    project_path = Path(project) if project else Path.cwd()

    console.print(f"[bold]Running in {project_path}:[/bold] [cyan]{command}[/cyan]\n")

    if not yes:
        if not Confirm.ask("Execute this command?"):
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit()

    import subprocess

    if watch:
        console.print("[yellow]Watch mode not yet implemented.[/yellow]")

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.stdout:
            console.print(result.stdout)
        if result.stderr:
            console.print(f"[red]{result.stderr}[/red]")

        console.print(f"\n[bold]Exit code:[/bold] {result.returncode}")

    except subprocess.TimeoutExpired:
        console.print("[red]Command timed out after 5 minutes[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
        raise typer.Exit(1)


@app.command()
def review(
    target: str = typer.Argument(..., help="File or directory to review"),
    project: str | None = typer.Option(
        None, "--project", "-p", help="Project directory"
    ),
    focus: str | None = typer.Option(
        None, "--focus", "-f", help="Focus area (security, performance, style, etc.)"
    ),
):
    """Review code for quality, security, and best practices."""
    print_banner()

    project_path = Path(project) if project else Path.cwd()
    target_path = project_path / target

    if not target_path.exists():
        console.print(f"[red]Target not found: {target_path}[/red]")
        raise typer.Exit(1)

    provider = get_provider()

    # Read target files
    files_content = {}
    if target_path.is_file():
        files_content[target] = target_path.read_text(encoding="utf-8")
    else:
        for file_path in target_path.rglob("*"):
            if file_path.is_file() and file_path.suffix in [
                ".py",
                ".js",
                ".ts",
                ".jsx",
                ".tsx",
                ".go",
                ".rs",
                ".java",
            ]:
                rel_path = file_path.relative_to(project_path)
                try:
                    files_content[str(rel_path)] = file_path.read_text(encoding="utf-8")
                except Exception:
                    pass

    if not files_content:
        console.print("[yellow]No code files found to review.[/yellow]")
        raise typer.Exit()

    console.print(f"[bold]Reviewing {len(files_content)} file(s)...[/bold]\n")

    context = "\n\n".join(
        [f"--- {name} ---\n{content}" for name, content in files_content.items()]
    )

    focus_prompt = f"\nFocus area: {focus}" if focus else ""

    prompt = f"""Perform a comprehensive code review of the following code.{focus_prompt}

Check for:
- Code quality and best practices
- Security vulnerabilities
- Performance issues
- Maintainability concerns
- Potential bugs
- Test coverage gaps

Code:
{context}

Provide a detailed review with specific suggestions for improvement."""

    messages = [
        ChatMessage(
            role="system",
            content="You are an expert code reviewer. Provide thorough, actionable feedback.",
        ),
        ChatMessage(role="user", content=prompt),
    ]

    console.print("[bold green]Code Review:[/bold green]\n")

    async def run_review():
        response = await provider.chat(messages, temperature=0.3)
        console.print(Markdown(response.content))

    run_async(run_review())


@app.command()
def explain(
    target: str = typer.Argument(..., help="File or code snippet to explain"),
    project: str | None = typer.Option(
        None, "--project", "-p", help="Project directory"
    ),
    detail: str = typer.Option(
        "medium", "--detail", "-d", help="Detail level (brief, medium, deep)"
    ),
):
    """Explain code in natural language."""
    print_banner()

    project_path = Path(project) if project else Path.cwd()
    target_path = project_path / target

    code = ""
    if target_path.exists():
        code = target_path.read_text(encoding="utf-8")
    else:
        code = target  # Treat as inline code

    provider = get_provider()

    detail_prompts = {
        "brief": "Provide a brief, high-level explanation.",
        "medium": "Provide a clear explanation with key concepts and flow.",
        "deep": "Provide a detailed explanation including algorithms, patterns, and implementation details.",
    }

    prompt = f"""Explain the following code:

{code}

{detail_prompts.get(detail, detail_prompts["medium"])}"""

    messages = [
        ChatMessage(
            role="system",
            content="You are an expert software engineer. Explain code clearly and thoroughly.",
        ),
        ChatMessage(role="user", content=prompt),
    ]

    console.print(f"[bold]Explaining:[/bold] {target}\n")

    async def run_explain():
        response = await provider.chat(messages, temperature=0.3)
        console.print(Markdown(response.content))

    run_async(run_explain())


@app.command()
def test(
    target: str | None = typer.Argument(None, help="File or directory to test"),
    project: str | None = typer.Option(
        None, "--project", "-p", help="Project directory"
    ),
    framework: str | None = typer.Option(
        None, "--framework", "-f", help="Test framework"
    ),
    generate: bool = typer.Option(False, "--generate", "-g", help="Generate tests"),
    run_tests: bool = typer.Option(
        True, "--run/--no-run", help="Run tests after generating"
    ),
):
    """Run or generate tests."""
    print_banner()

    project_path = Path(project) if project else Path.cwd()

    if generate and target:
        provider = get_provider()
        target_path = project_path / target

        if not target_path.exists():
            console.print(f"[red]Target not found: {target_path}[/red]")
            raise typer.Exit(1)

        code = target_path.read_text(encoding="utf-8")

        prompt = f"""Generate comprehensive tests for the following code:

{code}

Use {framework or "the appropriate framework for this language"}.
Include unit tests, edge cases, and integration tests where applicable."""

        messages = [
            ChatMessage(
                role="system",
                content="You are an expert test engineer. Generate thorough, well-structured tests.",
            ),
            ChatMessage(role="user", content=prompt),
        ]

        console.print("[bold cyan]Generating tests...[/bold cyan]\n")

        async def run_generate():
            response = await provider.chat(messages, temperature=0.2)
            console.print(Markdown(response.content))

        run_async(run_generate())

    elif run_tests:
        # Run existing tests
        console.print("[bold]Running tests...[/bold]\n")

        import subprocess

        test_commands = {
            "python": "pytest",
            "javascript": "npm test",
            "typescript": "npm test",
            "go": "go test ./...",
            "rust": "cargo test",
        }

        # Detect language
        lang = "python"
        if (project_path / "package.json").exists():
            lang = "javascript"
        elif (project_path / "go.mod").exists():
            lang = "go"
        elif (project_path / "Cargo.toml").exists():
            lang = "rust"

        cmd = test_commands.get(lang, "pytest")

        try:
            result = subprocess.run(
                cmd, shell=True, cwd=project_path, capture_output=True, text=True
            )
            console.print(result.stdout)
            if result.stderr:
                console.print(f"[red]{result.stderr}[/red]")
        except Exception as e:
            console.print(f"[red]Error running tests: {e}[/red]")
    else:
        console.print(
            "[yellow]Specify a target to generate tests, or use --run to run existing tests.[/yellow]"
        )


@app.command()
def doctor(
    project: str | None = typer.Option(
        None, "--project", "-p", help="Project directory"
    ),
    fix: bool = typer.Option(False, "--fix", help="Attempt to fix issues"),
):
    """Check project health and configuration."""
    print_banner()

    project_path = Path(project) if project else Path.cwd()

    # Initialize providers
    get_provider()

    console.print(f"[bold]Doctor check for:[/bold] {project_path}\n")

    issues = []
    warnings = []

    # Check providers
    providers = provider_registry.list_all_providers()
    if providers:
        console.print("[green]✓[/green] AI Providers configured:")
        for p in providers:
            console.print(f"  - {p.provider_name}")
    else:
        issues.append("No AI providers configured")
        console.print("[red]✗[/red] No AI providers configured")

    # Check project structure
    if (project_path / "package.json").exists():
        console.print("[green]✓[/green] Node.js project detected")
    elif (project_path / "requirements.txt").exists() or (
        project_path / "pyproject.toml"
    ).exists():
        console.print("[green]✓[/green] Python project detected")
    elif (project_path / "go.mod").exists():
        console.print("[green]✓[/green] Go project detected")
    elif (project_path / "Cargo.toml").exists():
        console.print("[green]✓[/green] Rust project detected")
    else:
        warnings.append("No recognized project structure")
        console.print("[yellow]![/yellow] No recognized project structure")

    # Check git
    if (project_path / ".git").exists():
        console.print("[green]✓[/green] Git repository initialized")
    else:
        warnings.append("Not a git repository")
        console.print("[yellow]![/yellow] Not a git repository")

    # Check environment
    if (project_path / ".env").exists() or (project_path / ".env.local").exists():
        console.print("[green]✓[/green] Environment file present")
    else:
        warnings.append("No .env file")
        console.print("[yellow]![/yellow] No .env file")

    # Summary
    console.print("\n" + "=" * 50)
    console.print(
        f"[bold]Summary:[/bold] {len(issues)} issues, {len(warnings)} warnings"
    )

    if issues:
        console.print("\n[bold red]Issues to fix:[/bold red]")
        for issue in issues:
            console.print(f"  - {issue}")

    if warnings:
        console.print("\n[bold yellow]Warnings:[/bold yellow]")
        for warning in warnings:
            console.print(f"  - {warning}")

    if not issues and not warnings:
        console.print("\n[green]All checks passed![/green]")


@app.command("continue")
def continue_session(
    project: str | None = typer.Option(
        None, "--project", "-p", help="Project directory"
    ),
    session_id: str | None = typer.Option(
        None, "--session", "-s", help="Session ID to continue"
    ),
):
    """Continue a previous session."""
    print_banner()

    console.print("[bold]Continuing session...[/bold]")
    console.print("[yellow]Session persistence not yet fully implemented.[/yellow]")
    console.print("Use 'orion ask' or other commands to continue working.")


@app.command()
def status(
    project: str | None = typer.Option(
        None, "--project", "-p", help="Project directory"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Show project and system status."""
    print_banner()

    project_path = Path(project) if project else Path.cwd()

    # Load shared memory
    memory = shared_memory.load_memory("default", str(project_path))

    # Get workspace info
    ws_info = {
        "path": str(project_path),
        "name": project_path.name,
        "git_branch": None,
        "git_status": None,
    }

    # Check git
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=project_path,
            capture_output=True,
            text=True,
        )
        ws_info["git_branch"] = (
            result.stdout.strip() if result.returncode == 0 else None
        )
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_path,
            capture_output=True,
            text=True,
        )
        ws_info["git_status"] = (
            len(result.stdout.splitlines()) if result.returncode == 0 else 0
        )
    except Exception:
        pass

    # Get provider info
    provider_info = []
    for p in provider_registry.list_all_providers():
        models = provider_registry.get_cached_models(p.provider_name)
        provider_info.append(
            {
                "name": p.provider_name,
                "type": type(p).__name__,
                "models_count": len(models),
            }
        )

    # Get model assignments
    model_assignments = {}
    for role in AgentRole:
        assignment = model_manager.get_assignment(role)
        if assignment:
            model_assignments[role.value] = {
                "provider": assignment.provider_name,
                "model": assignment.model_id,
                "temperature": assignment.temperature,
            }

    status_data = {
        "workspace": ws_info,
        "project_memory": {
            "project_id": memory.project_id,
            "analysis": memory.analysis is not None,
            "plan": memory.plan is not None,
            "architecture": memory.architecture is not None,
            "generated_files": len(memory.generated_files),
            "test_results": len(memory.test_results),
            "security_findings": len(memory.security_findings),
            "dependencies": len(memory.dependencies),
            "bugs_found": len(memory.bugs_found),
            "git_commits": len(memory.git_commits),
            "deployment_configs": len(memory.deployment_configs),
            "current_tasks": len(memory.current_tasks),
            "completed_tasks": len(memory.completed_tasks),
            "failed_tasks": len(memory.failed_tasks),
        },
        "providers": provider_info,
        "model_assignments": model_assignments,
        "version": settings.APP_VERSION,
    }

    if json_output:
        console.print(json.dumps(status_data, indent=2))
    else:
        console.print(f"\n[bold]Workspace:[/bold] {ws_info['path']}")
        console.print(f"[bold]Git Branch:[/bold] {ws_info['git_branch'] or 'N/A'}")
        console.print(f"[bold]Git Changes:[/bold] {ws_info['git_status'] or 0} files")
        console.print("\n[bold]Project Memory:[/bold]")
        console.print(f"  Analysis: {'✓' if memory.analysis else '✗'}")
        console.print(f"  Plan: {'✓' if memory.plan else '✗'}")
        console.print(f"  Architecture: {'✓' if memory.architecture else '✗'}")
        console.print(f"  Generated Files: {len(memory.generated_files)}")
        console.print(f"  Test Results: {len(memory.test_results)}")
        console.print(f"  Security Findings: {len(memory.security_findings)}")
        console.print(f"  Dependencies: {len(memory.dependencies)}")
        console.print(f"  Bugs Found: {len(memory.bugs_found)}")
        console.print(f"  Git Commits: {len(memory.git_commits)}")
        console.print(f"  Deployment Configs: {len(memory.deployment_configs)}")
        console.print(f"  Current Tasks: {len(memory.current_tasks)}")
        console.print(f"  Completed Tasks: {len(memory.completed_tasks)}")
        console.print(f"  Failed Tasks: {len(memory.failed_tasks)}")
        console.print(f"\n[bold]Providers:[/bold] {len(provider_info)}")
        for p in provider_info:
            console.print(f"  - {p['name']} ({p['type']}) - {p['models_count']} models")
        console.print("\n[bold]Model Assignments:[/bold]")
        for role, assignment in model_assignments.items():
            console.print(f"  {role}: {assignment['provider']}/{assignment['model']}")


@app.command()
def tasks(
    project: str | None = typer.Option(
        None, "--project", "-p", help="Project directory"
    ),
    list_all: bool = typer.Option(True, "--list", "-l", help="List all tasks"),
    add: str | None = typer.Option(None, "--add", "-a", help="Add a task"),
    complete: str | None = typer.Option(
        None, "--complete", "-c", help="Complete a task"
    ),
    fail: str | None = typer.Option(
        None, "--fail", "-f", help="Mark task as failed"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Manage project tasks."""
    print_banner()

    project_path = Path(project) if project else Path.cwd()
    memory = shared_memory.load_memory("default", str(project_path))

    if add:
        task_id = (
            f"task_{len(memory.current_tasks) + 1}_{int(datetime.now().timestamp())}"
        )
        task_info = {"description": add, "created_at": datetime.now().isoformat()}
        shared_memory.add_task("default", task_id, task_info)
        console.print(f"[green]Added task: {task_id}[/green]")
        return

    if complete:
        if shared_memory.complete_task("default", complete):
            console.print(f"[green]Completed task: {complete}[/green]")
        else:
            console.print(f"[red]Task not found: {complete}[/red]")
        return

    if fail:
        if shared_memory.fail_task("default", fail, "Marked as failed by user"):
            console.print(f"[red]Failed task: {fail}[/red]")
        else:
            console.print(f"[red]Task not found: {fail}[/red]")
        return

    if list_all:
        if json_output:
            console.print(
                json.dumps(
                    {
                        "current_tasks": memory.current_tasks,
                        "completed_tasks": memory.completed_tasks,
                        "failed_tasks": memory.failed_tasks,
                    },
                    indent=2,
                )
            )
        else:
            console.print("\n[bold]Current Tasks:[/bold]")
            for task_id, task_info in memory.current_tasks.items():
                console.print(
                    f"  [cyan]{task_id}[/cyan]: {task_info.get('description', 'No description')}"
                )

            console.print(
                f"\n[bold]Completed Tasks:[/bold] ({len(memory.completed_tasks)})"
            )
            for task_id in memory.completed_tasks[-10:]:
                console.print(f"  [green]✓[/green] {task_id}")

            console.print(f"\n[bold]Failed Tasks:[/bold] ({len(memory.failed_tasks)})")
            for task in memory.failed_tasks[-10:]:
                console.print(
                    f"  [red]✗[/red] {task.get('task_id', 'unknown')}: {task.get('error', 'No error')}"
                )


@app.command()
def history(
    project: str | None = typer.Option(
        None, "--project", "-p", help="Project directory"
    ),
    limit: int = typer.Option(50, "--limit", "-n", help="Number of entries to show"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Show session and command history."""
    print_banner()

    project_path = Path(project) if project else Path.cwd()
    memory = shared_memory.load_memory("default", str(project_path))

    # Load conversation history
    conversation = memory_store.load_conversation("default")

    if json_output:
        console.print(json.dumps(conversation[-limit:], indent=2))
    else:
        console.print(f"\n[bold]Conversation History (last {limit}):[/bold]\n")
        for entry in conversation[-limit:]:
            ts = entry.get("timestamp", "")
            role = entry.get("role", "unknown")
            content = entry.get("content", "")[:200]
            mem_type = entry.get("type", "chat")
            style = (
                "cyan"
                if role == "user"
                else "green"
                if role == "assistant"
                else "yellow"
            )
            console.print(
                f"[dim]{ts}[/dim] [bold {style}]{role}[/bold {style}] [{mem_type}]: {content}"
            )


@app.command()
def models(
    list_all: bool = typer.Option(False, "--list", "-l", help="List all models"),
    assign: str | None = typer.Option(
        None, "--assign", "-a", help="Assign model to role (role:provider:model)"
    ),
    show_assignments: bool = typer.Option(
        False, "--show", "-s", help="Show current model assignments"
    ),
    auto_assign: bool = typer.Option(False, "--auto", help="Auto-assign best models"),
):
    """Manage AI models and role assignments."""
    print_banner()

    if show_assignments:
        console.print("\n[bold]Current Model Assignments:[/bold]")
        for role in AgentRole:
            assignment = model_manager.get_assignment(role)
            if assignment:
                console.print(
                    f"  [cyan]{role.value}[/cyan]: {assignment.provider_name}/{assignment.model_id} (temp={assignment.temperature})"
                )
            else:
                console.print(f"  [dim]{role.value}[/dim]: Not assigned")
        return

    if auto_assign:
        console.print("[bold]Auto-assigning best models...[/bold]")
        results = model_manager.auto_assign_best_models()
        for role, success in results.items():
            status = "[green]✓[/green]" if success else "[red]✗[/red]"
            console.print(f"  {status} {role.value}")
        return

    if assign:
        parts = assign.split(":")
        if len(parts) != 3:
            console.print("[red]Format: role:provider:model[/red]")
            raise typer.Exit(1)

        role_str, provider_name, model_id = parts
        try:
            role = AgentRole(role_str)
        except ValueError:
            console.print(f"[red]Invalid role: {role_str}[/red]")
            console.print(f"Valid roles: {[r.value for r in AgentRole]}")
            raise typer.Exit(1)

        if model_manager.assign_model(role, provider_name, model_id):
            console.print(
                f"[green]Assigned {provider_name}/{model_id} to {role.value}[/green]"
            )
        else:
            console.print("[red]Failed to assign model[/red]")
        return

    if list_all:
        _load_providers_from_config()
        providers = provider_registry.get_chat_providers()
        for prov in providers:
            console.print(f"\n[bold]Models for {prov.provider_name}:[/bold]")
            try:
                models_list = run_async(prov.list_models())
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("Model", style="cyan")
                table.add_column("Context Window")
                table.add_column("Max Tokens")
                table.add_column("Capabilities")

                for model in models_list:
                    caps = ", ".join([c.value for c in model.capabilities])
                    table.add_row(
                        model.id, str(model.context_window), str(model.max_tokens), caps
                    )

                console.print(table)
            except Exception as e:
                console.print(f"[red]Error loading models: {e}[/red]")


@app.command()
def build_validate(
    project: str | None = typer.Option(
        None, "--project", "-p", help="Project directory"
    ),
    language: str | None = typer.Option(
        None, "--language", "-l", help="Language (auto-detected if not specified)"
    ),
    fix: bool = typer.Option(False, "--fix", help="Auto-fix issues"),
):
    """Validate project build, lint, and tests."""
    print_banner()

    project_path = Path(project) if project else Path.cwd()
    console.print(f"[bold]Validating project:[/bold] {project_path}")

    if language is None:
        language = build_validator._detect_language(project_path)

    console.print(f"[bold]Language:[/bold] {language}\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Running validation...", total=None)
        report = build_validator.validate(project_path, language)
        progress.update(task, description="Done!")

    console.print("\n[bold]Validation Report:[/bold]")
    console.print(
        f"Overall: {'[green]PASSED[/green]' if report.overall_success else '[red]FAILED[/red]'}"
    )
    console.print(
        f"Steps: {report.summary.get('passed', 0)}/{report.summary.get('total_steps', 0)} passed"
    )
    console.print(f"Duration: {report.summary.get('total_duration_ms', 0)}ms\n")

    for result in report.results:
        status = "[green]✓[/green]" if result.success else "[red]✗[/red]"
        optional = (
            " [dim](optional)[/dim]"
            if result.name in ["security_check", "vulnerability_check"]
            else ""
        )
        console.print(f"  {status} {result.name}{optional} ({result.duration_ms}ms)")
        if not result.success and result.error:
            console.print(f"    [red]{result.error[:200]}[/red]")

    if fix and not report.overall_success:
        console.print("\n[bold]Attempting auto-fix...[/bold]")
        fix_results = auto_fixer.fix(project_path, language)
        console.print(f"Fix results: {fix_results}")

    if not report.overall_success:
        raise typer.Exit(1)


@app.command()
def dependency_graph(
    project: str | None = typer.Option(
        None, "--project", "-p", help="Project directory"
    ),
    file: str | None = typer.Option(
        None, "--file", "-f", help="Analyze impact of changing a file"
    ),
    output: str | None = typer.Option(
        None, "--output", "-o", help="Output file for graph"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Analyze code dependency graph."""
    print_banner()

    project_path = Path(project) if project else Path.cwd()
    console.print(f"[bold]Analyzing dependencies in:[/bold] {project_path}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Building dependency graph...", total=None)
        graph = dependency_analyzer.analyze_workspace(project_path)
        progress.update(task, description="Done!")

    if file:
        # Analyze impact of changing this file
        file_path = str(project_path / file) if not os.path.isabs(file) else file
        impact = graph.find_impact(file_path)

        if json_output:
            console.print(json.dumps(impact, indent=2))
        else:
            console.print(f"\n[bold]Impact Analysis for {file}:[/bold]")
            console.print(f"Risk Level: {impact['risk_level'].upper()}")
            console.print(
                f"Directly Affected Files: {len(impact['directly_affected_files'])}"
            )
            console.print(f"All Affected Files: {len(impact['all_affected_files'])}")

            if impact["directly_affected_files"]:
                console.print("\n[bold]Directly Affected:[/bold]")
                for f in impact["directly_affected_files"][:20]:
                    console.print(f"  - {f}")

            if impact["affected_nodes"]:
                console.print("\n[bold]Affected Nodes:[/bold]")
                for node in impact["affected_nodes"]:
                    console.print(
                        f"  {node['type']}: {node['name']} ({node['dependents_count']} dependents)"
                    )
    else:
        # Show graph summary
        if output:
            dependency_analyzer.save_graph(Path(output))
            console.print(f"[green]Graph saved to {output}[/green]")

        if json_output:
            console.print(json.dumps(graph.to_dict(), indent=2))
        else:
            console.print("\n[bold]Dependency Graph Summary:[/bold]")
            console.print(f"Nodes: {len(graph.nodes)}")
            console.print(f"Edges: {len(graph.edges)}")

            # Count by type
            types = {}
            for node in graph.nodes.values():
                types[node.type] = types.get(node.type, 0) + 1

            for t, count in types.items():
                console.print(f"  {t}: {count}")


@app.command()
def security(
    project: str | None = typer.Option(
        None, "--project", "-p", help="Project directory"
    ),
    scan: bool = typer.Option(False, "--scan", "-s", help="Run security scan"),
    harden: bool = typer.Option(
        False, "--harden", "-h", help="Apply security hardening"
    ),
    deep: bool = typer.Option(False, "--deep", "-d", help="Deep scan with all tools"),
):
    """Security analysis and hardening."""
    print_banner()

    project_path = Path(project) if project else Path.cwd()

    provider = get_provider()
    model_info = model_manager.get_model_for_role(AgentRole.SECURITY)
    if not model_info:
        console.print("[red]No security model assigned[/red]")
        raise typer.Exit(1)

    model_provider, model_id = model_info
    temperature = model_manager.get_temperature_for_role(AgentRole.SECURITY)
    max_tokens = model_manager.get_max_tokens_for_role(AgentRole.SECURITY)

    # Load memory
    memory = shared_memory.load_memory("default", str(project_path))

    if scan or harden:
        # Create security agent
        agent = SecurityAgent()
        context = AgentContext(
            project_id="default",
            workspace_path=str(project_path),
            config={"deep_scan": deep},
            previous_outputs={
                "coder": {"generated_files": memory.generated_files},
                "planner": memory.plan,
            },
        )

        console.print("[bold]Running security analysis...[/bold]")

        async def run_security():
            result = await agent.execute(context)
            return result

        result = run_async(run_security())

        if result.success:
            findings = result.output.get("findings", [])
            report = result.output.get("report", {})

            console.print("\n[bold]Security Scan Complete:[/bold]")
            console.print(f"Findings: {len(findings)}")
            console.print(f"Overall Rating: {report.get('overall_rating', 'N/A')}")

            if findings:
                by_severity = report.get("by_severity", {})
                for sev, count in by_severity.items():
                    if count > 0:
                        color = (
                            "red"
                            if sev in ["critical", "high"]
                            else "yellow"
                            if sev == "medium"
                            else "green"
                        )
                        console.print(f"  [{color}]{sev.upper()}: {count}[/{color}]")

                console.print("\n[bold]Top Findings:[/bold]")
                for finding in findings[:10]:
                    console.print(
                        f"  [{finding.get('severity', 'info').upper()}] {finding.get('file', 'unknown')}:{finding.get('line', 0)} - {finding.get('description', '')[:100]}"
                    )

            if harden:
                console.print("\n[bold]Applying security hardening...[/bold]")
                hardening_agent = SecurityHardeningAgent()
                harden_context = AgentContext(
                    project_id="default",
                    workspace_path=str(project_path),
                    previous_outputs={"security": result.output},
                )

                harden_result = run_async(hardening_agent.execute(harden_context))

                if harden_result.success:
                    console.print(
                        f"[green]Hardened {len(harden_result.output.get('fixed_files', []))} files[/green]"
                    )
                else:
                    console.print(f"[red]Hardening failed: {harden_result.error}[/red]")
        else:
            console.print(f"[red]Security scan failed: {result.error}[/red]")
    else:
        console.print("Use --scan to run security scan, --harden to apply fixes")


@app.command()
def git_cmd(
    action: str = typer.Argument(
        ...,
        help="Git action (status, commit, branch, push, pull, log, diff, stash, tag, auto_commit, changelog)",
    ),
    project: str | None = typer.Option(
        None, "--project", "-p", help="Project directory"
    ),
    message: str | None = typer.Option(
        None, "--message", "-m", help="Commit message"
    ),
    branch: str | None = typer.Option(None, "--branch", "-b", help="Branch name"),
    remote: str | None = typer.Option(
        "origin", "--remote", "-r", help="Remote name"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Force action"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Git operations."""
    print_banner()

    project_path = Path(project) if project else Path.cwd()

    if not (project_path / ".git").exists():
        console.print("[red]Not a git repository[/red]")
        raise typer.Exit(1)

    agent = GitAgent()
    context = AgentContext(
        project_id="default",
        workspace_path=str(project_path),
        config={
            "action": action,
            "message": message,
            "branch_name": branch,
            "remote": remote,
            "force": force,
        },
    )

    console.print(f"[bold]Git {action}...[/bold]")

    async def run_git():
        result = await agent.execute(context)
        return result

    result = run_async(run_git())

    if result.success:
        if json_output:
            console.print(json.dumps(result.output, indent=2))
        else:
            if action == "status":
                out = result.output
                console.print(f"Branch: {out.get('branch', 'unknown')}")
                console.print(
                    f"Ahead: {out.get('ahead', 0)}, Behind: {out.get('behind', 0)}"
                )
                console.print(f"Clean: {out.get('clean', True)}")
                if out.get("files"):
                    console.print("\nFiles:")
                    for f in out["files"]:
                        console.print(f"  {f['status']} {f['path']}")
            elif action == "log":
                for commit in result.output.get("commits", []):
                    console.print(
                        f"  {commit.get('hash', '')[:8]} {commit.get('message', '')}"
                    )
            elif action == "changelog":
                console.print(result.output.get("changelog", ""))
            elif action == "diff":
                console.print(result.output.get("diff", ""))
            else:
                console.print(f"[green]Success[/green]: {result.output}")
    else:
        console.print(f"[red]Failed: {result.error}[/red]")
        if result.output and "conflicts" in result.output:
            console.print("Conflicts:")
            for c in result.output["conflicts"]:
                console.print(f"  {c}")


@app.command()
def refactor(
    target: str = typer.Argument(..., help="File or directory to refactor"),
    instructions: str = typer.Option(
        "", "--instructions", "-i", help="Refactoring instructions"
    ),
    project: str | None = typer.Option(
        None, "--project", "-p", help="Project directory"
    ),
    apply: bool = typer.Option(False, "--apply", "-a", help="Apply refactoring"),
):
    """Refactor code."""
    print_banner()

    project_path = Path(project) if project else Path.cwd()
    target_path = project_path / target

    if not target_path.exists():
        console.print(f"[red]Target not found: {target_path}[/red]")
        raise typer.Exit(1)

    provider = get_provider()
    model_info = model_manager.get_model_for_role(AgentRole.REFACTORING)
    if not model_info:
        console.print("[red]No refactoring model assigned[/red]")
        raise typer.Exit(1)

    model_provider, model_id = model_info
    temperature = model_manager.get_temperature_for_role(AgentRole.REFACTORING)
    max_tokens = model_manager.get_max_tokens_for_role(AgentRole.REFACTORING)

    memory = shared_memory.load_memory("default", str(project_path))

    agent = CodeRefactoringAgent()
    context = AgentContext(
        project_id="default",
        workspace_path=str(project_path),
        config={
            "refactor_instructions": instructions
            or "Improve code quality, reduce complexity, apply best practices"
        },
        previous_outputs={
            "coder": {"generated_files": memory.generated_files},
            "planner": memory.plan,
        },
    )

    if target_path.is_file():
        files = [target_path]
    else:
        files = (
            list(target_path.rglob("*.py"))
            + list(target_path.rglob("*.js"))
            + list(target_path.rglob("*.ts"))
        )

    console.print(f"[bold]Refactoring {len(files)} file(s)...[/bold]")

    for file_path in files:
        console.print(
            f"\n[bold]Processing {file_path.relative_to(project_path)}...[/bold]"
        )

        try:
            source_code = file_path.read_text(encoding="utf-8")

            system_prompt = f"""You are an expert software engineer specializing in code refactoring.
Refactor the following code according to the instructions.

Instructions: {instructions or "Improve code quality, reduce complexity, apply best practices"}

Requirements:
1. Maintain exact same functionality
2. Improve code quality, readability, and maintainability
3. Apply appropriate design patterns
4. Reduce complexity and duplication
5. Improve performance where possible
6. Follow best practices
7. Keep all public APIs compatible
8. Return the COMPLETE refactored file content

Source Code:
{source_code}"""

            messages = [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=f"Refactor {file_path.name}"),
            ]

            response = run_async(
                model_provider.chat(
                    messages=messages,
                    model=model_id,
                    temperature=temperature,
                    max_tokens=max_tokens or 8000,
                )
            )

            if apply:
                file_path.write_text(response.content, encoding="utf-8")
                console.print(
                    f"[green]Applied refactoring to {file_path.relative_to(project_path)}[/green]"
                )
            else:
                console.print("Preview:")
                console.print(
                    response.content[:500] + "..."
                    if len(response.content) > 500
                    else response.content
                )
                if Confirm.ask("Apply this refactoring?"):
                    file_path.write_text(response.content, encoding="utf-8")
                    console.print("[green]Applied[/green]")

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


# Add imports needed for new commands
import datetime
from datetime import datetime


@app.command()
def config(
    show: bool = typer.Option(False, "--show", help="Show current configuration"),
    set_key: str | None = typer.Option(
        None, "--set", help="Set a configuration value (key=value)"
    ),
    get_key: str | None = typer.Option(
        None, "--get", help="Get a configuration value"
    ),
    reset: bool = typer.Option(False, "--reset", help="Reset to defaults"),
):
    """Manage configuration."""
    print_banner()

    config_path = Path.home() / ".orion" / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    import json

    def load_config():
        if config_path.exists():
            return json.loads(config_path.read_text())
        return {}

    def save_config(config):
        config_path.write_text(json.dumps(config, indent=2))

    if show:
        config = load_config()
        console.print(Markdown(f"```json\n{json.dumps(config, indent=2)}\n```"))

    elif set_key:
        if "=" not in set_key:
            console.print("[red]Format: key=value[/red]")
            raise typer.Exit(1)
        key, value = set_key.split("=", 1)
        config = load_config()
        config[key] = value
        save_config(config)
        console.print(f"[green]Set {key} = {value}[/green]")

    elif get_key:
        config = load_config()
        value = config.get(get_key)
        if value is not None:
            console.print(value)
        else:
            console.print(f"[yellow]Key not found: {get_key}[/yellow]")

    elif reset:
        if Confirm.ask("Reset configuration to defaults?"):
            save_config({})
            console.print("[green]Configuration reset[/green]")

    else:
        console.print("Use --show, --set, --get, or --reset")


@app.command()
def providers(
    list: bool = typer.Option(False, "--list", "-l", help="List available providers"),
    add: str | None = typer.Option(
        None, "--add", "-a", help="Add provider (type:api_key)"
    ),
    remove: str | None = typer.Option(
        None, "--remove", "-r", help="Remove provider by name"
    ),
    test: str | None = typer.Option(
        None, "--test", "-t", help="Test provider connection"
    ),
):
    """Manage AI providers."""
    print_banner()

    if list:
        console.print("[bold]Available Provider Types:[/bold]")
        for ptype in ProviderFactory.get_supported_providers():
            console.print(f"  - {ptype}")

        console.print("\n[bold]Registered Providers:[/bold]")
        providers = provider_registry.list_all_providers()
        if providers:
            for p in providers:
                console.print(f"  - {p.provider_name} ({type(p).__name__})")
        else:
            console.print("  None")

    elif add:
        if ":" not in add:
            console.print("[red]Format: type:api_key[/red]")
            raise typer.Exit(1)

        ptype, api_key = add.split(":", 1)

        config = {"api_key": api_key}
        if ptype in [
            "openai",
            "anthropic",
            "google",
            "groq",
            "deepseek",
            "openrouter",
            "mock",
        ]:
            config["base_url"] = {
                "openai": "https://api.openai.com/v1",
                "anthropic": "https://api.anthropic.com",
                "google": "https://generativelanguage.googleapis.com/v1beta",
                "groq": "https://api.groq.com/openai/v1",
                "deepseek": "https://api.deepseek.com/v1",
                "openrouter": "https://openrouter.ai/api/v1",
                "nvidia": "https://integrate.api.nvidia.com/v1",
                "omniroute": "https://api.omniroute.ai/v1",
                "mock": "http://localhost",
            }.get(ptype, "")

        async def add_provider():
            provider = await ProviderFactory.create_provider(
                ptype, config, validate=False
            )
            if provider:
                console.print(
                    f"[green]Added provider: {provider.provider_name}[/green]"
                )
                _save_providers_to_config()
            else:
                console.print(f"[red]Failed to add provider: {ptype}[/red]")

        run_async(add_provider())

        # Refresh list
        providers = provider_registry.list_all_providers()
        if providers:
            console.print("\n[bold]Registered Providers:[/bold]")
            for p in providers:
                console.print(f"  - {p.provider_name} ({type(p).__name__})")

    elif remove:
        provider_registry.unregister_provider(remove)
        console.print(f"[green]Removed provider: {remove}[/green]")

    elif test:
        provider = provider_registry.get_provider(test)
        if not provider:
            console.print(f"[red]Provider not found: {test}[/red]")
            raise typer.Exit(1)

        async def test_provider():
            try:
                await provider.validate_connection()
                console.print(f"[green]Provider {test} connection OK[/green]")
            except Exception as e:
                console.print(f"[red]Provider {test} connection failed: {e}[/red]")

        run_async(test_provider())

    else:
        console.print("Use --list, --add, --remove, or --test")


@app.command()
def models(
    provider: str | None = typer.Option(
        None, "--provider", "-p", help="Provider name"
    ),
    list_all: bool = typer.Option(False, "--list", "-l", help="List all models"),
):
    """List available models."""
    print_banner()

    # Load providers from config
    _load_providers_from_config()

    if provider:
        prov = provider_registry.get_provider(provider)
        if not prov:
            console.print(f"[red]Provider not found: {provider}[/red]")
            raise typer.Exit(1)
        providers = [prov]
    else:
        providers = provider_registry.get_chat_providers()

    if not providers:
        console.print("[yellow]No providers available[/yellow]")
        raise typer.Exit()

    for prov in providers:
        console.print(f"\n[bold]Models for {prov.provider_name}:[/bold]")
        try:
            models_list = run_async(prov.list_models())
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Model", style="cyan")
            table.add_column("Context Window")
            table.add_column("Max Tokens")
            table.add_column("Capabilities")

            for model in models_list:
                caps = ", ".join([c.value for c in model.capabilities])
                table.add_row(
                    model.id, str(model.context_window), str(model.max_tokens), caps
                )

            console.print(table)
        except Exception as e:
            console.print(f"[red]Error loading models: {e}[/red]")


@app.command()
def memory(
    add: str | None = typer.Option(None, "--add", "-a", help="Add memory entry"),
    list_all: bool = typer.Option(False, "--list", "-l", help="List memories"),
    search: str | None = typer.Option(
        None, "--search", "-s", help="Search memories"
    ),
    limit: int = typer.Option(20, "--limit", help="Limit results"),
    project: str | None = typer.Option(None, "--project", "-p", help="Project ID"),
):
    """Manage project memory."""
    print_banner()

    project_id = project or "default"

    if add:
        memory_store.add_to_conversation(
            project_id, {"role": "user", "content": add, "type": "note"}
        )
        console.print("[green]Added to memory[/green]")

    elif search:
        console.print("[yellow]Search not implemented for basic memory store[/yellow]")
        console.print("Use vector_memory for semantic search")

    elif list_all:
        memories = memory_store.load_conversation(project_id)
        if memories:
            for mem in memories[-limit:]:
                ts = mem.get("timestamp", "")
                content = mem.get("content", "")
                mem_type = mem.get("type", "chat")
                console.print(
                    f"[dim]{ts}[/dim] [bold]{mem_type}[/bold]: {content[:200]}"
                )
        else:
            console.print("[yellow]No memories stored[/yellow]")

    else:
        console.print("Use --add, --list, or --search")


@app.command()
def context(
    add: str | None = typer.Option(None, "--add", "-a", help="Add file to context"),
    list_all: bool = typer.Option(False, "--list", "-l", help="List context files"),
    clear: bool = typer.Option(False, "--clear", help="Clear context"),
):
    """Manage context files for AI queries."""
    print_banner()

    import json

    context_file = Path.home() / ".orion" / "context.json"
    context_file.parent.mkdir(parents=True, exist_ok=True)

    def load_context():
        if context_file.exists():
            return json.loads(context_file.read_text())
        return {"files": []}

    def save_context(ctx):
        context_file.write_text(json.dumps(ctx, indent=2))

    ctx = load_context()

    if add:
        path = Path(add).resolve()
        if path.exists():
            if str(path) not in ctx["files"]:
                ctx["files"].append(str(path))
                save_context(ctx)
                console.print(f"[green]Added to context: {path}[/green]")
            else:
                console.print(f"[yellow]Already in context: {path}[/yellow]")
        else:
            console.print(f"[red]File not found: {path}[/red]")

    elif clear:
        ctx["files"] = []
        save_context(ctx)
        console.print("[green]Context cleared[/green]")

    elif list_all or True:
        if ctx["files"]:
            console.print("[bold]Context Files:[/bold]")
            for f in ctx["files"]:
                console.print(f"  - {f}")
        else:
            console.print("[yellow]No context files[/yellow]")


@app.command()
def logs(
    tail: int = typer.Option(100, "--tail", "-n", help="Number of lines to show"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output"),
    level: str = typer.Option("INFO", "--level", help="Log level filter"),
):
    """View application logs."""
    print_banner()

    log_files = [
        Path("error.log"),
        Path("startup.log"),
        Path("backend_startup.log"),
    ]

    for log_file in log_files:
        if log_file.exists():
            console.print(f"\n[bold]=== {log_file.name} ===[/bold]")
            try:
                content = log_file.read_text(encoding="utf-8", errors="replace")
                lines = content.splitlines()
                for line in lines[-tail:]:
                    console.print(line)
            except Exception as e:
                console.print(f"[red]Error reading {log_file}: {e}[/red]")
        else:
            console.print(f"\n[dim]{log_file.name} not found[/dim]")


@app.command()
def update(
    check_only: bool = typer.Option(False, "--check", help="Only check for updates"),
):
    """Update Orion Codex."""
    print_banner()

    console.print("[bold]Checking for updates...[/bold]")
    console.print(f"Current version: {settings.APP_VERSION}")
    console.print("[yellow]Update functionality not yet implemented[/yellow]")
    console.print(
        "Run 'pip install --upgrade orion-codex' or download latest from GitHub"
    )


@app.command()
def chat(
    project: str | None = typer.Option(
        None, "--project", "-p", help="Project directory"
    ),
    model: str | None = typer.Option(None, "--model", "-m", help="Model to use"),
):
    """Start an interactive chat session."""
    print_banner()

    provider = get_provider()

    console.print("[bold]Interactive Chat Session[/bold]")
    console.print("Type 'exit' or 'quit' to end. Type 'clear' to clear history.\n")

    messages = []

    while True:
        try:
            user_input = Prompt.ask("[bold cyan]You[/bold cyan]")

            if user_input.lower() in ["exit", "quit"]:
                break
            elif user_input.lower() == "clear":
                messages = []
                console.print("[yellow]History cleared[/yellow]")
                continue
            elif user_input.lower() == "help":
                console.print("Commands: exit, quit, clear, help")
                continue

            messages.append(ChatMessage(role="user", content=user_input))

            console.print("[bold green]AI:[/bold green]")

            async def chat_stream():
                async for chunk in provider.chat_stream(
                    messages, model or "default", stream=True
                ):
                    console.print(chunk, end="")
                console.print()

            run_async(chat_stream())

            messages.append(ChatMessage(role="assistant", content=""))

        except KeyboardInterrupt:
            break
        except EOFError:
            break

    console.print("\n[yellow]Session ended[/yellow]")


class AutonomousAgent:
    """Autonomous agent that can perform multi-step coding tasks."""

    def __init__(self, provider, project_path: Path, auto_approve: bool = False):
        self.provider = provider
        self.project_path = project_path
        self.auto_approve = auto_approve
        self.messages = []
        self.tools_used = []

    def add_system_prompt(self):
        """Add system prompt with available tools."""
        system_prompt = f"""You are an autonomous coding agent working in the project at {self.project_path}.

You have access to the following tools:
1. READ_FILE(path) - Read a file's contents
2. WRITE_FILE(path, content) - Write content to a file
3. EDIT_FILE(path, old_text, new_text) - Replace text in a file
4. LIST_DIR(path) - List directory contents
5. RUN_COMMAND(command) - Execute a shell command
6. GLOB(pattern) - Find files matching a pattern
7. GREP(pattern, path) - Search for text in files

IMPORTANT: You MUST use tools to complete tasks. Do not just answer directly.

When you need to use a tool, respond with ONLY a JSON object (no other text):
{{
    "tool": "TOOL_NAME",
    "args": {{"arg1": "value1", "arg2": "value2"}}
}}

Example: To list Python files, use:
{{
    "tool": "GLOB",
    "args": {{"pattern": "**/*.py"}}
}}

After each tool call, you'll receive the result. Continue using tools until the task is complete, then provide your final answer.

Current working directory: {self.project_path}
"""
        self.messages.append(ChatMessage(role="system", content=system_prompt))

    async def execute_task(self, task: str, model: str = "mock-model") -> str:
        """Execute a multi-step task autonomously."""
        self.messages.append(ChatMessage(role="user", content=task))

        max_iterations = 20
        for iteration in range(max_iterations):
            console.print(f"\n[dim]Iteration {iteration + 1}/{max_iterations}[/dim]")

            # Get AI response
            response = await self.provider.chat(
                self.messages, model=model, temperature=0.3
            )
            content = response.content

            # Check for tool calls
            tool_calls = self._parse_tool_calls(content)

            if not tool_calls:
                # No tool calls, task is complete
                self.messages.append(ChatMessage(role="assistant", content=content))
                return content

            # Execute tool calls
            for tool_call in tool_calls:
                tool_name = tool_call.get("tool")
                args = tool_call.get("args", {})

                console.print(f"[bold cyan]Tool:[/bold cyan] {tool_name}({args})")

                result = await self._execute_tool(tool_name, args)

                console.print(f"[dim]Result:[/dim] {result[:200]}...")

                # Add tool result to messages
                self.messages.append(
                    ChatMessage(
                        role="user", content=f"Tool result for {tool_name}:\n{result}"
                    )
                )

        return "Max iterations reached. Task may be incomplete."

    def _parse_tool_calls(self, content: str) -> list:
        """Parse tool calls from AI response."""
        import json
        import re

        tool_calls = []

        # Find JSON objects that look like tool calls
        json_pattern = r'\{[^{]*"tool"[^{}]*\}'
        matches = re.findall(json_pattern, content)

        for match in matches:
            try:
                tool_call = json.loads(match)
                if "tool" in tool_call and "args" in tool_call:
                    tool_calls.append(tool_call)
            except json.JSONDecodeError:
                pass

        return tool_calls

    async def _execute_tool(self, tool_name: str, args: dict) -> str:
        """Execute a tool and return the result."""
        try:
            if tool_name == "READ_FILE":
                path = self.project_path / args.get("path", "")
                if not path.exists():
                    return f"Error: File not found: {path}"
                return path.read_text(encoding="utf-8")

            elif tool_name == "WRITE_FILE":
                path = self.project_path / args.get("path", "")
                content = args.get("content", "")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                return f"Written to {path}"

            elif tool_name == "EDIT_FILE":
                path = self.project_path / args.get("path", "")
                old_text = args.get("old_text", "")
                new_text = args.get("new_text", "")
                if not path.exists():
                    return f"Error: File not found: {path}"
                content = path.read_text(encoding="utf-8")
                if old_text not in content:
                    return "Error: Text not found in file"
                new_content = content.replace(old_text, new_text, 1)
                path.write_text(new_content, encoding="utf-8")
                return f"Edited {path}"

            elif tool_name == "LIST_DIR":
                path = self.project_path / args.get("path", ".")
                if not path.exists():
                    return f"Error: Directory not found: {path}"
                items = []
                for item in path.iterdir():
                    items.append(f"{'DIR' if item.is_dir() else 'FILE'} {item.name}")
                return "\n".join(items)

            elif tool_name == "RUN_COMMAND":
                command = args.get("command", "")
                if not self.auto_approve:
                    if not Confirm.ask(f"Run command: {command}?"):
                        return "Command cancelled by user"
                import subprocess

                result = subprocess.run(
                    command,
                    shell=True,
                    cwd=self.project_path,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                output = f"Exit code: {result.returncode}\n"
                if result.stdout:
                    output += f"STDOUT:\n{result.stdout}\n"
                if result.stderr:
                    output += f"STDERR:\n{result.stderr}\n"
                return output

            elif tool_name == "GLOB":
                pattern = args.get("pattern", "**/*")
                path = self.project_path / args.get("path", ".")
                matches = list(path.rglob(pattern))
                return "\n".join(
                    [str(m.relative_to(self.project_path)) for m in matches]
                )

            elif tool_name == "GREP":
                pattern = args.get("pattern", "")
                path = self.project_path / args.get("path", ".")
                import re

                regex = re.compile(pattern)
                matches = []
                for file_path in path.rglob("*"):
                    if file_path.is_file():
                        try:
                            content = file_path.read_text(encoding="utf-8")
                            for i, line in enumerate(content.splitlines(), 1):
                                if regex.search(line):
                                    matches.append(
                                        f"{file_path.relative_to(self.project_path)}:{i}:{line}"
                                    )
                        except Exception:
                            pass
                return "\n".join(matches[:50])

            else:
                return f"Error: Unknown tool: {tool_name}"

        except Exception as e:
            return f"Error executing {tool_name}: {e}"


@app.command()
def agent(
    task: str = typer.Argument(..., help="Task for the autonomous agent"),
    project: str | None = typer.Option(
        None, "--project", "-p", help="Project directory"
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Auto-approve all actions"),
    model: str | None = typer.Option(None, "--model", "-m", help="Model to use"),
):
    """Run an autonomous agent to complete a multi-step coding task."""
    print_banner()

    project_path = Path(project) if project else Path.cwd()
    console.print(f"[bold]Project:[/bold] {project_path}")
    console.print(f"[bold]Task:[/bold] {task}\n")

    provider = get_provider()

    agent = AutonomousAgent(provider, project_path, auto_approve=yes)
    agent.add_system_prompt()

    console.print("[bold cyan]Starting autonomous agent...[/bold cyan]\n")

    async def run_agent():
        result = await agent.execute_task(task, model=model or "mock-model")
        console.print("\n[bold green]Result:[/bold green]\n")
        console.print(Markdown(result))

    run_async(run_agent())


@app.command()
def tui(
    project: str | None = typer.Option(
        None, "--project", "-p", help="Project directory"
    ),
):
    """Launch the full terminal UI."""
    if project:
        os.chdir(project)

    print_banner()
    console.print("[bold]Launching Terminal UI...[/bold]\n")

    try:
        run_tui()
    except KeyboardInterrupt:
        console.print("\n[yellow]TUI closed[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()


# Plugin commands
@app.command()
def plugin(
    install: str | None = typer.Option(
        None, "--install", "-i", help="Install plugin from path or URL"
    ),
    uninstall: str | None = typer.Option(
        None, "--uninstall", "-u", help="Uninstall plugin by name"
    ),
    enable: str | None = typer.Option(
        None, "--enable", "-e", help="Enable a plugin"
    ),
    disable: str | None = typer.Option(
        None, "--disable", "-d", help="Disable a plugin"
    ),
    reload: str | None = typer.Option(
        None, "--reload", "-r", help="Reload a plugin"
    ),
    update: str | None = typer.Option(
        None, "--update", help="Update a plugin"
    ),
    list_all: bool = typer.Option(False, "--list", "-l", help="List all plugins"),
    search: str | None = typer.Option(
        None, "--search", "-s", help="Search for plugins"
    ),
    info: str | None = typer.Option(
        None, "--info", help="Show plugin details"
    ),
):
    """Manage plugins."""
    print_banner()

    from backend.plugins.sdk.manager import plugin_manager
    from backend.plugins.sdk.manifest import PluginType

    if list_all:
        plugins = plugin_manager.list_plugins()
        if plugins:
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Name", style="cyan")
            table.add_column("Version")
            table.add_column("Type")
            table.add_column("Status")
            table.add_column("Description")

            for p in plugins:
                status = "[green]Enabled[/green]" if p["enabled"] else "[dim]Disabled[/dim]"
                table.add_row(
                    p["name"],
                    p["version"],
                    p["type"],
                    status,
                    p["description"][:50] + "..." if len(p["description"]) > 50 else p["description"],
                )
            console.print(table)
        else:
            console.print("[yellow]No plugins installed[/yellow]")

    elif install:
        console.print(f"[bold]Installing plugin from: {install}[/bold]")
        result = run_async(plugin_manager.install_plugin(install))
        if result.success:
            console.print(f"[green]{result.message}[/green]")
        else:
            console.print(f"[red]{result.message}[/red]")

    elif uninstall:
        console.print(f"[bold]Uninstalling plugin: {uninstall}[/bold]")
        success = run_async(plugin_manager.uninstall_plugin(uninstall))
        if success:
            console.print(f"[green]Plugin uninstalled: {uninstall}[/green]")
        else:
            console.print(f"[red]Failed to uninstall: {uninstall}[/red]")

    elif enable:
        console.print(f"[bold]Enabling plugin: {enable}[/bold]")
        success = run_async(plugin_manager.enable_plugin(enable))
        if success:
            console.print(f"[green]Plugin enabled: {enable}[/green]")
        else:
            console.print(f"[red]Failed to enable: {enable}[/red]")

    elif disable:
        console.print(f"[bold]Disabling plugin: {disable}[/bold]")
        success = run_async(plugin_manager.disable_plugin(disable))
        if success:
            console.print(f"[green]Plugin disabled: {disable}[/green]")
        else:
            console.print(f"[red]Failed to disable: {disable}[/red]")

    elif reload:
        console.print(f"[bold]Reloading plugin: {reload}[/bold]")
        success = run_async(plugin_manager.reload_plugin(reload))
        if success:
            console.print(f"[green]Plugin reloaded: {reload}[/green]")
        else:
            console.print(f"[red]Failed to reload: {reload}[/red]")

    elif update:
        console.print(f"[bold]Updating plugin: {update}[/bold]")
        console.print("[yellow]Update from source not yet implemented[/yellow]")

    elif search:
        console.print(f"[bold]Searching for: {search}[/bold]")
        console.print("[yellow]Plugin marketplace search not yet implemented[/yellow]")

    elif info:
        plugin = plugin_manager.get_plugin(info)
        if plugin:
            console.print(f"[bold]Name:[/bold] {plugin.manifest.name}")
            console.print(f"[bold]Version:[/bold] {plugin.manifest.version}")
            console.print(f"[bold]Author:[/bold] {plugin.manifest.author}")
            console.print(f"[bold]Type:[/bold] {plugin.manifest.plugin_type.value}")
            console.print(f"[bold]Description:[/bold] {plugin.manifest.description}")
            console.print(f"[bold]License:[/bold] {plugin.manifest.license}")
            console.print(f"[bold]Homepage:[/bold] {plugin.manifest.homepage}")
            console.print(f"[bold]Repository:[/bold] {plugin.manifest.repository}")
            console.print(f"[bold]Entry Point:[/bold] {plugin.manifest.entry_point}")
            console.print(f"[bold]Min Orion Version:[/bold] {plugin.manifest.min_orion_version}")
            console.print(f"[bold]Dependencies:[/bold] {[d.name for d in plugin.manifest.dependencies]}")
            console.print(f"[bold]Permissions:[/bold] {[p.value for p in plugin.manifest.permissions]}")
            console.print(f"[bold]Status:[/bold] {'Enabled' if plugin.enabled else 'Disabled'}")
        else:
            console.print(f"[red]Plugin not found: {info}[/red]")

    else:
        console.print("Use --list, --install, --uninstall, --enable, --disable, --reload, --update, --search, --info, --watch, or --unwatch")


@app.command()
def plugin_watch(
    plugin: str = typer.Argument(..., help="Plugin name to watch"),
    stop: bool = typer.Option(False, "--stop", help="Stop watching"),
):
    """Watch a plugin for changes and auto-reload (hot reload)."""
    print_banner()

    from backend.plugins.sdk.hotreload import hot_reload_manager

    if stop:
        console.print(f"[bold]Stopping hot reload for: {plugin}[/bold]")
        hot_reload_manager.stop_watching(plugin)
        console.print("[green]Stopped watching[/green]")
    else:
        console.print(f"[bold]Starting hot reload for: {plugin}[/bold]")
        success = hot_reload_manager.start_watching(plugin)
        if success:
            console.print("[green]Now watching for changes. Press Ctrl+C to stop.[/green]")
            console.print("[dim]Edit plugin files to trigger auto-reload[/dim]")
            try:
                import asyncio
                asyncio.get_event_loop().run_forever()
            except KeyboardInterrupt:
                hot_reload_manager.stop_watching(plugin)
                console.print("\n[yellow]Stopped watching[/yellow]")
        else:
            console.print("[red]Failed to start watching[/red]")
