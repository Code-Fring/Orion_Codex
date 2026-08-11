"""API routes for projects."""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.data.database import db_manager
from src.data.models import Project, ProjectStatus

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    prompt: str = Field(..., min_length=1)
    tech_stack_preferences: dict = Field(default_factory=dict)


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    status: ProjectStatus | None = None


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    prompt: str
    status: ProjectStatus
    tech_stack: dict
    architecture: dict | None
    generated_path: str | None
    error_message: str | None
    progress: int
    created_at: str
    updated_at: str
    completed_at: str | None

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]
    total: int


async def get_db() -> AsyncSession:
    """Get database session."""
    async with db_manager.session() as session:
        yield session


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Create a new project."""
    project = Project(
        name=project_data.name,
        description=project_data.description,
        prompt=project_data.prompt,
        tech_stack=project_data.tech_stack_preferences,
        status=ProjectStatus.PENDING,
    )

    db.add(project)
    await db.commit()
    await db.refresh(project)

    # Start generation pipeline in background
    background_tasks.add_task(
        run_generation_pipeline, str(project.id), project_data.prompt
    )

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        prompt=project.prompt,
        status=project.status,
        tech_stack=project.tech_stack,
        architecture=project.architecture,
        generated_path=project.generated_path,
        error_message=project.error_message,
        progress=project.progress,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
        completed_at=project.completed_at.isoformat() if project.completed_at else None,
    )


@router.get("/", response_model=ProjectListResponse)
async def list_projects(
    skip: int = 0,
    limit: int = 20,
    status: ProjectStatus | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List projects."""
    query = select(Project)
    if status:
        query = query.where(Project.status == status)

    total_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(total_query)

    query = query.offset(skip).limit(limit).order_by(Project.created_at.desc())
    result = await db.execute(query)
    projects = result.scalars().all()

    return ProjectListResponse(
        projects=[
            ProjectResponse(
                id=p.id,
                name=p.name,
                description=p.description,
                prompt=p.prompt,
                status=p.status,
                tech_stack=p.tech_stack,
                architecture=p.architecture,
                generated_path=p.generated_path,
                error_message=p.error_message,
                progress=p.progress,
                created_at=p.created_at.isoformat(),
                updated_at=p.updated_at.isoformat(),
                completed_at=p.completed_at.isoformat() if p.completed_at else None,
            )
            for p in projects
        ],
        total=total,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific project."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        prompt=project.prompt,
        status=project.status,
        tech_stack=project.tech_stack,
        architecture=project.architecture,
        generated_path=project.generated_path,
        error_message=project.error_message,
        progress=project.progress,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
        completed_at=project.completed_at.isoformat() if project.completed_at else None,
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    project_data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a project."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project_data.name is not None:
        project.name = project_data.name
    if project_data.description is not None:
        project.description = project_data.description
    if project_data.status is not None:
        project.status = project_data.status

    await db.commit()
    await db.refresh(project)

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        prompt=project.prompt,
        status=project.status,
        tech_stack=project.tech_stack,
        architecture=project.architecture,
        generated_path=project.generated_path,
        error_message=project.error_message,
        progress=project.progress,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
        completed_at=project.completed_at.isoformat() if project.completed_at else None,
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a project."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.delete(project)
    await db.commit()


@router.post("/{project_id}/regenerate", response_model=ProjectResponse)
async def regenerate_project(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Regenerate a project."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Reset project status
    project.status = ProjectStatus.PENDING
    project.progress = 0
    project.error_message = None
    project.generated_path = None
    project.completed_at = None

    await db.commit()

    # Start generation pipeline
    background_tasks.add_task(run_generation_pipeline, str(project.id), project.prompt)

    await db.refresh(project)

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        prompt=project.prompt,
        status=project.status,
        tech_stack=project.tech_stack,
        architecture=project.architecture,
        generated_path=project.generated_path,
        error_message=project.error_message,
        progress=project.progress,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
        completed_at=project.completed_at.isoformat() if project.completed_at else None,
    )


async def run_generation_pipeline(project_id: str, prompt: str) -> None:
    """Run the full generation pipeline for a project."""
    from datetime import datetime

    from src.data.models import Project, ProjectStatus

    async with db_manager.session() as db:
        # Get project
        result = await db.execute(select(Project).where(Project.id == UUID(project_id)))
        project = result.scalar_one_or_none()
        if not project:
            return

        # Update status to planning
        project.status = ProjectStatus.PLANNING
        project.progress = 10
        await db.commit()

        # TODO: Execute pipeline using agents
        # This is where the agent pipeline would run

        # For now, mark as completed
        project.status = ProjectStatus.COMPLETED
        project.progress = 100
        project.completed_at = datetime.utcnow()
        await db.commit()
