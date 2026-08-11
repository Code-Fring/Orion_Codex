"""Task API for plugins."""

from typing import Any

from backend.tasks.queue import Task, TaskPriority, TaskStatus, task_queue, task_scheduler


class TaskAPI:
    """API for task operations."""

    def __init__(self, project_id: str) -> None:
        self.project_id = project_id

    def create_task(
        self,
        name: str,
        description: str = "",
        agent_type: str = "",
        priority: TaskPriority = TaskPriority.NORMAL,
        input_data: dict[str, Any] | None = None,
        dependencies: list[str] | None = None,
    ) -> Task:
        """Create a new task."""
        task = Task(
            name=name,
            description=description,
            project_id=self.project_id,
            agent_type=agent_type,
            priority=priority,
            input_data=input_data or {},
            dependencies=dependencies or [],
        )
        return task

    def submit_task(self, task: Task) -> bool:
        """Submit a task for execution."""
        return task_scheduler.submit_task(task)

    def submit_tasks(self, tasks: list[Task]) -> int:
        """Submit multiple tasks."""
        return task_scheduler.submit_tasks(tasks)

    def get_task(self, task_id: str) -> Task | None:
        """Get task by ID."""
        return task_queue.get_task(task_id)

    def get_tasks(self, status: TaskStatus | None = None) -> list[Task]:
        """Get tasks for this project."""
        tasks = task_queue.get_tasks_by_project(self.project_id)
        if status:
            tasks = [t for t in tasks if t.status == status]
        return tasks

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task."""
        return task_queue.cancel_task(task_id)

    def get_queue_stats(self) -> dict[str, Any]:
        """Get queue statistics."""
        return task_queue.get_queue_stats()

    def get_scheduler_status(self) -> dict[str, Any]:
        """Get scheduler status."""
        return task_scheduler.get_status()
