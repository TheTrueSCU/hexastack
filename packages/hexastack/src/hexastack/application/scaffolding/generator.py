"""Hexagonal project scaffolding generator decomposed by architectural layers and template types.

Notes/Architectural Intent:
    Generates standardized microservices adhering strictly to Hexagonal Architecture,
    including .importlinter contracts, tiered CI workflows, and a golden-path working sample.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

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
        self._write_file("pyproject.toml", self._render_pyproject_toml())
        self._write_file(".importlinter", self._render_importlinter())
        self._write_file(".pre-commit-config.yaml", self._render_precommit())
        self._write_file(".github/workflows/ci.yml", self._render_github_ci())
        self._write_file("README.md", self._render_readme())

    def _render_pyproject_toml(self) -> str:
        if self.config.template in ("web-api", "enterprise"):
            extras = "[fastapi,db,ui]"
        elif self.config.template == "grpc-service" or self.config.include_grpc:
            extras = "[grpc,db,cli]"
        elif self.config.template == "graphql-service" or self.config.include_graphql:
            extras = "[graphql,fastapi,db,cli]"
        elif self.config.template == "mcp-agent" or self.config.include_mcp:
            extras = "[mcp,ai,cli]"
        elif self.config.template == "event-driven" or self.config.include_events:
            extras = "[events,cli]"
        else:
            extras = "[cli]"
        return f"""[project]
name = "{self.config.name}"
version = "0.1.0"
description = "{self.config.description}"
readme = "README.md"
requires-python = "{self.config.python_version}"
dependencies = [
    "hexastack{extras}>=0.1.0",
]

[project.scripts]
{self.config.name} = "{self.package_name}.adapters.driving.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[dependency-groups]
dev = [
    "complexipy>=7.0.1",
    "detect-secrets>=1.5.0",
    "faker>=33.0.0",
    "hypothesis>=6.100.0",
    "import-linter>=2.13",
    "locust>=2.31.0",
    "memray>=1.13.0",
    "pip-audit>=2.8.0",
    "pre-commit>=3.8.0",
    "py-spy>=0.3.14",
    "pytest>=8.0.0",
    "pytest-cov>=5.0.0",
    "pytest-randomly>=4.1.0",
    "pytest-xdist>=3.8.0",
    "ruff>=0.16.2",
    "ty>=0.0.69",
    "vulture>=2.11",
]

[tool.complexipy]
max_complexity_allowed = 25

[tool.coverage.run]
source = ["src/"]
omit = ["*/tests/*"]

[tool.coverage.report]
fail_under = 90
show_missing = true

[tool.pytest.ini_options]
addopts = "-n auto --import-mode=importlib --cov=src --cov-fail-under=90 --cov-report=term-missing"

[tool.ruff.lint]
select = ["B", "D", "E", "F", "I", "S", "SIM", "UP", "W"]
ignore = ["D100", "D104", "D107", "E501"]

[tool.ruff.lint.pydocstyle]
convention = "google"
"""

    def _render_importlinter(self) -> str:
        return f"""[importlinter]
root_package = {self.package_name}
include_type_checking = False

# 1. Strict Dependency Inversion: Infra -> Adapters -> Ports -> Domain
[importlinter:contract:hexagonal-layers]
name = Hexagonal Architecture Layers
type = layers
containers =
    {self.package_name}
layers =
    infra
    adapters
    ports
    domain

# 2. Pure Python Core: Domain cannot import outer framework layers
[importlinter:contract:domain-purity]
name = Domain Purity Guarantee
type = forbidden
source_modules =
    {self.package_name}.domain
forbidden_modules =
    {self.package_name}.adapters
    {self.package_name}.infra
    {self.package_name}.ports

# 3. Adapter Independence: Driving and Driven adapters communicate exclusively via Ports
[importlinter:contract:adapter-independence]
name = Adapter Independence
type = independence
modules =
    {self.package_name}.adapters.driving
    {self.package_name}.adapters.driven
