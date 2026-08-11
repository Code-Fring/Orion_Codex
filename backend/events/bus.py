"""Event system for Orion Codex."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable
from uuid import uuid4

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Core event types."""
    # Project events
    PROJECT_OPENED = "project.opened"
    PROJECT_CLOSED = "project.closed"
    PROJECT_CREATED = "project.created"
    PROJECT_DELETED = "project.deleted"

    # File events
    FILE_CREATED = "file.created"
    FILE_MODIFIED = "file.modified"
    FILE_DELETED = "file.deleted"
    FILE_RENAMED = "file.renamed"

    # Build events
    BUILD_STARTED = "build.started"
    BUILD_FINISHED = "build.finished"
    BUILD_FAILED = "build.failed"

    # Test events
    TEST_STARTED = "test.started"
    TEST_FINISHED = "test.finished"
    TEST_FAILED = "test.failed"

    # Task events
    TASK_ASSIGNED = "task.assigned"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"

    # Agent events
    AGENT_STARTED = "agent.started"
    AGENT_STOPPED = "agent.stopped"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"

    # Plugin events
    PLUGIN_LOADED = "plugin.loaded"
    PLUGIN_UNLOADED = "plugin.unloaded"
    PLUGIN_ENABLED = "plugin.enabled"
    PLUGIN_DISABLED = "plugin.disabled"
    PLUGIN_ERROR = "plugin.error"

    # Provider events
    PROVIDER_CHANGED = "provider.changed"
    PROVIDER_ADDED = "provider.added"
    PROVIDER_REMOVED = "provider.removed"

    # Model events
    MODEL_CHANGED = "model.changed"
    MODEL_ASSIGNED = "model.assigned"

    # Git events
    GIT_COMMIT = "git.commit"
    GIT_PUSH = "git.push"
    GIT_PULL = "git.pull"
    GIT_MERGE = "git.merge"
    GIT_BRANCH_CREATED = "git.branch.created"
    GIT_BRANCH_DELETED = "git.branch.deleted"

    # Terminal events
    TERMINAL_COMMAND = "terminal.command"
    TERMINAL_OUTPUT = "terminal.output"

    # Diagnostics events
    DIAGNOSTICS_UPDATED = "diagnostics.updated"
    LINT_STARTED = "lint.started"
    LINT_FINISHED = "lint.finished"

    # Custom event prefix
    CUSTOM = "custom."


@dataclass
class Event:
    """Event data structure."""
    type: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str | None = None
    correlation_id: str | None = None
    event_id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "correlation_id": self.correlation_id,
            "event_id": self.event_id,
        }

    @classmethod
    def create(cls, event_type: str | EventType, data: dict[str, Any] | None = None, source: str | None = None, correlation_id: str | None = None) -> "Event":
        if isinstance(event_type, EventType):
            event_type = event_type.value
        return cls(
            type=event_type,
            data=data or {},
            source=source,
            correlation_id=correlation_id,
        )


class EventSubscription:
    """Event subscription."""

    def __init__(
        self,
        event_type: str,
        handler: Callable[[Event], Any],
        filter_fn: Callable[[Event], bool] | None = None,
        once: bool = False,
    ) -> None:
        self.event_type = event_type
        self.handler = handler
        self.filter_fn = filter_fn
        self.once = once
        self.active = True


