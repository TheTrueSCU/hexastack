"""Configuration template renderers (pyproject.toml, .importlinter, .pre-commit, Dockerfile, README)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hexastack.application.scaffolding.generator import ScaffoldConfig


def render_dockerfile(config: ScaffoldConfig) -> str:
    return f"""# Multi-stage ultra-fast uv Dockerfile
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Install dependencies in isolated layer
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy application source and build final virtualenv
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Final rootless production runtime stage
FROM python:3.13-slim-bookworm AS runtime

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1

# Create non-root system user
RUN groupadd -r -g 10001 appuser && \
    useradd -r -u 10001 -g appuser -d /app -s /sbin/nologin appuser

# Copy virtualenv and application from builder
COPY --from=builder --chown=appuser:appuser /app /app

USER appuser:appuser
EXPOSE 8000 50051

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["{config.name}"]
CMD ["dev"]
"""


def render_dockerignore() -> str:
    return """.git
.gitignore
.venv
.pytest_cache
.coverage
.mutmut-cache
.secrets.baseline
htmlcov
dist
build
tests
docs
__pycache__
*.pyc
"""


def render_pyproject_toml(config: ScaffoldConfig, package_name: str) -> str:
    if config.template in ("web-api", "enterprise"):
        extras = "[fastapi,db,ui]"
    elif config.template == "grpc-service" or config.include_grpc:
        extras = "[grpc,db,cli]"
    elif config.template == "graphql-service" or config.include_graphql:
        extras = "[graphql,fastapi,db,cli]"
    elif config.template == "mcp-agent" or config.include_mcp:
        extras = "[mcp,ai,cli]"
    elif config.template == "event-driven" or config.include_events:
        extras = "[events,cli]"
    else:
        extras = "[cli]"

    return f"""[project]
name = "{config.name}"
version = "0.1.0"
description = "{config.description}"
readme = "README.md"
requires-python = "{config.python_version}"
dependencies = [
    "hexastack{extras}>=0.1.0",
]

[project.scripts]
{config.name} = "{package_name}.adapters.driving.cli:main"

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


def render_importlinter(package_name: str) -> str:
    return f"""[importlinter]
root_package = {package_name}
include_type_checking = False

# 1. Strict Dependency Inversion: Infra -> Adapters -> Ports -> Domain
[importlinter:contract:hexagonal-layers]
name = Hexagonal Architecture Layers
type = layers
containers =
    {package_name}
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
    {package_name}.domain
forbidden_modules =
    {package_name}.adapters
    {package_name}.infra
    {package_name}.ports

# 3. Adapter Independence: Driving and Driven adapters communicate exclusively via Ports
[importlinter:contract:adapter-independence]
name = Adapter Independence
type = independence
modules =
    {package_name}.adapters.driving
    {package_name}.adapters.driven
"""


def render_precommit() -> str:
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

  - repo: local
    hooks:
      - id: ruff-format
        name: ruff format
        entry: uv run ruff format
        language: system
        types: [python]

      - id: ruff-lint
        name: ruff check
        entry: uv run ruff check --fix
        language: system
        types: [python]

      - id: ty
        name: ty (type checker)
        entry: uv run ty check
        language: system
        types: [python]
        pass_filenames: false

      - id: import-linter
        name: import-linter (hexagonal boundaries)
        entry: uv run lint-imports
        language: system
        types: [python]
        pass_filenames: false

      - id: complexipy
        name: complexipy (cyclomatic complexity)
        entry: uv run complexipy src/
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


def render_readme(config: ScaffoldConfig, package_name: str) -> str:
    return f"""# {config.name}

> {config.description}

Scaffolded with **[Hexastack](https://github.com/TheTrueSCU/hexastack)** — The Hexagonal Architecture Framework for Python.

## Architecture

This project enforces clean **Ports & Adapters (Hexagonal Architecture)**:

```text
src/{package_name}/
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

# 2. Run test suite & coverage
uv run pytest

# 3. Launch interactive development environment
uv run {config.name} dev
```
"""
