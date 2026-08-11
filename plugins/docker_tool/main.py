"""Docker Tool Plugin."""

import asyncio
import logging
from typing import Any

from backend.plugins.sdk.base import ToolPlugin, PluginContext, PluginManifest

logger = logging.getLogger(__name__)


class DockerToolPlugin(ToolPlugin):
    """Docker Management Tool Plugin."""

    def __init__(self, manifest: PluginManifest, context: PluginContext) -> None:
        super().__init__(manifest, context)
        self._client = None
        self._docker_host = "unix:///var/run/docker.sock"
        self._timeout = 60

    async def _on_initialize(self) -> None:
        """Initialize the tool."""
        self._docker_host = self.get_config("docker_host", "unix:///var/run/docker.sock")
        self._timeout = self.get_config("timeout", 60)

        try:
            import docker
            self._client = docker.DockerClient(base_url=self._docker_host, timeout=self._timeout)
            # Test connection
            self._client.ping()
        except Exception as e:
            logger.warning(f"Docker connection failed: {e}")

    async def _on_shutdown(self) -> None:
        """Shutdown the tool."""
        if self._client:
            self._client.close()

    async def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        """Execute a Docker operation."""
        if not self._client:
            return {"error": "Docker client not initialized"}

        action = args.get("action")
        if not action:
            return {"error": "No action specified"}

        try:
            if action == "list_containers":
                return await self._list_containers(args)
            elif action == "inspect_container":
                return await self._inspect_container(args)
            elif action == "start_container":
                return await self._start_container(args)
            elif action == "stop_container":
                return await self._stop_container(args)
            elif action == "restart_container":
                return await self._restart_container(args)
            elif action == "remove_container":
                return await self._remove_container(args)
            elif action == "create_container":
                return await self._create_container(args)
            elif action == "list_images":
                return await self._list_images(args)
            elif action == "pull_image":
                return await self._pull_image(args)
            elif action == "remove_image":
                return await self._remove_image(args)
            elif action == "build_image":
                return await self._build_image(args)
            elif action == "list_networks":
                return await self._list_networks(args)
            elif action == "list_volumes":
                return await self._list_volumes(args)
            elif action == "logs":
                return await self._logs(args)
            elif action == "exec":
                return await self._exec(args)
            else:
                return {"error": f"Unknown action: {action}"}

        except Exception as e:
            logger.error(f"Docker error: {e}")
            return {"error": str(e)}

    async def _list_containers(self, args: dict) -> dict[str, Any]:
        """List containers."""
        all_containers = args.get("all", False)
        containers = self._client.containers.list(all=all_containers)
        return {
            "containers": [
                {
                    "id": c.id[:12],
                    "name": c.name,
                    "image": c.image.tags[0] if c.image.tags else c.image.id[:12],
                    "status": c.status,
                    "ports": c.ports,
                }
                for c in containers
            ]
        }

    async def _inspect_container(self, args: dict) -> dict[str, Any]:
        """Inspect a container."""
        container_id = args.get("container_id")
        container = self._client.containers.get(container_id)
        return container.attrs

    async def _start_container(self, args: dict) -> dict[str, Any]:
        """Start a container."""
        container_id = args.get("container_id")
        container = self._client.containers.get(container_id)
        container.start()
        return {"success": True, "message": f"Started {container.name}"}

    async def _stop_container(self, args: dict) -> dict[str, Any]:
        """Stop a container."""
        container_id = args.get("container_id")
        timeout = args.get("timeout", 10)
        container = self._client.containers.get(container_id)
        container.stop(timeout=timeout)
        return {"success": True, "message": f"Stopped {container.name}"}

    async def _restart_container(self, args: dict) -> dict[str, Any]:
        """Restart a container."""
        container_id = args.get("container_id")
        timeout = args.get("timeout", 10)
        container = self._client.containers.get(container_id)
        container.restart(timeout=timeout)
        return {"success": True, "message": f"Restarted {container.name}"}

    async def _remove_container(self, args: dict) -> dict[str, Any]:
        """Remove a container."""
        container_id = args.get("container_id")
        force = args.get("force", False)
        container = self._client.containers.get(container_id)
        container.remove(force=force)
        return {"success": True, "message": f"Removed {container.name}"}

    async def _create_container(self, args: dict) -> dict[str, Any]:
        """Create a container."""
        image = args.get("image")
        name = args.get("name")
        command = args.get("command")
        environment = args.get("environment", {})
        ports = args.get("ports", {})
        volumes = args.get("volumes", {})
        detach = args.get("detach", True)

        container = self._client.containers.create(
            image=image,
            name=name,
            command=command,
            environment=environment,
            ports=ports,
            volumes=volumes,
            detach=detach,
        )
        return {"success": True, "container_id": container.id[:12], "name": container.name}

    async def _list_images(self, args: dict) -> dict[str, Any]:
        """List images."""
        images = self._client.images.list()
        return {
            "images": [
                {
                    "id": img.id[7:19],
                    "tags": img.tags,
                    "size": img.attrs.get("Size", 0),
                }
                for img in images
            ]
        }

    async def _pull_image(self, args: dict) -> dict[str, Any]:
        """Pull an image."""
        image = args.get("image")
        tag = args.get("tag", "latest")
        full_image = f"{image}:{tag}"
        image_obj = self._client.images.pull(full_image)
        return {"success": True, "image": full_image, "id": image_obj.id[7:19]}

    async def _remove_image(self, args: dict) -> dict[str, Any]:
        """Remove an image."""
        image_id = args.get("image_id")
        force = args.get("force", False)
        self._client.images.remove(image_id, force=force)
        return {"success": True, "message": f"Removed {image_id}"}

    async def _build_image(self, args: dict) -> dict[str, Any]:
        """Build an image."""
        path = args.get("path", ".")
        tag = args.get("tag")
        dockerfile = args.get("dockerfile", "Dockerfile")
        image_obj, logs = self._client.images.build(
            path=path,
            tag=tag,
            dockerfile=dockerfile,
        )
        return {"success": True, "image_id": image_obj.id[7:19], "tag": tag}

    async def _list_networks(self, args: dict) -> dict[str, Any]:
        """List networks."""
        networks = self._client.networks.list()
        return {
            "networks": [
                {"id": n.id[:12], "name": n.name, "driver": n.attrs.get("Driver"), "scope": n.attrs.get("Scope")}
                for n in networks
            ]
        }

    async def _list_volumes(self, args: dict) -> dict[str, Any]:
        """List volumes."""
        volumes = self._client.volumes.list()
        return {
            "volumes": [
                {"name": v.name, "driver": v.attrs.get("Driver"), "mountpoint": v.attrs.get("Mountpoint")}
                for v in volumes
            ]
        }

    async def _logs(self, args: dict) -> dict[str, Any]:
        """Get container logs."""
        container_id = args.get("container_id")
        tail = args.get("tail", 100)
        container = self._client.containers.get(container_id)
        logs = container.logs(tail=tail, timestamps=True).decode("utf-8")
        return {"logs": logs}

    async def _exec(self, args: dict) -> dict[str, Any]:
        """Execute command in container."""
        container_id = args.get("container_id")
        command = args.get("command")
        container = self._client.containers.get(container_id)
        exec_result = container.exec_run(command)
        return {
            "exit_code": exec_result.exit_code,
            "output": exec_result.output.decode("utf-8") if exec_result.output else "",
        }

    def get_tool_schema(self) -> dict[str, Any]:
        """Get tool schema for LLM function calling."""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "list_containers", "inspect_container", "start_container",
                        "stop_container", "restart_container", "remove_container",
                        "create_container", "list_images", "pull_image",
                        "remove_image", "build_image", "list_networks",
                        "list_volumes", "logs", "exec"
                    ],
                    "description": "Docker action to perform"
                },
                "container_id": {"type": "string", "description": "Container ID or name"},
                "all": {"type": "boolean", "description": "Show all containers"},
                "timeout": {"type": "integer", "description": "Stop timeout in seconds"},
                "force": {"type": "boolean", "description": "Force operation"},
                "image": {"type": "string", "description": "Image name"},
                "name": {"type": "string", "description": "Container name"},
                "command": {"type": "string", "description": "Command to run"},
                "environment": {"type": "object", "description": "Environment variables"},
                "ports": {"type": "object", "description": "Port mappings"},
                "volumes": {"type": "object", "description": "Volume mappings"},
                "detach": {"type": "boolean", "description": "Run detached"},
                "tag": {"type": "string", "description": "Image tag"},
                "path": {"type": "string", "description": "Build context path"},
                "dockerfile": {"type": "string", "description": "Dockerfile name"},
                "tail": {"type": "integer", "description": "Number of log lines"},
            },
            "required": ["action"]
        }