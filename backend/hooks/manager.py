"""Hook system for Orion Codex."""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class HookPoint(Enum):
    """Core hook points."""
    # Build hooks
    BEFORE_BUILD = "before_build"
    AFTER_BUILD = "after_build"

    # Edit hooks
    BEFORE_EDIT = "before_edit"
    AFTER_EDIT = "after_edit"

    # Merge hooks
    BEFORE_MERGE = "before_merge"
    AFTER_MERGE = "after_merge"

    # Agent hooks
    BEFORE_AGENT_EXECUTION = "before_agent_execution"
    AFTER_AGENT_EXECUTION = "after_agent_execution"

    # Plugin hooks
    BEFORE_PLUGIN_LOAD = "before_plugin_load"
    AFTER_PLUGIN_LOAD = "after_plugin_load"
    BEFORE_PLUGIN_UNLOAD = "before_plugin_unload"
    AFTER_PLUGIN_UNLOAD = "after_plugin_unload"

    # Command hooks
    BEFORE_COMMAND = "before_command"
    AFTER_COMMAND = "after_command"

    # Task hooks
    BEFORE_TASK_START = "before_task_start"
    AFTER_TASK_COMPLETE = "after_task_complete"

    # File hooks
    BEFORE_FILE_WRITE = "before_file_write"
    AFTER_FILE_WRITE = "after_file_write"
    BEFORE_FILE_DELETE = "before_file_delete"
    AFTER_FILE_DELETE = "after_file_delete"

    # Git hooks
    BEFORE_COMMIT = "before_commit"
    AFTER_COMMIT = "after_commit"
    BEFORE_PUSH = "before_push"
    AFTER_PUSH = "after_push"

    # Provider hooks
    BEFORE_PROVIDER_CALL = "before_provider_call"
    AFTER_PROVIDER_CALL = "after_provider_call"


@dataclass
class HookContext:
    """Context passed to hooks."""
    hook_point: HookPoint
    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    cancel: bool = False
    cancel_reason: str | None = None


@dataclass
class HookRegistration:
    """Hook registration."""
    hook_point: HookPoint
    handler: Callable[[HookContext], Any]
    priority: int = 0
    plugin_name: str | None = None


class HookManager:
    """Manages hook registration and execution."""

    def __init__(self) -> None:
        self._hooks: dict[HookPoint, list[HookRegistration]] = {
            point: [] for point in HookPoint
        }
        self._global_before_hooks: list[Callable[[HookContext], Any]] = []
        self._global_after_hooks: list[Callable[[HookContext], Any]] = []

    def register_hook(
        self,
        hook_point: HookPoint,
        handler: Callable[[HookContext], Any],
        priority: int = 0,
        plugin_name: str | None = None,
    ) -> HookRegistration:
        """Register a hook handler."""
        registration = HookRegistration(
            hook_point=hook_point,
            handler=handler,
            priority=priority,
            plugin_name=plugin_name,
        )
        self._hooks[hook_point].append(registration)
        # Sort by priority (higher priority runs first)
        self._hooks[hook_point].sort(key=lambda h: -h.priority)
        return registration

    def unregister_hook(self, registration: HookRegistration) -> bool:
        """Unregister a hook handler."""
        if registration in self._hooks[registration.hook_point]:
            self._hooks[registration.hook_point].remove(registration)
            return True
        return False

    def unregister_plugin_hooks(self, plugin_name: str) -> int:
        """Unregister all hooks for a plugin."""
        count = 0
        for hook_point in HookPoint:
            to_remove = [h for h in self._hooks[hook_point] if h.plugin_name == plugin_name]
            for h in to_remove:
                self._hooks[hook_point].remove(h)
                count += 1
        return count

    async def execute_before_hooks(self, hook_point: HookPoint, context: HookContext) -> HookContext:
        """Execute all before hooks for a hook point."""
        # Execute global before hooks
        for hook in self._global_before_hooks:
            try:
                result = hook(context)
                if asyncio.iscoroutine(result):
                    result = await result
                if context.cancel:
                    break
            except Exception as e:
                logger.error(f"Error in global before hook: {e}")

        # Execute hook point specific before hooks
        for registration in self._hooks[hook_point]:
            try:
                result = registration.handler(context)
                if asyncio.iscoroutine(result):
                    result = await result
                if context.cancel:
                    break
            except Exception as e:
                logger.error(f"Error in hook {hook_point.value} from {registration.plugin_name}: {e}")

        return context

    async def execute_after_hooks(self, hook_point: HookPoint, context: HookContext) -> HookContext:
        """Execute all after hooks for a hook point."""
        # Execute hook point specific after hooks
        for registration in self._hooks[hook_point]:
            try:
                result = registration.handler(context)
                if asyncio.iscoroutine(result):
                    result = await result
            except Exception as e:
                logger.error(f"Error in after hook {hook_point.value} from {registration.plugin_name}: {e}")

        # Execute global after hooks
        for hook in self._global_after_hooks:
            try:
                result = hook(context)
                if asyncio.iscoroutine(result):
                    result = await result
            except Exception as e:
                logger.error(f"Error in global after hook: {e}")

        return context

    def add_global_before_hook(self, handler: Callable[[HookContext], Any]) -> None:
        """Add a global before hook."""
        self._global_before_hooks.append(handler)

    def add_global_after_hook(self, handler: Callable[[HookContext], Any]) -> None:
        """Add a global after hook."""
        self._global_after_hooks.append(handler)

    def get_hooks_for_point(self, hook_point: HookPoint) -> list[HookRegistration]:
        """Get all hooks for a hook point."""
        return self._hooks[hook_point].copy()


# Global hook manager
hook_manager = HookManager()


# Convenience functions
async def run_before_hooks(
    hook_point: HookPoint,
    data: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> HookContext:
    """Run before hooks for a hook point."""
    context = HookContext(
        hook_point=hook_point,
        data=data or {},
        metadata=metadata or {},
    )
    return await hook_manager.execute_before_hooks(hook_point, context)


async def run_after_hooks(
    hook_point: HookPoint,
    data: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> HookContext:
    """Run after hooks for a hook point."""
    context = HookContext(
        hook_point=hook_point,
        data=data or {},
        metadata=metadata or {},
    )
    return await hook_manager.execute_after_hooks(hook_point, context)


async def run_hooks(
    hook_point: HookPoint,
    data: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> HookContext:
    """Run both before and after hooks."""
    context = await run_before_hooks(hook_point, data, metadata)
    if not context.cancel:
        context = await run_after_hooks(hook_point, data, metadata)
    return context


def register_hook(
    hook_point: HookPoint,
    handler: Callable[[HookContext], Any],
    priority: int = 0,
    plugin_name: str | None = None,
) -> HookRegistration:
    """Register a hook."""
    return hook_manager.register_hook(hook_point, handler, priority, plugin_name)


def unregister_hook(registration: HookRegistration) -> bool:
    """Unregister a hook."""
    return hook_manager.unregister_hook(registration)