"""

    def _render_precommit(self) -> str:
        return r"""repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml

  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
        exclude: ^(\.venv|docs|_build)/

  - repo: https://github.com/bufbuild/buf
    rev: v1.34.0
    hooks:
      - id: buf-lint
        files: ^.*\.proto$

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: local
    hooks:
      - id: import-linter
        name: import-linter (hexagonal boundaries)
        entry: uv run lint-imports
        language: system
        pass_filenames: false

      - id: ty-check
        name: ty check (static type check)
        entry: uv run ty check
        language: system
        types: [python]
        pass_filenames: false

      - id: vulture
        name: vulture (dead code detector)
        entry: uv run vulture
        language: system
        files: ^src/.*\.py$
        pass_filenames: false

      - id: pip-audit
        name: pip-audit (dependency vulnerability scan)
        entry: uv run pip-audit --local
        language: system
        pass_filenames: false
"""

    def _render_github_ci(self) -> str:
        return """name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  check:
    name: Fast Check (Lint, Types, Unit Tests)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
      - run: uv run pre-commit run --all-files
      - run: uv run pytest tests/unit

  fuzz:
    name: Property & Integration Tests
    needs: check
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv run pytest tests/hypothesis tests/integration
"""

    def _render_readme(self) -> str:
        return f"""# {self.config.name}

> {self.config.description}

Scaffolded with **[Hexastack](https://github.com/TheTrueSCU/hexastack)** — The Hexagonal Architecture Framework for Python.

## Architecture

This project enforces clean **Ports & Adapters (Hexagonal Architecture)**:

```text
src/{self.package_name}/
├── domain/                      # 100% Pure Python Entities, Value Objects & CQRS Messages
│   ├── models.py
│   └── commands.py
├── ports/                       # Inverted Interfaces (Abstract Repositories & Gateways)
│   └── repositories.py
├── adapters/
│   ├── driving/                 # INBOUND Adapters (HTTP REST, CLI, UI)
│   │   ├── cli.py
│   │   └── http.py
│   └── driven/                  # OUTBOUND Adapters (Database, Outbox, External APIs)
│       └── database.py
└── infra/                       # Kernel, Bootstrapper & Dependency Injection
    ├── bootstrap.py
    └── config.py
```

## Getting Started

```bash
# 1. Install dependencies & pre-commit hooks
uv sync
uv run pre-commit install

# 2. Run all tests & coverage checks
uv run pytest

# 3. Launch DevTools & API Server
uv run {self.config.name} serve
```
"""

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
            '"""Pure domain models, CQRS messages, and business logic."""\n'
            "from .commands import CreateItemCommand, ItemCreatedResponse\n"
            "from .models import Item\n\n"
            '__all__ = ["CreateItemCommand", "Item", "ItemCreatedResponse"]\n',
        )
        self._write_file(
            f"src/{self.package_name}/domain/models.py", self._render_domain_models()
        )
        self._write_file(
            f"src/{self.package_name}/domain/commands.py",
            self._render_domain_commands(),
        )

    def _render_domain_models(self) -> str:
        return """\"\"\"Domain entities and value objects.\"\"\"

from dataclasses import dataclass, field
import uuid


@dataclass
class Item:
    \"\"\"Domain entity representing a managed item.\"\"\"

    title: str
    description: str = ''
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    completed: bool = False
"""

    def _render_domain_commands(self) -> str:
        return """\"\"\"CQRS command and query contracts.\"\"\"

from hexastack_core.domain import Command
from pydantic import BaseModel


class CreateItemCommand(Command):
    \"\"\"Command to create a new domain item.\"\"\"

    title: str
    description: str = ''


class ItemCreatedResponse(BaseModel):
    \"\"\"Result returned after item creation.\"\"\"

    id: str
    title: str
"""

    # ----------------------------------------------------------------------
    # Ports Layer (Abstract Interfaces)
    # ----------------------------------------------------------------------

    def _write_ports_layer(self) -> None:
        self._write_file(
            f"src/{self.package_name}/ports/__init__.py",
            '"""Secondary abstract port interfaces."""\n'
            "from .repositories import ItemRepositoryPort\n\n"
            '__all__ = ["ItemRepositoryPort"]\n',
        )
        self._write_file(
            f"src/{self.package_name}/ports/repositories.py",
            f"""\"\"\"Abstract storage repository ports.\"\"\"

from abc import ABC, abstractmethod
from typing import Optional
from {self.package_name}.domain.models import Item


class ItemRepositoryPort(ABC):
    \"\"\"Abstract repository port for persisting Item entities.\"\"\"

    @abstractmethod
    def save(self, item: Item) -> None:
        \"\"\"Persist an item.\"\"\"
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, item_id: str) -> Optional[Item]:
        \"\"\"Retrieve an item by identifier.\"\"\"
        raise NotImplementedError
