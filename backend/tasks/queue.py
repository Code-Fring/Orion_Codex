"""Task queue and scheduler for managing generation tasks."""

import asyncio
import logging
import uuid
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from backend.api.websocket import broadcast_log, broadcast_task_update

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels."""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class TaskStatus(Enum):
    """Task execution status."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Task representation."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    project_id: str = ""
    agent_type: str = ""
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    input_data: dict[str, Any] = field(default_factory=dict)
    output_data: dict[str, Any] | None = None
    error: str | None = None
    dependencies: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    retries: int = 0
    max_retries: int = 3
    timeout: int = 300  # seconds


class TaskQueue:
    """Priority-based task queue."""

    def __init__(self, max_size: int = 1000) -> None:
        self.max_size = max_size
        self._queues: dict[TaskPriority, deque] = {
            TaskPriority.CRITICAL: deque(),
            TaskPriority.HIGH: deque(),
            TaskPriority.NORMAL: deque(),
            TaskPriority.LOW: deque(),
        }
        self._tasks: dict[str, Task] = {}
        self._running: dict[str, Task] = {}
        self._completed: dict[str, Task] = {}
        self._failed: dict[str, Task] = {}

    def enqueue(self, task: Task) -> bool:
        """Add a task to the queue."""
        if len(self._tasks) >= self.max_size:
            logger.warning(f"Queue full, rejecting task {task.id}")
            return False

        if task.id in self._tasks:
            logger.warning(f"Task already exists: {task.id}")
            return False

        self._tasks[task.id] = task
        self._queues[task.priority].append(task.id)
        task.status = TaskStatus.QUEUED
        logger.info(
            f"Enqueued task: {task.id} ({task.name}) with priority {task.priority.name}"
        )
        return True

    def dequeue(self) -> Task | None:
        """Get the next highest priority task."""
        for priority in [
            TaskPriority.CRITICAL,
            TaskPriority.HIGH,
            TaskPriority.NORMAL,
            TaskPriority.LOW,
        ]:
            queue = self._queues[priority]
            while queue:
                task_id = queue.popleft()
                task = self._tasks.get(task_id)
                if task and task.status == TaskStatus.QUEUED:
                    # Check dependencies
                    if self._dependencies_met(task):
                        return task
                    else:
                        # Re-queue at the end
                        queue.append(task_id)

        return None

    def _dependencies_met(self, task: Task) -> bool:
        """Check if all task dependencies are completed."""
        for dep_id in task.dependencies:
            dep_task = self._tasks.get(dep_id)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False
        return True

    def start_task(self, task: Task) -> None:
        """Mark task as running."""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        self._running[task.id] = task
        logger.info(f"Started task: {task.id}")

        # Broadcast task start
        asyncio.create_task(
            broadcast_task_update(
                task.project_id,
                {
                    "id": task.id,
                    "name": task.name,
                    "status": task.status.value,
                    "started_at": task.started_at.isoformat()
                    if task.started_at
                    else None,
                },
            )
        )

    def complete_task(
        self, task: Task, output: dict[str, Any] | None = None
    ) -> None:
        """Mark task as completed."""
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()
        task.output_data = output
        self._running.pop(task.id, None)
        self._completed[task.id] = task
        logger.info(f"Completed task: {task.id}")

        # Broadcast task completion
        asyncio.create_task(
            broadcast_task_update(
                task.project_id,
                {
                    "id": task.id,
                    "name": task.name,
                    "status": task.status.value,
                    "output_data": output,
                    "completed_at": task.completed_at.isoformat()
                    if task.completed_at
                    else None,
                },
            )
        )

    def fail_task(self, task: Task, error: str) -> bool:
        """Mark task as failed, handle retries."""
        task.error = error
        task.retries += 1

        if task.retries < task.max_retries:
            # Re-queue for retry
            task.status = TaskStatus.QUEUED
            self._queues[task.priority].append(task.id)
            logger.warning(
                f"Task failed, retrying ({task.retries}/{task.max_retries}): {task.id} - {error}"
            )
            return True
        else:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.utcnow()
            self._running.pop(task.id, None)
            self._failed[task.id] = task
            logger.error(f"Task failed permanently: {task.id} - {error}")

            # Broadcast task failure
            asyncio.create_task(
                broadcast_task_update(
                    task.project_id,
                    {
                        "id": task.id,
                        "name": task.name,
                        "status": task.status.value,
                        "error_message": error,
                        "completed_at": task.completed_at.isoformat()
                        if task.completed_at
                        else None,
                    },
                )
            )
            return False

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task."""
        task = self._tasks.get(task_id)
        if not task:
            return False

        if task.status in (
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        ):
            return False

        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.utcnow()

        # Remove from queues
        for queue in self._queues.values():
            if task_id in queue:
                queue.remove(task_id)

        self._running.pop(task_id, None)
        logger.info(f"Cancelled task: {task_id}")
        return True

    def get_task(self, task_id: str) -> Task | None:
        """Get task by ID."""
        return self._tasks.get(task_id)

    def get_tasks_by_project(self, project_id: str) -> list[Task]:
        """Get all tasks for a project."""
        return [t for t in self._tasks.values() if t.project_id == project_id]

    def get_tasks_by_status(self, status: TaskStatus) -> list[Task]:
        """Get all tasks with a specific status."""
        return [t for t in self._tasks.values() if t.status == status]

    def get_queue_stats(self) -> dict[str, Any]:
        """Get queue statistics."""
        return {
            "total_tasks": len(self._tasks),
            "queued": sum(len(q) for q in self._queues.values()),
            "running": len(self._running),
            "completed": len(self._completed),
            "failed": len(self._failed),
            "by_priority": {p.name: len(q) for p, q in self._queues.items()},
        }


class TaskScheduler:
    """Schedules and executes tasks with worker pools."""

    def __init__(
        self,
        queue: TaskQueue,
        worker_count: int = 4,
        task_handler: Callable[[Task], Awaitable[dict[str, Any]]] | None = None,
    ) -> None:
        self.queue = queue
        self.worker_count = worker_count
        self.task_handler = task_handler
        self._workers: list[asyncio.Task] = []
        self._running = False
        self._shutdown_event = asyncio.Event()

    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            return

        self._running = True
        self._shutdown_event.clear()

        for i in range(self.worker_count):
            worker = asyncio.create_task(self._worker_loop(i))
            self._workers.append(worker)

        logger.info(f"Started scheduler with {self.worker_count} workers")

    async def stop(self) -> None:
        """Stop the scheduler."""
        if not self._running:
            return

        self._running = False
        self._shutdown_event.set()

        # Wait for workers to finish
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)

        self._workers.clear()
        logger.info("Stopped scheduler")

    async def _worker_loop(self, worker_id: int) -> None:
        """Worker loop for processing tasks."""
        logger.info(f"Worker {worker_id} started")

        while self._running:
            try:
                # Wait for shutdown or task
                task = self.queue.dequeue()

                if task:
                    await self._execute_task(task)
                else:
                    # No tasks available, wait a bit
                    try:
                        await asyncio.wait_for(self._shutdown_event.wait(), timeout=1.0)
                    except asyncio.TimeoutError:
                        pass
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(1)

        logger.info(f"Worker {worker_id} stopped")

    async def _execute_task(self, task: Task) -> None:
        """Execute a single task."""
        self.queue.start_task(task)

        try:
            if self.task_handler:
                # Execute with timeout
                output = await asyncio.wait_for(
                    self.task_handler(task),
                    timeout=task.timeout,
                )
                self.queue.complete_task(task, output)
            else:
                # No handler, just mark complete
                self.queue.complete_task(task, {"message": "No handler configured"})
        except asyncio.TimeoutError:
            self.queue.fail_task(task, f"Task timed out after {task.timeout}s")
        except Exception as e:
            self.queue.fail_task(task, str(e))

    def submit_task(self, task: Task) -> bool:
        """Submit a task for execution."""
        return self.queue.enqueue(task)

    def submit_tasks(self, tasks: list[Task]) -> int:
        """Submit multiple tasks."""
        count = 0
        for task in tasks:
            if self.queue.enqueue(task):
                count += 1
        return count

    def get_status(self) -> dict[str, Any]:
        """Get scheduler status."""
        return {
            "running": self._running,
            "workers": len(self._workers),
            "queue_stats": self.queue.get_queue_stats(),
        }


# Global task queue and scheduler
task_queue = TaskQueue()
task_scheduler = TaskScheduler(task_queue)


# Convenience function for agents to log messages
async def log_message(
    project_id: str, level: str, message: str, context: dict[str, Any] | None = None
):
    """Log a message and broadcast to WebSocket clients."""
    log_data = {
        "project_id": project_id,
        "level": level.upper(),
        "message": message,
        "context": context or {},
        "created_at": datetime.utcnow().isoformat(),
    }
    await broadcast_log(project_id, log_data)
    return log_data


# Convenience function for agents to broadcast progress
async def broadcast_progress(project_id: str, progress: int, status: str):
    """Broadcast progress update to WebSocket clients."""
    from backend.api.websocket import ws_manager

    await ws_manager.broadcast_progress(project_id, progress, status)
