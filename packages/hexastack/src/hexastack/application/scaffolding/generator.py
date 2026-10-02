"""Hexagonal project scaffolding generator decomposed by architectural layers and template types.

Notes/Architectural Intent:
    Generates standardized microservices adhering strictly to Hexagonal Architecture,
    including .importlinter contracts, tiered CI workflows, and a golden-path working sample.
"""

from __future__ import annotations

from pathlib import Path

from hexastack.application.scaffolding import templates
from hexastack.application.scaffolding.models import (
    ScaffoldConfig,
)
from hexastack_core.utils.fs import atomic_write_text


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
        atomic_write_text(file_path, content.strip() + "\n", encoding="utf-8")

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
        self._write_file(".secrets.baseline", templates.render_secrets_baseline())
        self._write_file(".github/workflows/ci.yml", templates.render_github_ci())
        self._write_file(
            "README.md", templates.render_readme(self.config, self.package_name)
        )
        self._write_file("Dockerfile", templates.render_dockerfile(self.config))
        self._write_file(".dockerignore", templates.render_dockerignore())
        self._write_file(".gitignore", templates.render_gitignore())
        self._write_file(
            ".devcontainer/devcontainer.json",
            templates.render_devcontainer_json(self.config),
        )

        if self.config.include_sentry:
            self._write_file(
                ".env.example",
                "# Sentry Error Tracking & Distributed Tracing\nSENTRY_DSN=\nSENTRY_ENVIRONMENT=development\n",
            )

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

        if self.config.include_agents:
            self._write_agents_hub()

    def _write_agents_hub(self) -> None:
        rules_content = f"""---
trigger: always_on
description: Architectural invariants and hexagonal boundary rules for {self.config.name}.
---

## Architectural Invariants for {self.config.name}

1. **Hexagonal Architecture Layer Isolation**:
   - `domain/` contains 100% pure entities, value objects, and business logic with ZERO framework imports.
   - `ports/` defines abstract ABC interfaces (`@abstractmethod`).
   - `adapters/` contains driving (HTTP, CLI, gRPC) and driven (database, cache, buses) implementations. Adapters must NEVER import from `infra/`.
   - `infra/` contains assembly, dependency injection (rodi), bootstrapper, and environment configuration.
   - Enforced by `import-linter` via `uv run lint-imports` or `hexaqual sanity`.

2. **Docstrings & Public APIs**:
   - Every public module, class, and function must have Google-style docstrings with `Args:`, `Returns:`, `Raises:`, and a `Notes/Architectural Intent:` section.

3. **1:1 Test Symmetry & Side-Effect Free Assertions**:
   - Every `src/{self.package_name}/<path>.py` file requires a matching `tests/unit/<path>/test_<name>.py` and `__init__.py`.
   - In test assertions, assign method return values to variables first before evaluating `assert` to avoid CodeQL side-effect alerts.
   - Cognitive complexity must remain <= 25 per function (enforced by `complexipy`).
"""
        agents_content = f"""# AI Agent Workspace Guardrails

> This repository adheres to strict Hexagonal Architecture and quality governance enforced by [**Hexaqual**](https://github.com/TheTrueSCU/hexaqual).

## Active Invariants

- Domain purity: `domain/` has no external dependencies.
- Hexagonal boundaries: `adapters/` communicates exclusively via `ports/` and never imports `infra/`.
- 1:1 Test Parity: Every source module has a corresponding unit test.
- Side-effect free assertions in all test suites.
- Rule definitions live in `.agents/rules/{self.project_slug}-invariants.md`.
"""
        gemini_content = f"""# AI Coding Assistant Protocol & Architectural Guardrails

> Primary local memory context for AI coding assistants (Antigravity CLI, Gemini, Claude, Cursor).

## Invariants & Rules
See [AGENTS.md](AGENTS.md) and [.agents/rules/{self.project_slug}-invariants.md](.agents/rules/{self.project_slug}-invariants.md).

## Commands
- `uv run hexaqual sanity`: Full pre-commit quality check (Ruff, Ty, complexipy, test parity, __all__).
- `uv run pytest`: Run unit and architecture test suites with coverage.
"""
        self._write_file(
            f".agents/rules/{self.project_slug}-invariants.md", rules_content
        )
        self._write_file("AGENTS.md", agents_content)
        self._write_file("GEMINI.md", gemini_content)

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
    # Test Suite (1:1 Symmetry, Parity & Boundaries)
    # ----------------------------------------------------------------------

    def _write_test_suite(self) -> None:
        self._write_file("tests/__init__.py", "")
        self._write_file(
            "tests/conftest.py", templates.render_test_conftest(self.package_name)
        )
        self._write_file("tests/architecture/__init__.py", "")
        self._write_file(
            "tests/architecture/test_hexagonal_boundaries.py",
            templates.render_test_architecture(self.package_name),
        )
        self._write_file("tests/hypothesis/__init__.py", "")
        self._write_file(
            "tests/hypothesis/test_domain_fuzz.py",
            templates.render_test_domain_fuzz(self.package_name),
        )

        # 1:1 Unit test parity
        self._write_file("tests/unit/__init__.py", "")
        self._write_file(
            "tests/unit/test___init__.py",
            templates.render_test_root_init(self.package_name),
        )

        # Domain unit tests
        self._write_file("tests/unit/domain/__init__.py", "")
        self._write_file(
            "tests/unit/domain/test___init__.py",
            templates.render_test_subpackage_init(self.package_name, "domain"),
        )
        self._write_file(
            "tests/unit/domain/test_models.py",
            templates.render_test_domain_models(self.package_name),
        )
        self._write_file(
            "tests/unit/domain/test_commands.py",
            templates.render_test_domain_commands(self.package_name),
        )

        # Ports unit tests
        self._write_file("tests/unit/ports/__init__.py", "")
        self._write_file(
            "tests/unit/ports/test___init__.py",
            templates.render_test_subpackage_init(self.package_name, "ports"),
        )
        self._write_file(
            "tests/unit/ports/test_repositories.py",
            templates.render_test_ports_repositories(self.package_name),
        )

        # Adapters unit tests
        self._write_file("tests/unit/adapters/__init__.py", "")
        self._write_file(
            "tests/unit/adapters/test___init__.py",
            templates.render_test_subpackage_init(self.package_name, "adapters"),
        )

        # Adapters driven
        self._write_file("tests/unit/adapters/driven/__init__.py", "")
        self._write_file(
            "tests/unit/adapters/driven/test___init__.py",
            templates.render_test_subpackage_init(self.package_name, "adapters.driven"),
        )
        self._write_file(
            "tests/unit/adapters/driven/test_database.py",
            templates.render_test_adapters_database(self.package_name),
        )

        # Adapters driving
        self._write_file("tests/unit/adapters/driving/__init__.py", "")
        self._write_file(
            "tests/unit/adapters/driving/test___init__.py",
            templates.render_test_subpackage_init(
                self.package_name, "adapters.driving"
            ),
        )
        self._write_file(
            "tests/unit/adapters/driving/test_cli.py",
            templates.render_test_adapters_cli(self.package_name),
        )

        if (
            self.config.template in ("web-api", "enterprise", "graphql-service")
            or self.config.include_graphql
        ):
            self._write_file(
                "tests/unit/adapters/driving/test_http.py",
                templates.render_test_adapters_http(self.package_name),
            )

        if (
            self.config.template in ("grpc-service", "enterprise")
            or self.config.include_grpc
        ):
            self._write_file(
                "tests/unit/adapters/driving/test_grpc.py",
                templates.render_test_adapters_grpc(self.package_name),
            )

        if (
            self.config.template in ("graphql-service", "enterprise")
            or self.config.include_graphql
        ):
            self._write_file(
                "tests/unit/adapters/driving/test_graphql.py",
                templates.render_test_adapters_graphql(self.package_name),
            )

        if (
            self.config.template in ("mcp-agent", "enterprise")
            or self.config.include_mcp
        ):
            self._write_file(
                "tests/unit/adapters/driving/test_mcp.py",
                templates.render_test_adapters_mcp(self.package_name),
            )

        # Infra unit tests
        self._write_file("tests/unit/infra/__init__.py", "")
        self._write_file(
            "tests/unit/infra/test___init__.py",
            templates.render_test_subpackage_init(self.package_name, "infra"),
        )
        self._write_file(
            "tests/unit/infra/test_config.py",
            templates.render_test_infra_config(self.package_name),
        )
        self._write_file(
            "tests/unit/infra/test_handlers.py",
            templates.render_test_infra_handlers(self.package_name),
        )
        self._write_file(
            "tests/unit/infra/test_bootstrap.py",
            templates.render_test_infra_bootstrap(self.package_name),
        )


def scaffold_project(
    name: str,
    template: str = "web-api",
    description: str = "A modern microservice powered by Hexastack.",
    db_type: str = "in-memory",
    include_events: bool = False,
    include_mcp: bool = False,
    include_grpc: bool = False,
    include_graphql: bool = False,
    include_release: bool = False,
    include_openssf: bool = False,
    include_qual: bool = True,
    include_agents: bool = True,
    include_mutation: bool = True,
    include_sentry: bool = False,
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
        include_qual=include_qual,
        include_agents=include_agents,
        include_mutation=include_mutation,
        include_sentry=include_sentry,
    )
    scaffolder = ProjectScaffolder(config, output_dir=output_dir)
    return scaffolder.generate()


__all__ = [
    "ProjectScaffolder",
    "scaffold_project",
]
