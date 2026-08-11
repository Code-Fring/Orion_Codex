"""WebSocket routes for real-time updates."""

import json
from uuid import UUID

from backend.core.auth.jwt import get_user_id_from_token
from backend.database.connection import get_db_session
from backend.models.models import Project
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/ws", tags=["websocket"])


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        self._active_connections: dict[str, set[WebSocket]] = {}
        self._user_connections: dict[str, set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, project_id: str, user_id: str):
        await websocket.accept()
        if project_id not in self._active_connections:
            self._active_connections[project_id] = set()
        self._active_connections[project_id].add(websocket)

        if user_id not in self._user_connections:
            self._user_connections[user_id] = set()
        self._user_connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, project_id: str, user_id: str):
        if project_id in self._active_connections:
            self._active_connections[project_id].discard(websocket)
            if not self._active_connections[project_id]:
                del self._active_connections[project_id]

        if user_id in self._user_connections:
            self._user_connections[user_id].discard(websocket)
            if not self._user_connections[user_id]:
                del self._user_connections[user_id]

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_text(json.dumps(message))
        except Exception:
            pass

    async def broadcast_to_project(self, project_id: str, message: dict):
        if project_id in self._active_connections:
            disconnected = set()
            for websocket in self._active_connections[project_id]:
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception:
                    disconnected.add(websocket)

            for ws in disconnected:
                self._active_connections[project_id].discard(ws)

    async def broadcast_to_user(self, user_id: str, message: dict):
        if user_id in self._user_connections:
            disconnected = set()
            for websocket in self._user_connections[user_id]:
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception:
                    disconnected.add(websocket)

            for ws in disconnected:
                self._user_connections[user_id].discard(ws)

    def get_total_connections(self) -> int:
        total = 0
        for conns in self._active_connections.values():
            total += len(conns)
        return total

    def get_project_connection_count(self, project_id: str) -> int:
        return len(self._active_connections.get(project_id, set()))

    async def broadcast_task_update(self, project_id: str, task_data: dict):
        """Broadcast task update to all connections for a project."""
        await self.broadcast_to_project(
            project_id,
            {
                "type": "task_update",
                "project_id": project_id,
                "data": task_data,
            },
        )

    async def broadcast_log(self, project_id: str, log_data: dict):
        """Broadcast log entry to all connections for a project."""
        await self.broadcast_to_project(
            project_id,
            {
                "type": "log",
                "project_id": project_id,
                "data": log_data,
            },
        )

    async def broadcast_progress(self, project_id: str, progress: int, status: str):
        """Broadcast progress update to all connections for a project."""
        await self.broadcast_to_project(
            project_id,
            {
                "type": "progress",
                "project_id": project_id,
                "data": {
                    "progress": progress,
                    "status": status,
                },
            },
        )

    async def broadcast_project_status(self, project_id: str, status_data: dict):
        """Broadcast project status update to all connections for a project."""
        await self.broadcast_to_project(
            project_id,
            {
                "type": "project_status",
                "project_id": project_id,
                "data": status_data,
            },
        )


ws_manager = ConnectionManager()


# Helper functions for agents/tasks to broadcast updates
async def broadcast_task_update(project_id: str, task_data: dict):
    """Broadcast task update to WebSocket clients."""
    await ws_manager.broadcast_task_update(project_id, task_data)


async def broadcast_log(project_id: str, log_data: dict):
    """Broadcast log entry to WebSocket clients."""
    await ws_manager.broadcast_log(project_id, log_data)


async def broadcast_progress(project_id: str, progress: int, status: str):
    """Broadcast progress update to WebSocket clients."""
    await ws_manager.broadcast_progress(project_id, progress, status)


async def broadcast_project_status(project_id: str, status_data: dict):
    """Broadcast project status update to WebSocket clients."""
    await ws_manager.broadcast_project_status(project_id, status_data)


async def websocket_endpoint(websocket: WebSocket, project_id: str):
    """Handle WebSocket connection for project updates."""
    user_id = websocket.query_params.get("user_id", "anonymous")

    await ws_manager.connect(websocket, project_id, user_id)

    try:
        await ws_manager.send_personal_message(
            {"type": "connected", "project_id": project_id}, websocket
        )

        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await ws_manager.send_personal_message({"type": "pong"}, websocket)
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, project_id, user_id)
    except Exception:
        ws_manager.disconnect(websocket, project_id, user_id)


async def get_current_user_id_ws(websocket: WebSocket) -> UUID:
    """Get current user ID from WebSocket query parameters."""
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise HTTPException(status_code=401, detail="Missing token")

    user_id = get_user_id_from_token(token)
    if not user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise HTTPException(status_code=401, detail="Invalid token")

    return UUID(user_id)


async def verify_project_access(
    project_id: UUID, user_id: UUID, db: AsyncSession
) -> Project:
    """Verify user has access to the project."""
    from sqlalchemy import select

    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return project


@router.websocket("/project/{project_id}")
async def project_websocket(
    websocket: WebSocket,
    project_id: UUID,
    user_id: UUID = Depends(get_current_user_id_ws),
    db: AsyncSession = Depends(get_db_session),
):
    """WebSocket endpoint for project real-time updates."""
    # Verify project access
    try:
        await verify_project_access(project_id, user_id, db)
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket_endpoint(websocket, str(project_id))


@router.get("/stats")
async def websocket_stats():
    """Get WebSocket connection statistics."""
    return {
        "total_connections": ws_manager.get_total_connections(),
        "projects": {
            project_id: ws_manager.get_project_connection_count(project_id)
            for project_id in ws_manager._active_connections.keys()
        },
    }