class EventBus:
    """Event bus for publishing and subscribing to events."""

    def __init__(self) -> None:
        self._subscriptions: dict[str, list[EventSubscription]] = {}
        self._wildcard_subscriptions: list[EventSubscription] = []
        self._event_history: list[Event] = []
        self._max_history = 1000
        self._running = False

    def subscribe(
        self,
        event_type: str,
        handler: Callable[[Event], Any],
        filter_fn: Callable[[Event], bool] | None = None,
        once: bool = False,
    ) -> EventSubscription:
        """Subscribe to an event type."""
        subscription = EventSubscription(event_type, handler, filter_fn, once)

        if event_type == "*" or event_type.endswith(".*"):
            self._wildcard_subscriptions.append(subscription)
        else:
            if event_type not in self._subscriptions:
                self._subscriptions[event_type] = []
            self._subscriptions[event_type].append(subscription)

        return subscription

    def unsubscribe(self, subscription: EventSubscription) -> bool:
        """Unsubscribe from events."""
        subscription.active = False

        if subscription.event_type == "*" or subscription.event_type.endswith(".*"):
            if subscription in self._wildcard_subscriptions:
                self._wildcard_subscriptions.remove(subscription)
                return True
        else:
            if subscription.event_type in self._subscriptions:
                if subscription in self._subscriptions[subscription.event_type]:
                    self._subscriptions[subscription.event_type].remove(subscription)
                    return True

        return False

    async def publish(self, event: Event) -> int:
        """Publish an event to all subscribers."""
        if not self._running:
            return 0

        # Add to history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        handlers_called = 0

        # Call specific subscriptions
        subscriptions = self._subscriptions.get(event.type, []).copy()
        for sub in subscriptions:
            if not sub.active:
                continue
            if sub.filter_fn and not sub.filter_fn(event):
                continue

            try:
                await sub.handler(event)
                handlers_called += 1
                if sub.once:
                    self.unsubscribe(sub)
            except Exception as e:
                logger.error(f"Error in event handler for {event.type}: {e}")

        # Call wildcard subscriptions
        for sub in self._wildcard_subscriptions.copy():
            if not sub.active:
                continue
            if sub.filter_fn and not sub.filter_fn(event):
                continue

            # Check if wildcard matches
            if sub.event_type == "*" or event.type.startswith(sub.event_type[:-1]):
                try:
                    await sub.handler(event)
                    handlers_called += 1
                    if sub.once:
                        self.unsubscribe(sub)
                except Exception as e:
                    logger.error(f"Error in wildcard event handler: {e}")

        return handlers_called

    async def publish_sync(self, event: Event) -> int:
        """Publish event synchronously (for non-async handlers)."""
        if not self._running:
            return 0

        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        handlers_called = 0

        subscriptions = self._subscriptions.get(event.type, []).copy()
        for sub in subscriptions:
            if not sub.active:
                continue
            if sub.filter_fn and not sub.filter_fn(event):
                continue

            try:
                if asyncio.iscoroutinefunction(sub.handler):
                    await sub.handler(event)
                else:
                    sub.handler(event)
                handlers_called += 1
                if sub.once:
                    self.unsubscribe(sub)
            except Exception as e:
                logger.error(f"Error in event handler for {event.type}: {e}")

        for sub in self._wildcard_subscriptions.copy():
            if not sub.active:
                continue
            if sub.filter_fn and not sub.filter_fn(event):
                continue

            if sub.event_type == "*" or event.type.startswith(sub.event_type[:-1]):
                try:
                    if asyncio.iscoroutinefunction(sub.handler):
                        await sub.handler(event)
                    else:
                        sub.handler(event)
                    handlers_called += 1
                    if sub.once:
                        self.unsubscribe(sub)
                except Exception as e:
                    logger.error(f"Error in wildcard event handler: {e}")

        return handlers_called

    def get_history(self, event_type: str | None = None, limit: int = 100) -> list[Event]:
        """Get event history."""
        if event_type:
            return [e for e in self._event_history if e.type == event_type][-limit:]
        return self._event_history[-limit:]

    def clear_history(self) -> None:
        """Clear event history."""
        self._event_history.clear()

    def start(self) -> None:
        """Start the event bus."""
        self._running = True

    def stop(self) -> None:
        """Stop the event bus."""
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running


# Global event bus
event_bus = EventBus()


# Convenience functions
async def publish_event(event_type: str | EventType, data: dict[str, Any] | None = None, source: str | None = None, correlation_id: str | None = None) -> int:
    """Publish an event."""
    event = Event.create(event_type, data, source, correlation_id)
    return await event_bus.publish(event)


def subscribe_to_event(event_type: str, handler: Callable[[Event], Any], filter_fn: Callable[[Event], bool] | None = None, once: bool = False) -> EventSubscription:
    """Subscribe to an event."""
    return event_bus.subscribe(event_type, handler, filter_fn, once)


def unsubscribe_from_event(subscription: EventSubscription) -> bool:
    """Unsubscribe from an event."""
    return event_bus.unsubscribe(subscription)


def start_event_bus() -> None:
    """Start the global event bus."""
    event_bus.start()


def stop_event_bus() -> None:
    """Stop the global event bus."""
    event_bus.stop()