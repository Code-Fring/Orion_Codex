"""API routes for tasks and generation logs."""

from uuid import UUID

from backend.core.auth.jwt import get_user_id_from_token
from backend.database.connection import get_db_session
from backend.models.models import GenerationLog, Project, Task, TaskStatus
from backend.tasks.queue import Task as QueueTask
from backend.tasks.queue import TaskPriority, task_queue, task_scheduler
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    description: str | None
    status: TaskStatus
    step_order: int
    agent_type: str | None
    input_data: dict
    output_data: dict | None
    error_message: str | None
    started_at: str | None
    completed_at: str | None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class TaskCreate(BaseModel):
    project_id: UUID
    name: str
    description: str | None = None
    agent_type: str
    step_order: int
    input_data: dict = {}
    dependencies: list[UUID] = []


async def get_current_user_id(authorization: str = Depends(lambda x: x)) -> UUID:
    """Get current user ID from token."""
    token = (
        authorization.replace("Bearer ", "")
        if authorization.startswith("Bearer ")
        else authorization
    )
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return UUID(user_id)


@router.get("/project/{project_id}", response_model=list[TaskResponse])
async def list_project_tasks(
    project_id: UUID,
    status: TaskStatus | None = None,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """List tasks for a project."""
    from sqlalchemy import select

    # Verify project ownership
    project_result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user_id)
    )
    if not project_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    query = select(Task).where(Task.project_id == project_id)
    if status:
        query = query.where(Task.status == status)

    query = query.order_by(Task.step_order)
    result = await db.execute(query)
    tasks = result.scalars().all()

    return [
        TaskResponse(
            id=t.id,
            project_id=t.project_id,
            name=t.name,
            description=t.description,
            status=t.status,
            step_order=t.step_order,
            agent_type=t.agent_type,
            input_data=t.input_data,
            output_data=t.output_data,
            error_message=t.error_message,
            started_at=t.started_at.isoformat() if t.started_at else None,
            completed_at=t.completed_at.isoformat() if t.completed_at else None,
            created_at=t.created_at.isoformat(),
            updated_at=t.updated_at.isoformat(),
        )
        for t in tasks
    ]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """Get a specific task."""
    from sqlalchemy import select

    result = await db.execute(
        select(Task)
        .join(Project)
        .where(Task.id == task_id, Project.owner_id == user_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskResponse(
        id=task.id,
        project_id=task.project_id,
        name=task.name,
        description=task.description,
        status=task.status,
        step_order=task.step_order,
        agent_type=task.agent_type,
        input_data=task.input_data,
        output_data=task.output_data,
        error_message=task.error_message,
        started_at=task.started_at.isoformat() if task.started_at else None,
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
        created_at=task.created_at.isoformat(),
        updated_at=task.updated_at.isoformat(),
    )


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """Create a new task."""
    from sqlalchemy import select

    # Verify project ownership
    project_result = await db.execute(
        select(Project).where(
            Project.id == task_data.project_id, Project.owner_id == user_id
        )
    )
    if not project_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    task = Task(
        project_id=task_data.project_id,
        name=task_data.name,
        description=task_data.description,
        agent_type=task_data.agent_type,
        step_order=task_data.step_order,
        input_data=task_data.input_data,
        status=TaskStatus.PENDING,
    )

    db.add(task)
    await db.commit()
    await db.refresh(task)

    return TaskResponse(
        id=task.id,
        project_id=task.project_id,
        name=task.name,
        description=task.description,
        status=task.status,
        step_order=task.step_order,
        agent_type=task.agent_type,
        input_data=task.input_data,
        output_data=task.output_data,
        error_message=task.error_message,
        started_at=task.started_at.isoformat() if task.started_at else None,
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
        created_at=task.created_at.isoformat(),
        updated_at=task.updated_at.isoformat(),
    )


@router.get("/queue/stats")
async def get_queue_stats(
    user_id: UUID = Depends(get_current_user_id),
):
    """Get task queue statistics."""
    return task_queue.get_queue_stats()


# Generation Logs
class LogResponse(BaseModel):
    id: UUID
    project_id: UUID
    level: str
    message: str
    context: dict | None
    created_at: str

    class Config:
        from_attributes = True


@router.get("/project/{project_id}/logs", response_model=list[LogResponse])
async def get_project_logs(
    project_id: UUID,
    level: str | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """Get generation logs for a project."""
    from sqlalchemy import select

    # Verify project ownership
    project_result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user_id)
    )
    if not project_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    query = select(GenerationLog).where(GenerationLog.project_id == project_id)
    if level:
        query = query.where(GenerationLog.level == level.upper())

    query = query.order_by(GenerationLog.created_at.desc()).limit(limit)
    result = await db.execute(query)
    logs = result.scalars().all()

    return [
        LogResponse(
            id=log.id,
            project_id=log.project_id,
            level=log.level,
            message=log.message,
            context=log.context,
            created_at=log.created_at.isoformat(),
        )
        for log in logs
    ]


# Task Queue and Scheduler endpoints
@router.get("/queue/stats")
async def get_queue_stats(
    user_id: UUID = Depends(get_current_user_id),
):
    """Get task queue statistics."""
    return task_queue.get_queue_stats()


@router.get("/scheduler/status")
async def get_scheduler_status(
    user_id: UUID = Depends(get_current_user_id),
):
    """Get scheduler status."""
    return task_scheduler.get_status()


@router.post("/scheduler/start")
async def start_scheduler(
    user_id: UUID = Depends(get_current_user_id),
):
    """Start the task scheduler."""
    await task_scheduler.start()
    return {"status": "started", "workers": task_scheduler.worker_count}


@router.post("/scheduler/stop")
async def stop_scheduler(
    user_id: UUID = Depends(get_current_user_id),
):
    """Stop the task scheduler."""
    await task_scheduler.stop()
    return {"status": "stopped"}


@router.post("/{task_id}/retry", response_model=TaskResponse)
async def retry_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """Retry a failed task."""
    from sqlalchemy import select

    result = await db.execute(
        select(Task)
        .join(Project)
        .where(Task.id == task_id, Project.owner_id == user_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != TaskStatus.FAILED:
        raise HTTPException(status_code=400, detail="Only failed tasks can be retried")

    # Reset task status
    task.status = TaskStatus.PENDING
    task.error_message = None
    task.started_at = None
    task.completed_at = None
    task.retries = 0

    await db.commit()
    await db.refresh(task)

    # Re-queue the task
    from backend.tasks.queue import task_queue

    queue_task = QueueTask(
        id=str(task.id),
        name=task.name,
        description=task.description or "",
        project_id=str(task.project_id),
        agent_type=task.agent_type or "",
        priority=TaskPriority.NORMAL,
        input_data=task.input_data,
        max_retries=3,
    )

    task_queue.enqueue(queue_task)

    return TaskResponse(
        id=task.id,
        project_id=task.project_id,
        name=task.name,
        description=task.description,
        status=task.status,
        step_order=task.step_order,
        agent_type=task.agent_type,
        input_data=task.input_data,
        output_data=task.output_data,
        error_message=task.error_message,
        started_at=task.started_at.isoformat() if task.started_at else None,
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
        created_at=task.created_at.isoformat(),
        updated_at=task.updated_at.isoformat(),
    )
