"""Hooks package for Orion Codex."""

from backend.hooks.manager import (
    HookContext,
    HookManager,
    HookPoint,
    HookRegistration,
    hook_manager,
    register_hook,
    run_after_hooks,
    run_before_hooks,
    run_hooks,
    unregister_hook,
)

__all__ = [
    "HookContext",
    "HookManager",
    "HookPoint",
    "HookRegistration",
    "hook_manager",
    "register_hook",
    "run_after_hooks",
    "run_before_hooks",
    "run_hooks",
    "unregister_hook",
]