""",
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
            f"""\"\"\"In-memory and persistent database adapters.\"\"\"

from typing import Optional
from {self.package_name}.domain.models import Item
from {self.package_name}.ports.repositories import ItemRepositoryPort


class InMemoryItemRepository(ItemRepositoryPort):
    \"\"\"In-memory repository adapter for local development and unit tests.\"\"\"

    def __init__(self) -> None:
        self._storage: dict[str, Item] = {{}}

    def save(self, item: Item) -> None:
        self._storage[item.id] = item

    def get_by_id(self, item_id: str) -> Optional[Item]:
        return self._storage.get(item_id)
""",
        )
        self._write_file(
            f"src/{self.package_name}/adapters/driving/__init__.py",
            '"""Driving presentation adapters."""\n',
        )
        self._write_file(
            f"src/{self.package_name}/adapters/driving/cli.py",
            f"""\"\"\"Typer CLI entrypoint and driving command adapters.\"\"\"

import sys
import typer
from hexastack_cli.infra.decorators import cli_command
from {self.package_name}.domain.commands import CreateItemCommand

cli_command("create-item", help="Create a new Item in the system.")(CreateItemCommand)

def main() -> None:
    \"\"\"CLI entrypoint.\"\"\"
    from {self.package_name}.infra.bootstrap import create_app
    app = create_app()
    cli_app = app.get("cli_app")
    if cli_app is not None:
        cli_app()
    else:
        sys.stderr.write("CLI application failed to bootstrap.\\n")
        sys.exit(1)
""",
        )

        if (
            self.config.template in ("web-api", "enterprise", "graphql-service")
            or self.config.include_graphql
        ):
            self._write_file(
                f"src/{self.package_name}/adapters/driving/http.py",
                f"""\"\"\"FastAPI REST routing adapters.\"\"\"

from hexastack_fastapi.infra.decorators import api_command
from {self.package_name}.domain.commands import CreateItemCommand

api_command("/items", method="POST", summary="Create a new Item")(CreateItemCommand)
""",
            )

        if self.config.template == "grpc-service" or self.config.include_grpc:
            self._write_file(
                f"src/{self.package_name}/adapters/driving/grpc.py",
                f"""\"\"\"High-performance gRPC driving adapter with inline @proto_schema contract.\"\"\"

from dataclasses import dataclass
from hexastack_grpc.infra.decorators import proto_schema
from {self.package_name}.domain.commands import CreateItemCommand


@proto_schema(
    schema=\"\"\"
    syntax = "proto3";
    package {self.package_name}.v1;

    message CreateItemRequest {{
        string title = 1;
        string description = 2;
    }}

    message CreateItemResponse {{
        string id = 1;
        string title = 2;
    }}

    service ItemService {{
        rpc CreateItem (CreateItemRequest) returns (CreateItemResponse);
    }}
    \"\"\",
    message_name="CreateItemRequest",
    service_name="{self.package_name}.v1.ItemService",
    rpc_name="CreateItem",
)
@dataclass
class CreateItemRpcCommand(CreateItemCommand):
    \"\"\"gRPC Inbound Command contract.\"\"\"
