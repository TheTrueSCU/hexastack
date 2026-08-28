"""Hexagonal project scaffolding generator decomposed by architectural layers and template types.

Notes/Architectural Intent:
    Generates standardized microservices adhering strictly to Hexagonal Architecture,
    including .importlinter contracts, tiered CI workflows, and a golden-path working sample.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from hexastack.application.scaffolding import templates

TemplateType = Literal[
    "minimal",
    "web-api",
    "event-driven",
    "mcp-agent",
    "enterprise",
    "grpc-service",
    "graphql-service",
]


@dataclass(frozen=True)
class ScaffoldConfig:
    """Configuration parameters for scaffolding a new Hexastack project."""

    name: str
    template: TemplateType = "web-api"
    description: str = "A modern microservice powered by Hexastack."
    python_version: str = ">=3.13"
    db_type: str = "in-memory"  # in-memory, sqlite, postgres
    include_events: bool = False
    include_mcp: bool = False
    include_grpc: bool = False
    include_graphql: bool = False
    include_release: bool = False
    include_openssf: bool = False


class ProjectScaffolder:
    """Engine responsible for rendering and writing hexagonal service scaffolds.

    Notes/Architectural Intent:
        Creates a clean directory layout (domain, ports, adapters/driving, adapters/driven, infra)
        with zero-framework domain isolation, pre-configured import-linter rules, and passing tests.
    """

    def __init__(self, config: ScaffoldConfig, output_dir: Path | None = None) -> None:
        """Initialize project scaffolder with target configuration and root destination directory.

        Args:
            config: Project scaffolding parameters.
            output_dir: Destination base directory (defaults to current working directory).
        """
        self.config = config
        self.base_dir = output_dir or Path.cwd()
        self.project_slug = config.name.lower().replace("-", "_").replace(" ", "_")
        self.package_name = self.project_slug
        self.target_dir = self.base_dir / config.name

    def generate(self) -> Path:
        """Render and write all project files to disk.

        Returns:
            Absolute Path to the newly scaffolded project directory.

        Raises:
            FileExistsError: If target directory already exists and is non-empty.
        """
        self._validate_target_directory()
        self._write_config_files()
        self._write_domain_layer()
        self._write_ports_layer()
        self._write_adapters_layer()
        self._write_infra_layer()
        self._write_test_suite()
        return self.target_dir

    def _validate_target_directory(self) -> None:
        if self.target_dir.exists() and any(self.target_dir.iterdir()):
            raise FileExistsError(
                f"Directory '{self.target_dir}' already exists and is not empty."
            )
        self.target_dir.mkdir(parents=True, exist_ok=True)

    def _write_file(self, rel_path: str, content: str) -> None:
        file_path = self.target_dir / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content.strip() + "\n", encoding="utf-8")

    # ----------------------------------------------------------------------
    # Configuration & Tooling Files
    # ----------------------------------------------------------------------

    def _write_config_files(self) -> None:
        self._write_file(
            "pyproject.toml",
            templates.render_pyproject_toml(self.config, self.package_name),
        )
        self._write_file(
            ".importlinter", templates.render_importlinter(self.package_name)
        )
        self._write_file(".pre-commit-config.yaml", templates.render_precommit())
        self._write_file(".github/workflows/ci.yml", templates.render_github_ci())
        self._write_file(
            "README.md", templates.render_readme(self.config, self.package_name)
        )
        self._write_file("Dockerfile", templates.render_dockerfile(self.config))
        self._write_file(".dockerignore", templates.render_dockerignore())

        if self.config.include_release:
            self._write_file(
                ".github/workflows/release.yml",
                templates.render_github_release(self.config),
            )
            self._write_file("CHANGELOG.md", templates.render_changelog())

        if self.config.include_openssf:
            self._write_file(
                ".github/workflows/scorecard.yml", templates.render_github_scorecard()
            )
            self._write_file("SECURITY.md", templates.render_security_md(self.config))
            self._write_file(
                "GOVERNANCE.md", templates.render_governance_md(self.config)
            )
            self._write_file(
                "CODE_OF_CONDUCT.md", templates.render_code_of_conduct_md()
            )

    # ----------------------------------------------------------------------
    # Domain Layer (Pure Python)
    # ----------------------------------------------------------------------

    def _write_domain_layer(self) -> None:
        self._write_file(
            f"src/{self.package_name}/__init__.py", '"""Service root package."""\n'
        )
        self._write_file(f"src/{self.package_name}/py.typed", "")
        self._write_file(
            f"src/{self.package_name}/domain/__init__.py",
            templates.render_domain_init(),
        )
        self._write_file(
            f"src/{self.package_name}/domain/models.py",
            templates.render_domain_models(),
        )
        self._write_file(
            f"src/{self.package_name}/domain/commands.py",
            templates.render_domain_commands(),
        )

    # ----------------------------------------------------------------------
    # Ports Layer (Abstract Interfaces)
    # ----------------------------------------------------------------------

    def _write_ports_layer(self) -> None:
        self._write_file(
            f"src/{self.package_name}/ports/__init__.py", templates.render_ports_init()
        )
        self._write_file(
            f"src/{self.package_name}/ports/repositories.py",
            templates.render_ports_repositories(self.package_name),
        )

    # ----------------------------------------------------------------------
    # Adapters Layer (Driving & Driven)
    # ----------------------------------------------------------------------

    def _write_adapters_layer(self) -> None:
        self._write_file(
            f"src/{self.package_name}/adapters/__init__.py",
            '"""Driving and driven adapters."""\n',
        )
        self._write_file(
            f"src/{self.package_name}/adapters/driven/__init__.py",
            '"""Driven infrastructure adapters."""\n',
        )
        self._write_file(
            f"src/{self.package_name}/adapters/driven/database.py",
            templates.render_driven_database(self.package_name),
        )
        self._write_file(
            f"src/{self.package_name}/adapters/driving/__init__.py",
            '"""Driving presentation adapters."""\n',
        )
        self._write_file(
            f"src/{self.package_name}/adapters/driving/cli.py",
            templates.render_driving_cli(self.package_name),
        )

        if (
            self.config.template in ("web-api", "enterprise", "graphql-service")
            or self.config.include_graphql
        ):
            self._write_file(
                f"src/{self.package_name}/adapters/driving/http.py",
                templates.render_driving_http(self.package_name),
            )

        if (
            self.config.template in ("grpc-service", "enterprise")
            or self.config.include_grpc
        ):
            self._write_file(
                f"src/{self.package_name}/adapters/driving/grpc.py",
                templates.render_driving_grpc(self.package_name),
            )
            self._write_file("buf.yaml", templates.render_buf_yaml())
            self._write_file(
                f"protos/{self.package_name}/v1/item.proto",
                templates.render_proto_file(self.package_name),
            )

        if (
            self.config.template in ("graphql-service", "enterprise")
            or self.config.include_graphql
        ):
            self._write_file(
                f"src/{self.package_name}/adapters/driving/graphql.py",
                templates.render_driving_graphql(self.package_name),
            )

        if (
            self.config.template in ("mcp-agent", "enterprise")
            or self.config.include_mcp
        ):
            self._write_file(
                f"src/{self.package_name}/adapters/driving/mcp.py",
                templates.render_driving_mcp(self.package_name),
            )
            self._write_file("mcp.json", templates.render_mcp_json(self.config))

    # ----------------------------------------------------------------------
    # Infra Layer (Kernel, Handlers, Bootstrap)
    # ----------------------------------------------------------------------

    def _write_infra_layer(self) -> None:
        self._write_file(
            f"src/{self.package_name}/infra/__init__.py",
            '"""Infrastructure and dependency injection assembly."""\n',
        )
        self._write_file(
            f"src/{self.package_name}/infra/config.py",
            templates.render_infra_config(self.config),
        )
        self._write_file(
            f"src/{self.package_name}/infra/handlers.py",
            templates.render_infra_handlers(self.package_name),
        )
        self._write_file(
            f"src/{self.package_name}/infra/bootstrap.py",
            templates.render_infra_bootstrap(self.config, self.package_name),
        )

    # ----------------------------------------------------------------------
    # Test Suite
    # ----------------------------------------------------------------------

    def _write_test_suite(self) -> None:
        self._write_file("tests/__init__.py", "")
        self._write_file(
            "tests/conftest.py", templates.render_test_conftest(self.package_name)
        )
        self._write_file(
            "tests/unit/test_domain.py", templates.render_test_domain(self.package_name)
        )
        self._write_file(
            "tests/hypothesis/test_domain_fuzz.py",
            templates.render_test_domain_fuzz(self.package_name),
        )


def scaffold_project(
    name: str,
    template: TemplateType = "web-api",
    description: str = "A modern microservice powered by Hexastack.",
    db_type: str = "in-memory",
    include_events: bool = False,
    include_mcp: bool = False,
    include_grpc: bool = False,
    include_graphql: bool = False,
    include_release: bool = False,
    include_openssf: bool = False,
    output_dir: Path | None = None,
) -> Path:
    """Convenience helper to scaffold a new Hexastack project."""
    config = ScaffoldConfig(
        name=name,
        template=template,
        description=description,
        db_type=db_type,
        include_events=include_events,
        include_mcp=include_mcp,
        include_grpc=include_grpc,
        include_graphql=include_graphql,
        include_release=include_release,
        include_openssf=include_openssf,
    )
    scaffolder = ProjectScaffolder(config, output_dir=output_dir)
    return scaffolder.generate()
