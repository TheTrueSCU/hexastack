"""Configuration template renderers (pyproject.toml, .importlinter, .pre-commit, Dockerfile, README)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hexastack.application.scaffolding.models import ScaffoldConfig


def render_dockerfile(config: ScaffoldConfig) -> str:
    return f"""# Multi-stage ultra-fast uv Dockerfile
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Install dependencies in isolated layer
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --no-install-project --no-dev

# Copy application source and build final virtualenv
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev

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
    extras_list: list[str] = []
    if config.template in ("web-api", "enterprise"):
        extras_list.extend(["fastapi", "db", "ui", "cli"])
    elif config.template == "grpc-service" or config.include_grpc:
        extras_list.extend(["grpc", "db", "cli"])
    elif config.template == "graphql-service" or config.include_graphql:
        extras_list.extend(["graphql", "fastapi", "db", "cli"])
    elif config.template == "mcp-agent" or config.include_mcp:
        extras_list.extend(["mcp", "ai", "cli"])
    elif config.template == "event-driven" or config.include_events:
        extras_list.extend(["events", "cli"])
    else:
        extras_list.append("cli")

    if config.include_qual and "qual" not in extras_list:
        extras_list.append("qual")
    if config.include_sentry and "sentry" not in extras_list:
        extras_list.append("sentry")

    extras_str = "[" + ",".join(sorted(set(extras_list))) + "]"

    mutation_config = ""
    if config.include_mutation:
        mutation_config = """
[tool.pytest-gremlins]
paths = ["src"]
operators = ["arithmetic", "boolean", "boundary", "comparison", "return"]
workers = "auto"
batch_size = 10
cache = true
"""

    return f"""[project]
name = "{config.name}"
version = "0.1.0"
description = "{config.description}"
readme = "README.md"
requires-python = "{config.python_version}"
dependencies = [
    "hexastack{extras_str}>=0.8.0",
    "pydantic-settings>=2.0.0",
]

[project.scripts]
{config.name} = "{package_name}.adapters.driving.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[dependency-groups]
dev = [
    "hexaqual[all]>=0.9.0",
    "hypothesis>=6.168.3",
    "pre-commit>=4.6.2",
    "pytest-cov>=7.1.0",
    "pytest-xdist>=3.8.0",
    "ruff>=0.16.9",
    "ty>=0.0.84",
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

[tool.ruff.lint.per-file-ignores]
"**/tests/**/*.py" = ["ARG", "D", "E501", "S101", "S105"]
{mutation_config}"""


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

  - repo: https://github.com/TheTrueSCU/hexaqual
    rev: v0.9.0
    hooks:
      - id: hexaqual-sanity
      - id: hexaqual-architecture
      - id: hexaqual-agents
"""


def render_gitignore() -> str:
    return """# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# Caches and Environments
.venv/
env/
venv/
.cache/
.pytest_cache/
.ruff_cache/
.mypy_cache/
.ty_cache/
.hypothesis/
.complexipy_cache/
.hexaflow/
.import_linter_cache/
.ropeproject/

# Test & Coverage
.coverage
.coverage.*
htmlcov/
nosetests.xml
coverage.xml
junit.xml
*.xml
*.cover

# Build & Packaging
build/
dist/
*.egg-info/
*.egg
.eggs/

# Database files & Local State
*.db*
*.sqlite
*.sqlite3
logs/
*.log

# OS Specific
.DS_Store
Thumbs.db

# Hexaqual managed agent assets (materialized via hexaqual agents sync)
.agents/rules/hexaqual-*
.agents/workflows/hexaqual-*
.agents/skills/hexaqual_*
"""


def render_secrets_baseline() -> str:
    return """{
  "version": "1.5.0",
  "plugins_used": [
    {
      "name": "ArtifactoryDetector"
    },
    {
      "name": "AWSKeyDetector"
    },
    {
      "name": "AzureStorageKeyDetector"
    },
    {
      "name": "Base64HighEntropyString",
      "limit": 4.5
    },
    {
      "name": "BasicAuthDetector"
    },
    {
      "name": "CloudantDetector"
    },
    {
      "name": "DiscordBotTokenDetector"
    },
    {
      "name": "GitHubTokenDetector"
    },
    {
      "name": "GitLabTokenDetector"
    },
    {
      "name": "HexHighEntropyString",
      "limit": 3.0
    },
    {
      "name": "IbmCloudIamDetector"
    },
    {
      "name": "IbmCosHmacDetector"
    },
    {
      "name": "IPPublicDetector"
    },
    {
      "name": "JwtTokenDetector"
    },
    {
      "name": "KeywordDetector",
      "keyword_exclude": ""
    },
    {
      "name": "MailchimpDetector"
    },
    {
      "name": "NpmDetector"
    },
    {
      "name": "OpenAIDetector"
    },
    {
      "name": "PrivateKeyDetector"
    },
    {
      "name": "PypiTokenDetector"
    },
    {
      "name": "SendGridDetector"
    },
    {
      "name": "SlackDetector"
    },
    {
      "name": "SoftlayerDetector"
    },
    {
      "name": "SquareOAuthDetector"
    },
    {
      "name": "StripeDetector"
    },
    {
      "name": "TelegramBotTokenDetector"
    },
    {
      "name": "TwilioKeyDetector"
    }
  ],
  "filters_used": [
    {
      "path": "detect_secrets.filters.allowlist.is_line_allowlisted"
    },
    {
      "path": "detect_secrets.filters.common.is_baseline_file",
      "filename": ".secrets.baseline"
    },
    {
      "path": "detect_secrets.filters.common.is_ignored_due_to_verification_policies",
      "min_level": 2
    },
    {
      "path": "detect_secrets.filters.heuristic.is_indirect_reference"
    },
    {
      "path": "detect_secrets.filters.heuristic.is_likely_id_string"
    },
    {
      "path": "detect_secrets.filters.heuristic.is_lock_file"
    },
    {
      "path": "detect_secrets.filters.heuristic.is_not_alphanumeric_string"
    },
    {
      "path": "detect_secrets.filters.heuristic.is_potential_uuid"
    },
    {
      "path": "detect_secrets.filters.heuristic.is_prefixed_with_dollar_sign"
    },
    {
      "path": "detect_secrets.filters.heuristic.is_sequential_string"
    },
    {
      "path": "detect_secrets.filters.heuristic.is_swagger_file"
    },
    {
      "path": "detect_secrets.filters.heuristic.is_templated_secret"
    }
  ],
  "results": {}
}
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