""",
            )
            self._write_file(
                "buf.yaml",
                """version: v2
modules:
  - path: protos
lint:
  use:
    - DEFAULT
breaking:
  use:
    - FILE
""",
            )
            self._write_file(
                f"protos/{self.package_name}/v1/item.proto",
                f"""syntax = "proto3";

package {self.package_name}.v1;

message CreateItemRequest {{
  string title = 1;
  string description = 2;
}}

message CreateItemResponse {{
  string id = 1;
  string title = 2;
}}

service ItemService {{
  rpc CreateItem(CreateItemRequest) returns (CreateItemResponse);
}}
""",
            )

        if self.config.template == "graphql-service" or self.config.include_graphql:
            self._write_file(
                f"src/{self.package_name}/adapters/driving/graphql.py",
                f"""\"\"\"Strawberry GraphQL driving schema and query/mutation resolvers.\"\"\"

import strawberry
from hexastack_cqrs.ports.buses import CommandBusPort
from {self.package_name}.domain.commands import CreateItemCommand


@strawberry.type
class ItemGqlType:
    id: str
    title: str


@strawberry.type
class Query:
    @strawberry.field
    def health(self) -> str:
        return "OK"


@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_item(self, info: strawberry.Info, title: str, description: str = "") -> ItemGqlType:
        bus = info.context["command_bus"]
        cmd = CreateItemCommand(title=title, description=description)
        result = bus.dispatch(cmd)
        return ItemGqlType(id=result.id, title=result.title)


schema = strawberry.Schema(query=Query, mutation=Mutation)
""",
            )

        if self.config.template == "mcp-agent" or self.config.include_mcp:
            self._write_file(
                f"src/{self.package_name}/adapters/driving/mcp.py",
                f"""\"\"\"Model Context Protocol (MCP) tool exposure for Gemini, Antigravity, and Claude.\"\"\"

from hexastack_mcp.infra.decorators import mcp_tool
from {self.package_name}.domain.commands import CreateItemCommand

# Expose CreateItemCommand as an MCP tool for AI agents
mcp_tool(
    name="create_item",
    description="Create a new Item in the system with title and description",
    kind="command",
)(CreateItemCommand)
""",
            )
            self._write_file(
                "mcp.json",
                f"""{{
  "mcpServers": {{
    "{self.config.name}": {{
      "command": "uv",
      "args": ["run", "{self.config.name}", "mcp", "run"],
      "env": {{
        "HEXASTACK_AI__PROVIDER": "gemini",
        "PYTHONUNBUFFERED": "1"
      }}
    }}
  }}
}}
""",
            )

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
            f"""\"\"\"Application settings and environment configuration.\"\"\"

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    \"\"\"Service environment settings.\"\"\"

    model_config = SettingsConfigDict(env_prefix='APP_', extra='ignore')

    service_name: str = '{self.config.name}'
    environment: str = 'development'
""",
        )
        self._write_file(
            f"src/{self.package_name}/infra/handlers.py",
            f"""\"\"\"Application CQRS command and query handlers.\"\"\"

from {self.package_name}.domain.commands import CreateItemCommand, ItemCreatedResponse
from {self.package_name}.domain.models import Item
from {self.package_name}.ports.repositories import ItemRepositoryPort


def handle_create_item(cmd: CreateItemCommand, repo: ItemRepositoryPort) -> ItemCreatedResponse:
    \"\"\"Handler processing CreateItemCommand.\"\"\"
    item = Item(title=cmd.title, description=cmd.description)
    repo.save(item)
    return ItemCreatedResponse(id=item.id, title=item.title)
