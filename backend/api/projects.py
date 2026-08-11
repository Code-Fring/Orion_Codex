"""API routes for projects."""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.base import AgentContext
from backend.core.auth.jwt import get_user_id_from_token
from backend.database.connection import get_db_session
from backend.models.models import Project, ProjectStatus
from backend.router.router import task_router
from backend.workspace.manager import workspace_manager

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


async def get_current_user_id(authorization: str = Header(None)) -> UUID:
    """Get current user ID from token."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # In real implementation, extract from JWT
    # For now, return a placeholder
    token = (
        authorization.replace("Bearer ", "")
        if authorization.startswith("Bearer ")
        else authorization
    )
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return UUID(user_id)


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """Create a new project."""
    project = Project(
        owner_id=user_id,
        name=project_data.name,
        description=project_data.description,
        prompt=project_data.prompt,
        tech_stack=project_data.tech_stack_preferences,
        status=ProjectStatus.PENDING,
    )

    db.add(project)
    await db.commit()
    await db.refresh(project)

    # Create workspace
    workspace_manager.create_workspace(str(project.id), project.name)

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
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """List projects for the current user."""
    from sqlalchemy import func, select

    query = select(Project).where(Project.owner_id == user_id)
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
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """Get a specific project."""
    from sqlalchemy import select

    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user_id)
    )
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
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """Update a project."""
    from sqlalchemy import select

    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user_id)
    )
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
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """Delete a project."""
    from sqlalchemy import select

    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Delete workspace
    workspace_manager.delete_workspace(str(project_id))

    await db.delete(project)
    await db.commit()


@router.post("/{project_id}/regenerate", response_model=ProjectResponse)
async def regenerate_project(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """Regenerate a project."""
    from sqlalchemy import select

    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user_id)
    )
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

    from backend.database.connection import db_manager
    from backend.models.models import Project, ProjectStatus

    async with db_manager.session() as db:
        # Get project
        result = await db.execute(select(Project).where(Project.id == UUID(project_id)))
        project = result.scalar_one_or_none()
        if not project:
            return

        # Create workspace context
        workspace_path = workspace_manager.get_workspace(project_id)
        if not workspace_path:
            workspace_path = workspace_manager.create_workspace(
                project_id, project.name
            )

        context = AgentContext(
            project_id=project_id,
            workspace_path=str(workspace_path / "source"),
            config={"prompt": prompt},
        )

        # Update status to planning
        project.status = ProjectStatus.PLANNING
        project.progress = 10
        await db.commit()

        # Execute pipeline
        pipeline = task_router.get_default_pipeline()
        results = await pipeline.execute(context)

        # Update project with results
        builder_result = results.get("builder")
        if builder_result and builder_result.success:
            project.generated_path = str(workspace_path / "source")
            project.status = ProjectStatus.COMPLETED
            project.progress = 100
            project.completed_at = datetime.utcnow()
        else:
            project.status = ProjectStatus.FAILED
            project.error_message = (
                builder_result.error if builder_result else "Generation failed"
            )
            project.progress = 0

        await db.commit()


@router.get("/{project_id}/files")
async def list_project_files(
    project_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """List all files in the project workspace."""
    import os
    from pathlib import Path

    from sqlalchemy import select

    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    workspace_path = workspace_manager.get_workspace(str(project_id))
    if not workspace_path:
        return {"files": []}

    source_path = workspace_path / "source"
    if not source_path.exists():
        return {"files": []}

    def build_tree(path: Path, relative_path: str = "") -> list:
        items = []
        try:
            for entry in sorted(
                path.iterdir(), key=lambda x: (x.is_file(), x.name.lower())
            ):
                rel_path = (
                    os.path.join(relative_path, entry.name)
                    if relative_path
                    else entry.name
                )
                if entry.is_dir():
                    children = build_tree(entry, rel_path)
                    items.append(
                        {
                            "name": entry.name,
                            "path": rel_path,
                            "type": "directory",
                            "children": children,
                        }
                    )
                else:
                    stat = entry.stat()
                    items.append(
                        {
                            "name": entry.name,
                            "path": rel_path,
                            "type": "file",
                            "size": stat.st_size,
                            "language": entry.suffix[1:] if entry.suffix else None,
                        }
                    )
        except PermissionError:
            pass
        return items

    files = build_tree(source_path)
    return {"files": files}


@router.get("/{project_id}/files/content")
async def get_file_content(
    project_id: UUID,
    path: str,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """Get the content of a specific file."""

    from sqlalchemy import select

    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    workspace_path = workspace_manager.get_workspace(str(project_id))
    if not workspace_path:
        raise HTTPException(status_code=404, detail="Workspace not found")

    file_path = workspace_path / "source" / path
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    # Security check - ensure path is within workspace
    try:
        file_path.resolve().relative_to((workspace_path / "source").resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not a text file")

    return {
        "path": path,
        "content": content,
        "size": file_path.stat().st_size,
    }


@router.put("/{project_id}/files")
async def save_file_content(
    project_id: UUID,
    data: dict,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """Save content to a file."""

    from sqlalchemy import select

    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    file_path = data.get("path")
    content = data.get("content")

    if not file_path or content is None:
        raise HTTPException(status_code=400, detail="Path and content are required")

    workspace_path = workspace_manager.get_workspace(str(project_id))
    if not workspace_path:
        raise HTTPException(status_code=404, detail="Workspace not found")

    full_path = workspace_path / "source" / file_path

    # Security check
    try:
        full_path.resolve().relative_to((workspace_path / "source").resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    # Create parent directories if needed
    full_path.parent.mkdir(parents=True, exist_ok=True)

    # Write file
    full_path.write_text(content, encoding="utf-8")

    return {"success": True, "path": file_path}
