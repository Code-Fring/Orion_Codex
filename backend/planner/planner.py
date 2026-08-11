"""Project planner for creating detailed specifications."""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ProjectType(Enum):
    """Types of projects."""

    WEB_APP = "web_app"
    MOBILE_APP = "mobile_app"
    DESKTOP_APP = "desktop_app"
    API = "api"
    CLI = "cli"
    LIBRARY = "library"
    GAME = "game"
    ML_PIPELINE = "ml_pipeline"
    AUTOMATION = "automation"
    SAAS = "saas"
    MICROSERVICES = "microservices"
    OTHER = "other"


class Complexity(Enum):
    """Project complexity levels."""

    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


@dataclass
class TechStack:
    """Technology stack specification."""

    language: str = "python"
    framework: str = "fastapi"
    database: str = "sqlite"
    orm: str = "sqlalchemy"
    testing: str = "pytest"
    deployment: str = "docker"
    frontend: str | None = None
    additional: list[str] = field(default_factory=list)


@dataclass
class ArchitectureSpec:
    """Architecture specification."""

    pattern: str = "layered"
    components: list[dict[str, Any]] = field(default_factory=list)
    data_flow: str = ""


@dataclass
class TaskSpec:
    """Task specification."""

    name: str
    description: str
    agent_type: str
    dependencies: list[str] = field(default_factory=list)
    priority: int = 1
    estimated_duration: str = "30m"


@dataclass
class Milestone:
    """Project milestone."""

    name: str
    tasks: list[str] = field(default_factory=list)


@dataclass
class ProjectPlan:
    """Complete project plan."""

    project_type: ProjectType = ProjectType.WEB_APP
    description: str = ""
    features: list[str] = field(default_factory=list)
    tech_stack: TechStack = field(default_factory=TechStack)
    architecture: ArchitectureSpec = field(default_factory=ArchitectureSpec)
    file_structure: dict[str, Any] = field(default_factory=dict)
    tasks: list[TaskSpec] = field(default_factory=list)
    milestones: list[Milestone] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    complexity: Complexity = Complexity.MODERATE
    estimated_files: int = 0


