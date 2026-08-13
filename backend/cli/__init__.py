"""Orion Codex CLI - Terminal-first AI coding agent."""

__all__ = ["app", "console"]


def __getattr__(name: str):
    if name in __all__:
        from backend.cli.main import app, console

        return {"app": app, "console": console}[name]
    raise AttributeError(name)