""",
        )

        scan_packages = [f"{self.package_name}.adapters.driving.cli"]
        extra_imports = []

        if (
            self.config.template in ("web-api", "enterprise", "graphql-service")
            or self.config.include_graphql
        ):
            scan_packages.append(f"{self.package_name}.adapters.driving.http")
            extra_imports.append(f"import {self.package_name}.adapters.driving.http")
        if self.config.template == "grpc-service" or self.config.include_grpc:
            scan_packages.append(f"{self.package_name}.adapters.driving.grpc")
            extra_imports.append(f"import {self.package_name}.adapters.driving.grpc")
        if self.config.template == "graphql-service" or self.config.include_graphql:
            scan_packages.append(f"{self.package_name}.adapters.driving.graphql")
            extra_imports.append(f"import {self.package_name}.adapters.driving.graphql")
        if self.config.template == "mcp-agent" or self.config.include_mcp:
            scan_packages.append(f"{self.package_name}.adapters.driving.mcp")
            extra_imports.append(f"import {self.package_name}.adapters.driving.mcp")

        packages_list_str = ",\n            ".join(scan_packages)
        extra_imports_str = "\n".join(extra_imports)

        self._write_file(
            f"src/{self.package_name}/infra/bootstrap.py",
            f"""\"\"\"Hexastack bootstrapper and application assembly.\"\"\"

from typing import Any
from hexastack_core.infra.bootstrap import bootstrap
from hexastack_cqrs.infra.decorators import command_handler
import {self.package_name}.adapters.driving.cli
{extra_imports_str}
from {self.package_name}.adapters.driven.database import InMemoryItemRepository
from {self.package_name}.domain.commands import CreateItemCommand
from {self.package_name}.infra.handlers import handle_create_item
from {self.package_name}.ports.repositories import ItemRepositoryPort

# Bind command handler
command_handler(CreateItemCommand)(handle_create_item)


def create_app() -> Any:
    \"\"\"Bootstrap full Hexastack microservice kernel.\"\"\"
    result = bootstrap(
        packages_to_scan=[
            {packages_list_str},
        ],
    )
    repo = InMemoryItemRepository()
    result.container.add_instance(repo, declared_class=ItemRepositoryPort)
    return result
""",
        )

    # ----------------------------------------------------------------------
    # Test Suite
    # ----------------------------------------------------------------------

    def _write_test_suite(self) -> None:
        self._write_file("tests/__init__.py", "")
        self._write_file(
            "tests/conftest.py",
            f"""\"\"\"Shared pytest fixtures.\"\"\"

import pytest
from {self.package_name}.adapters.driven.database import InMemoryItemRepository


@pytest.fixture
def item_repo():
    return InMemoryItemRepository()
""",
        )
        self._write_file(
            "tests/unit/test_domain.py",
            f"""\"\"\"Unit tests verifying pure domain models and handlers.\"\"\"

from {self.package_name}.domain.commands import CreateItemCommand
from {self.package_name}.domain.models import Item
from {self.package_name}.infra.handlers import handle_create_item


def test_item_entity_creation():
    item = Item(title="Buy Milk")
    assert item.title == "Buy Milk"
    assert not item.completed
    assert item.id is not None


def test_handle_create_item(item_repo):
    cmd = CreateItemCommand(title="Ship Release", description="v1.0")
    res = handle_create_item(cmd, repo=item_repo)
    assert res.title == "Ship Release"
    saved = item_repo.get_by_id(res.id)
    assert saved is not None
    assert saved.description == "v1.0"
""",
        )
        self._write_file(
            "tests/hypothesis/test_domain_fuzz.py",
            f"""\"\"\"Property-based fuzzing tests for domain entities.\"\"\"

from hypothesis import given, strategies as st
from {self.package_name}.domain.models import Item


@given(title=st.text(min_size=1), description=st.text())
def test_item_property_invariants(title: str, description: str):
    item = Item(title=title, description=description)
    assert item.title == title
    assert item.description == description
    assert len(item.id) > 0
""",
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
    )
    scaffolder = ProjectScaffolder(config, output_dir=output_dir)
    return scaffolder.generate()
