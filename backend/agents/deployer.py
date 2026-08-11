"""Deployer agent for packaging and deploying projects."""

import json
import logging
from pathlib import Path
from typing import Any

from backend.agents.base import AgentContext, AgentResult, BaseAgent

logger = logging.getLogger(__name__)


class DeployerAgent(BaseAgent):
    """Agent for packaging and deploying projects."""

    def __init__(
        self,
        name: str = "deployer_agent",
        description: str = "Packages and deploys projects",
        config: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(name=name, description=description, config=config)

    @property
    def agent_type(self) -> str:
        return "deployer"

    async def execute(self, context: AgentContext) -> AgentResult:
        """Package and prepare the project for deployment."""
        builder_output = context.previous_outputs.get("builder")
        plan = context.previous_outputs.get("planner")

        if not builder_output:
            return AgentResult(success=False, error="No builder output available")

        generated_files = builder_output.get("generated_files", [])
        if not generated_files:
            return AgentResult(success=False, error="No files to deploy")

        workspace_path = Path(context.workspace_path)
        exports_path = workspace_path / "exports"
        exports_path.mkdir(parents=True, exist_ok=True)

        tech_stack = plan.get("tech_stack", {}) if plan else {}
        deployment_target = tech_stack.get("deployment", "docker")

        results = {
            "artifacts": [],
            "deployment_configs": [],
            "instructions": [],
        }

        try:
            # Generate deployment configurations
            if deployment_target == "docker" or deployment_target == "kubernetes":
                docker_result = await self._generate_docker_configs(
                    workspace_path, exports_path, plan, tech_stack
                )
                results["deployment_configs"].extend(docker_result)

            if deployment_target == "vercel":
                vercel_result = await self._generate_vercel_config(
                    workspace_path, exports_path, plan, tech_stack
                )
                results["deployment_configs"].extend(vercel_result)

            # Create deployment package
            package_result = await self._create_deployment_package(
                workspace_path, exports_path, generated_files, plan
            )
            results["artifacts"].extend(package_result)

            # Generate deployment instructions
            instructions = self._generate_instructions(
                deployment_target, tech_stack, plan
            )
            results["instructions"] = instructions

            return AgentResult(
                success=True,
                output=results,
            )
        except Exception as e:
            logger.error(f"Deployer agent failed: {e}")
            return AgentResult(success=False, error=str(e))

    async def _generate_docker_configs(
        self,
        workspace_path: Path,
        exports_path: Path,
        plan: dict[str, Any],
        tech_stack: dict[str, Any],
    ) -> list[str]:
        """Generate Docker and Docker Compose configurations."""
        configs = []

        language = tech_stack.get("language", "python")
        framework = tech_stack.get("framework", "")

        # Generate Dockerfile
        dockerfile_content = self._get_dockerfile_template(language, framework, plan)
        dockerfile_path = exports_path / "Dockerfile"
        dockerfile_path.write_text(dockerfile_content)
        configs.append("Dockerfile")

        # Generate docker-compose.yml
        compose_content = self._get_docker_compose_template(language, framework, plan)
        compose_path = exports_path / "docker-compose.yml"
        compose_path.write_text(compose_content)
        configs.append("docker-compose.yml")

        # Generate .dockerignore
        dockerignore_content = self._get_dockerignore_template()
        dockerignore_path = exports_path / ".dockerignore"
        dockerignore_path.write_text(dockerignore_content)
        configs.append(".dockerignore")

        return configs

    def _get_dockerfile_template(
        self, language: str, framework: str, plan: dict[str, Any]
    ) -> str:
        """Get Dockerfile template for the tech stack."""
        templates = {
            "python": f"""# Multi-stage build for Python/{framework}
FROM python:3.12-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.12-slim

WORKDIR /app

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy installed packages
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
""",
            "javascript": f"""# Multi-stage build for Node.js/{framework}
FROM node:20-alpine as builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci --only=production

# Production stage
FROM node:20-alpine

WORKDIR /app

# Create non-root user
RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001

# Copy built dependencies
COPY --from=builder --chown=nextjs:nodejs /app/node_modules ./node_modules

# Copy application code
COPY --chown=nextjs:nodejs . .

# Switch to non-root user
USER nextjs

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/health || exit 1

# Run application
CMD ["npm", "start"]
""",
            "go": """# Multi-stage build for Go
FROM golang:1.22-alpine as builder

WORKDIR /app

# Install dependencies
COPY go.mod go.sum ./
RUN go mod download

# Build application
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o main .

# Production stage
FROM alpine:latest

WORKDIR /app

# Create non-root user
RUN addgroup -g 1001 -S appuser && adduser -S -u 1001 -G appuser appuser

# Copy binary
COPY --from=builder --chown=appuser:appuser /app/main .

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8080

# Run application
CMD ["./main"]
""",
        }

        return templates.get(language, templates["python"])

    def _get_docker_compose_template(
        self, language: str, framework: str, plan: dict[str, Any]
    ) -> str:
        """Get docker-compose.yml template."""
        return """version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/orion
    depends_on:
      - db
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

  db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=orion
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:

networks:
  default:
    name: orion-network
"""

    def _get_dockerignore_template(self) -> str:
        """Get .dockerignore template."""
        return """# Git
.git
.gitignore

# Documentation
*.md
docs/

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Testing
coverage/
.htmlcov/
.pytest_cache/
.coverage

# Dependencies
node_modules/
__pycache__/
*.pyc
.pip/
.venv/
venv/
env/

# Build
dist/
build/
*.egg-info/

# Environment
.env
.env.local
.env.*.local

# Docker
Dockerfile*
docker-compose*.yml
.dockerignore

# Exports
exports/
"""

    async def _generate_vercel_config(
        self,
        workspace_path: Path,
        exports_path: Path,
        plan: dict[str, Any],
        tech_stack: dict[str, Any],
    ) -> list[str]:
        """Generate Vercel configuration."""
        configs = []

        vercel_json = {
            "version": 2,
            "builds": [{"src": "package.json", "use": "@vercel/next"}],
            "routes": [{"src": "/(.*)", "dest": "/$1"}],
            "env": {"NEXT_TELEMETRY_DISABLED": "1"},
        }

        vercel_path = exports_path / "vercel.json"
        vercel_path.write_text(json.dumps(vercel_json, indent=2))
        configs.append("vercel.json")

        return configs

    async def _create_deployment_package(
        self,
        workspace_path: Path,
        exports_path: Path,
        generated_files: list[str],
        plan: dict[str, Any],
    ) -> list[str]:
        """Create a deployment package."""
        artifacts = []

        # Create a zip archive of the project
        import zipfile

        package_name = f"{plan.get('name', 'project')}-deployment.zip"
        package_path = exports_path / package_name

        with zipfile.ZipFile(package_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_rel in generated_files:
                file_path = workspace_path / file_rel
                if file_path.exists():
                    zipf.write(file_path, file_rel)

            # Add deployment configs
            for config_file in exports_path.iterdir():
                if config_file.name != package_name:
                    zipf.write(config_file, f"deployment/{config_file.name}")

        artifacts.append(f"deployment/{package_name}")

        # Create a tarball as well
        import tarfile

        tarball_name = f"{plan.get('name', 'project')}-deployment.tar.gz"
        tarball_path = exports_path / tarball_name

        with tarfile.open(tarball_path, "w:gz") as tar:
            for file_rel in generated_files:
                file_path = workspace_path / file_rel
                if file_path.exists():
                    tar.add(file_path, arcname=file_rel)

            for config_file in exports_path.iterdir():
                if config_file.name not in (package_name, tarball_name):
                    tar.add(config_file, arcname=f"deployment/{config_file.name}")

        artifacts.append(f"deployment/{tarball_name}")

        return artifacts

    def _generate_instructions(
        self,
        deployment_target: str,
        tech_stack: dict[str, Any],
        plan: dict[str, Any],
    ) -> list[str]:
        """Generate deployment instructions."""
        instructions = [
            f"# Deployment Instructions for {plan.get('name', 'the project')}",
            "",
            f"## Target: {deployment_target.upper()}",
            "",
        ]

        if deployment_target == "docker":
            instructions.extend(
                [
                    "### Using Docker Compose (Recommended)",
                    "",
                    "1. Navigate to the exports directory:",
                    "   ```bash",
                    "   cd exports",
                    "   ```",
                    "",
                    "2. Start the services:",
                    "   ```bash",
                    "   docker-compose up -d",
                    "   ```",
                    "",
                    "3. Check status:",
                    "   ```bash",
                    "   docker-compose ps",
                    "   ```",
                    "",
                    "4. View logs:",
                    "   ```bash",
                    "   docker-compose logs -f app",
                    "   ```",
                    "",
                    "### Using Docker Directly",
                    "",
                    "1. Build the image:",
                    "   ```bash",
                    "   docker build -t orion-app .",
                    "   ```",
                    "",
                    "2. Run the container:",
                    "   ```bash",
                    "   docker run -d -p 8000:8000 --name orion-app orion-app",
                    "   ```",
                    "",
                ]
            )
        elif deployment_target == "vercel":
            instructions.extend(
                [
                    "### Deploy to Vercel",
                    "",
                    "1. Install Vercel CLI:",
                    "   ```bash",
                    "   npm i -g vercel",
                    "   ```",
                    "",
                    "2. Deploy:",
                    "   ```bash",
                    "   vercel --prod",
                    "   ```",
                    "",
                ]
            )

        instructions.extend(
            [
                "## Post-Deployment",
                "",
                "1. Verify the application is running at the provided URL",
                "2. Check health endpoint: `/health`",
                "3. Monitor logs for any errors",
                "4. Set up monitoring and alerting",
                "5. Configure custom domain if needed",
                "",
                "## Rollback",
                "",
                "To rollback to a previous version:",
                "```bash",
                "docker-compose down",
                "docker tag orion-app:previous orion-app:latest",
                "docker-compose up -d",
                "```",
            ]
        )

        return instructions
