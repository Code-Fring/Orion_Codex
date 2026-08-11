"""File operations for the CLI."""

from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Confirm
from rich.syntax import Syntax
from rich.table import Table

# Create local console to avoid circular import
console = Console()
app = typer.Typer(name="file", help="File operations")


@app.command()
def ls(
    path: str = typer.Argument(".", help="Directory to list"),
    all: bool = typer.Option(False, "--all", "-a", help="Show hidden files"),
    long: bool = typer.Option(False, "--long", "-l", help="Long format"),
):
    """List files in a directory."""
    target = Path(path).resolve()

    if not target.exists():
        console.print(f"[red]Path not found: {target}[/red]")
        raise typer.Exit(1)

    if not target.is_dir():
        console.print(f"[red]Not a directory: {target}[/red]")
        raise typer.Exit(1)

    files = []
    for item in target.iterdir():
        if not all and item.name.startswith("."):
            continue
        files.append(item)

    files.sort(key=lambda x: (not x.is_dir(), x.name.lower()))

    if long:
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Permissions")
        table.add_column("Size")
        table.add_column("Modified")
        table.add_column("Name")

        for item in files:
            stat = item.stat()
            perms = oct(stat.st_mode)[-3:]
            size = str(stat.st_size) if item.is_file() else "-"
            import datetime

            modified = datetime.datetime.fromtimestamp(stat.st_mtime).strftime(
                "%Y-%m-%d %H:%M"
            )
            name = item.name + ("/" if item.is_dir() else "")
            style = "cyan" if item.is_dir() else "white"
            table.add_row(perms, size, modified, f"[{style}]{name}[/{style}]")

        console.print(table)
    else:
        for item in files:
            name = item.name + ("/" if item.is_dir() else "")
            style = "cyan" if item.is_dir() else "white"
            console.print(f"[{style}]{name}[/{style}]")


@app.command()
def cat(
    file: str = typer.Argument(..., help="File to display"),
    line_numbers: bool = typer.Option(
        False, "--line-numbers", "-n", help="Show line numbers"
    ),
    syntax: bool = typer.Option(
        True, "--syntax/--no-syntax", help="Syntax highlighting"
    ),
):
    """Display file contents."""
    path = Path(file).resolve()

    if not path.exists():
        console.print(f"[red]File not found: {path}[/red]")
        raise typer.Exit(1)

    if not path.is_file():
        console.print(f"[red]Not a file: {path}[/red]")
        raise typer.Exit(1)

    content = path.read_text(encoding="utf-8")

    if syntax:
        ext = path.suffix.lstrip(".")
        console.print(Syntax(content, ext or "text", line_numbers=line_numbers))
    else:
        if line_numbers:
            for i, line in enumerate(content.splitlines(), 1):
                console.print(f"{i:4}: {line}")
        else:
            console.print(content)


@app.command()
def write(
    file: str = typer.Argument(..., help="File to write"),
    content: str = typer.Option(
        None, "--content", "-c", help="Content to write (or use stdin)"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite without confirmation"
    ),
):
    """Write content to a file."""
    path = Path(file).resolve()

    if path.exists() and not force:
        if not Confirm.ask(f"File {path} exists. Overwrite?"):
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit()

    if content is None:
        console.print("[yellow]Enter content (Ctrl+D to finish):[/yellow]")
        import sys

        content = sys.stdin.read()

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    console.print(f"[green]Written to {path}[/green]")


@app.command()
def edit(
    file: str = typer.Argument(..., help="File to edit"),
    old: str = typer.Argument(..., help="Text to replace"),
    new: str = typer.Argument(..., help="New text"),
    all: bool = typer.Option(False, "--all", "-a", help="Replace all occurrences"),
):
    """Edit a file by replacing text."""
    path = Path(file).resolve()

    if not path.exists():
        console.print(f"[red]File not found: {path}[/red]")
        raise typer.Exit(1)

    content = path.read_text(encoding="utf-8")

    if all:
        new_content = content.replace(old, new)
        count = content.count(old)
    else:
        new_content = content.replace(old, new, 1)
        count = 1 if old in content else 0

    if count == 0:
        console.print(f"[yellow]Text not found: {old}[/yellow]")
        raise typer.Exit()

    path.write_text(new_content, encoding="utf-8")
    console.print(f"[green]Replaced {count} occurrence(s) in {path}[/green]")


@app.command()
def find(
    pattern: str = typer.Argument(..., help="Glob pattern to search"),
    path: str = typer.Option(".", "--path", "-p", help="Directory to search"),
    type: str = typer.Option(None, "--type", "-t", help="File type (file, dir)"),
):
    """Find files matching a pattern."""
    target = Path(path).resolve()

    if not target.exists():
        console.print(f"[red]Path not found: {target}[/red]")
        raise typer.Exit(1)

    matches = list(target.rglob(pattern))

    if type == "file":
        matches = [m for m in matches if m.is_file()]
    elif type == "dir":
        matches = [m for m in matches if m.is_dir()]

    for match in matches:
        rel = match.relative_to(target)
        style = "cyan" if match.is_dir() else "white"
        console.print(f"[{style}]{rel}[/{style}]")

    console.print(f"\n[dim]{len(matches)} match(es)[/dim]")


@app.command()
def grep(
    pattern: str = typer.Argument(..., help="Regex pattern to search"),
    path: str = typer.Option(".", "--path", "-p", help="Directory to search"),
    include: str = typer.Option("*", "--include", "-i", help="File pattern to include"),
    line_numbers: bool = typer.Option(
        True, "--line-numbers/--no-line-numbers", "-n", help="Show line numbers"
    ),
):
    """Search for pattern in files."""
    import re

    target = Path(path).resolve()

    if not target.exists():
        console.print(f"[red]Path not found: {target}[/red]")
        raise typer.Exit(1)

    regex = re.compile(pattern)
    matches = []

    for file_path in target.rglob(include):
        if not file_path.is_file():
            continue
        try:
            content = file_path.read_text(encoding="utf-8")
            for i, line in enumerate(content.splitlines(), 1):
                if regex.search(line):
                    matches.append((file_path, i, line))
        except Exception:
            pass

    for file_path, line_num, line in matches:
        rel = file_path.relative_to(target)
        console.print(f"[cyan]{rel}[/cyan]:{line_num}: {line}")

    console.print(f"\n[dim]{len(matches)} match(es)[/dim]")