class ProjectPlanner:
    """Plans projects from requirements."""

    def __init__(self) -> None:
        self.tech_stack_templates = self._load_tech_stack_templates()

    def _load_tech_stack_templates(self) -> dict[str, dict[str, Any]]:
        """Load technology stack templates."""
        return {
            "python_fastapi": {
                "language": "python",
                "framework": "fastapi",
                "database": "postgresql",
                "orm": "sqlalchemy",
                "testing": "pytest",
                "deployment": "docker",
                "additional": ["uvicorn", "pydantic", "alembic"],
            },
            "python_django": {
                "language": "python",
                "framework": "django",
                "database": "postgresql",
                "orm": "django_orm",
                "testing": "pytest",
                "deployment": "docker",
                "additional": ["djangorestframework", "celery"],
            },
            "typescript_nextjs": {
                "language": "typescript",
                "framework": "nextjs",
                "database": "postgresql",
                "orm": "prisma",
                "testing": "jest",
                "deployment": "vercel",
                "frontend": "react",
                "additional": ["tailwindcss", "next-auth"],
            },
            "javascript_react": {
                "language": "javascript",
                "framework": "vite",
                "database": "firebase",
                "orm": "none",
                "testing": "jest",
                "deployment": "vercel",
                "frontend": "react",
                "additional": ["react-router", "axios"],
            },
            "go_gin": {
                "language": "go",
                "framework": "gin",
                "database": "postgresql",
                "orm": "gorm",
                "testing": "testify",
                "deployment": "docker",
                "additional": ["viper", "zap"],
            },
        }

    def get_tech_stack_template(self, key: str) -> dict[str, Any] | None:
        """Get a tech stack template by key."""
        return self.tech_stack_templates.get(key)

    def list_tech_stack_templates(self) -> list[str]:
        """List available tech stack templates."""
        return list(self.tech_stack_templates.keys())

    def create_plan_from_analysis(self, analysis: dict[str, Any]) -> ProjectPlan:
        """Create a project plan from analysis results."""
        plan = ProjectPlan()

        # Set basic info
        plan.project_type = ProjectType(analysis.get("project_type", "web_app"))
        plan.description = analysis.get("description", "")
        plan.features = analysis.get("features", [])
        plan.constraints = analysis.get("constraints", [])
        plan.complexity = Complexity(analysis.get("complexity", "moderate"))
        plan.estimated_files = analysis.get("estimated_files", 0)

        # Determine tech stack
        tech_prefs = analysis.get("tech_stack_preferences", {})
        plan.tech_stack = self._determine_tech_stack(tech_prefs, plan.project_type)

        # Generate architecture
        plan.architecture = self._generate_architecture(
            plan.project_type, plan.tech_stack
        )

        # Generate file structure
        plan.file_structure = self._generate_file_structure(
            plan.project_type, plan.tech_stack
        )

        # Generate tasks
        plan.tasks = self._generate_tasks(plan)

        # Generate milestones
        plan.milestones = self._generate_milestones(plan.tasks)

        return plan

    def _determine_tech_stack(
        self,
        preferences: dict[str, Any],
        project_type: ProjectType,
    ) -> TechStack:
        """Determine the best tech stack based on preferences and project type."""
        # Start with defaults based on project type
        defaults = {
            ProjectType.WEB_APP: "python_fastapi",
            ProjectType.API: "python_fastapi",
            ProjectType.SAAS: "typescript_nextjs",
            ProjectType.MOBILE_APP: "javascript_react",
            ProjectType.DESKTOP_APP: "python_fastapi",
            ProjectType.CLI: "python_fastapi",
            ProjectType.GAME: "python_fastapi",
            ProjectType.ML_PIPELINE: "python_fastapi",
            ProjectType.AUTOMATION: "python_fastapi",
        }

        template_key = defaults.get(project_type, "python_fastapi")
        template = self.tech_stack_templates.get(
            template_key, self.tech_stack_templates["python_fastapi"]
        )

        # Override with preferences
        tech_stack = TechStack(**template)

        if preferences.get("language"):
            tech_stack.language = preferences["language"]
        if preferences.get("framework"):
            tech_stack.framework = preferences["framework"]
        if preferences.get("database"):
            tech_stack.database = preferences["database"]
        if preferences.get("deployment"):
            tech_stack.deployment = preferences["deployment"]

        return tech_stack

    def _generate_architecture(
        self,
        project_type: ProjectType,
        tech_stack: TechStack,
    ) -> ArchitectureSpec:
        """Generate architecture specification."""
        # Base architecture patterns by project type
        patterns = {
            ProjectType.WEB_APP: "layered",
            ProjectType.API: "layered",
            ProjectType.SAAS: "modular_monolith",
            ProjectType.MICROSERVICES: "microservices",
        }

        components = [
            {"name": "api", "type": "backend", "description": "REST API layer"},
            {"name": "core", "type": "backend", "description": "Business logic"},
            {"name": "data", "type": "database", "description": "Data access layer"},
            {"name": "models", "type": "shared", "description": "Data models"},
        ]

        if tech_stack.frontend:
            components.append(
                {
                    "name": "frontend",
                    "type": "frontend",
                    "description": f"{tech_stack.frontend} frontend application",
                }
            )

        return ArchitectureSpec(
            pattern=patterns.get(project_type, "layered"),
            components=components,
            data_flow="Client -> API -> Core -> Data -> Database",
        )

    def _generate_file_structure(
        self,
        project_type: ProjectType,
        tech_stack: TechStack,
    ) -> dict[str, Any]:
        """Generate project file structure."""
        structure = {
            "directories": [
                "src",
                "tests",
                "assets",
                "logs",
                "exports",
            ],
        }

        if tech_stack.language == "python":
            structure["src"] = {
                "api": ["routes.py", "schemas.py", "dependencies.py"],
                "core": ["services.py", "exceptions.py", "config.py"],
                "data": ["models.py", "repository.py", "database.py"],
                "models": ["__init__.py"],
                "main.py": "",
            }
            structure["tests"] = {
                "unit": ["test_services.py", "test_api.py"],
                "integration": ["test_api_integration.py"],
                "conftest.py": "",
            }
            structure["root"] = [
                "requirements.txt",
                "pyproject.toml",
                ".env.example",
                "README.md",
                "Dockerfile",
                "docker-compose.yml",
            ]
        elif tech_stack.language in ("javascript", "typescript"):
            structure["src"] = {
                "app": ["page.tsx", "layout.tsx"],
                "components": ["ui/", "forms/"],
                "lib": ["api.ts", "utils.ts", "db.ts"],
                "hooks": ["useApi.ts"],
                "types": ["index.ts"],
            }
            structure["tests"] = {
                "unit": ["components.test.tsx", "lib.test.ts"],
                "integration": ["api.test.ts"],
                "setup.ts": "",
            }
            structure["root"] = [
                "package.json",
                "tsconfig.json",
                "next.config.js"
                if tech_stack.framework == "nextjs"
                else "vite.config.ts",
                ".env.example",
                "README.md",
                "Dockerfile",
                "docker-compose.yml",
            ]

        return structure

    def _generate_tasks(self, plan: ProjectPlan) -> list[TaskSpec]:
        """Generate task list from plan."""
        tasks = [
            TaskSpec(
                name="setup_project",
                description="Initialize project structure and configuration",
                agent_type="builder",
                priority=1,
                estimated_duration="15m",
            ),
            TaskSpec(
                name="generate_core",
                description="Generate core business logic",
                agent_type="builder",
                dependencies=["setup_project"],
                priority=2,
                estimated_duration="30m",
            ),
            TaskSpec(
                name="generate_api",
                description="Generate API layer",
                agent_type="builder",
                dependencies=["setup_project"],
                priority=2,
                estimated_duration="30m",
            ),
            TaskSpec(
                name="generate_data_layer",
                description="Generate data models and repository",
                agent_type="builder",
                dependencies=["setup_project"],
                priority=2,
                estimated_duration="20m",
            ),
        ]

        if plan.tech_stack.frontend:
            tasks.append(
                TaskSpec(
                    name="generate_frontend",
                    description="Generate frontend application",
                    agent_type="builder",
                    dependencies=["setup_project"],
                    priority=2,
                    estimated_duration="45m",
                )
            )

        tasks.extend(
            [
                TaskSpec(
                    name="generate_tests",
                    description="Generate and run tests",
                    agent_type="tester",
                    dependencies=[
                        "generate_core",
                        "generate_api",
                        "generate_data_layer",
                    ],
                    priority=3,
                    estimated_duration="30m",
                ),
                TaskSpec(
                    name="review_code",
                    description="Review code quality",
                    agent_type="reviewer",
                    dependencies=["generate_tests"],
                    priority=4,
                    estimated_duration="15m",
                ),
                TaskSpec(
                    name="generate_deployment",
                    description="Generate deployment configurations",
                    agent_type="deployer",
                    dependencies=["review_code"],
                    priority=5,
                    estimated_duration="10m",
                ),
            ]
        )

        return tasks

    def _generate_milestones(self, tasks: list[TaskSpec]) -> list[Milestone]:
        """Generate milestones from tasks."""
        milestones = [
            Milestone(name="Setup", tasks=["setup_project"]),
            Milestone(
                name="Core Implementation",
                tasks=["generate_core", "generate_api", "generate_data_layer"],
            ),
        ]

        if any(t.name == "generate_frontend" for t in tasks):
            milestones.append(Milestone(name="Frontend", tasks=["generate_frontend"]))

        milestones.extend(
            [
                Milestone(name="Testing", tasks=["generate_tests"]),
                Milestone(name="Review", tasks=["review_code"]),
                Milestone(name="Deployment Prep", tasks=["generate_deployment"]),
            ]
        )

        return milestones
