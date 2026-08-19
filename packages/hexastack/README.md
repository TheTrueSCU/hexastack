# hexastack

> The unified distribution package and diagnostic CLI for the Hexastack framework.

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)

---

## 1. Overview & Capabilities

`hexastack` acts as the umbrella distribution for the entire Hexastack monorepo, offering:

- **Scoped Extras**: Single-command installs for scoped use cases (e.g., `pip install hexastack[cli]`, `pip install hexastack[web]`, `pip install hexastack[graphql]`, `pip install hexastack[mcp]`, `pip install hexastack[grpc]`, `pip install hexastack[db]`).
- **Interactive Diagnostic CLI**: The `hexastack` terminal command provides system health checks, package inspection, CQRS message route exploration, local FastAPI dev server launching, MCP server execution, gRPC daemon hosting, and Alembic database migration management.

---

## 2. Monorepo & Sibling Relationships

```mermaid
graph TD
    subgraph Umbrella ["hexastack (Distribution & CLI App)"]
        CLI_APP["hexastack CLI Entrypoint"]
        DIAG["Diagnostics Handlers (info, inspect, ping)"]
        DEMO_SERVER["FastAPI Demo Server (serve)"]
        DB_CLI["Alembic Migration Tooling (db)"]
        MCP_CLI["MCP Server Runner (mcp)"]
        GRPC_CLI["gRPC Server Daemon (grpc)"]
    end

    subgraph BaseDependencies ["Default Direct Dependencies"]
        CORE["hexastack-core"]
        CQRS["hexastack-cqrs"]
        LOG["hexastack-logging"]
    end

    subgraph ScopedExtras ["Optional Scoped Extras"]
        AUTH["hexastack-auth (hexastack[auth])"]
        OTEL["hexastack-otel (hexastack[otel])"]
        EVENTS["hexastack-events (hexastack[events])"]
        AI["hexastack-ai (hexastack[ai])"]
        CLI["hexastack-cli (hexastack[cli])"]
        FASTAPI["hexastack-fastapi (hexastack[fastapi])"]
        GRAPHQL["hexastack-graphql (hexastack[graphql])"]
        MCP["hexastack-mcp (hexastack[mcp])"]
        GRPC["hexastack-grpc (hexastack[grpc])"]
        DB["hexastack-db (hexastack[db])"]
        UVICORN["uvicorn[standard] (hexastack[web])"]
    end

    Umbrella --> CORE
    Umbrella --> CQRS
    Umbrella --> LOG

    CLI_APP -. optional extra .-> CLI
    DEMO_SERVER -. optional extra .-> FASTAPI
    DEMO_SERVER -. optional extra .-> UVICORN
    DB_CLI -. optional extra .-> DB
    MCP_CLI -. optional extra .-> MCP
    GRPC_CLI -. optional extra .-> GRPC
```

### Explicit Dependencies (Direct)
- `hexastack-core`: Core kernel, DI container (`rodi`), and bootstrap engine.
- `hexastack-cqrs`: Command, query, and event execution buses.
- `hexastack-logging`: Structured logging and telemetry.

### Optional Integrations (Extras)
- `[auth]`: Installs `hexastack-auth` for security, RBAC, JWT, PBKDF2, and `@authorize` middleware.
- `[otel]`: Installs `hexastack-otel` for OpenTelemetry distributed tracing and OTLP export.
- `[events]`: Installs `hexastack-events` for CloudEvents 1.0, Transactional Outbox, and streaming buses.
- `[ai]`: Installs `hexastack-ai` for LiteLLM, Instructor, PydanticAI, and reflective agent tools.
- `[cli]`: Installs `hexastack-cli` for interactive CLI commands.
- `[db]` / `[sql]`: Installs `hexastack-db` for persistence and Alembic migrations.
- `[fastapi]`: Installs `hexastack-fastapi`.
- `[graphql]`: Installs `hexastack-graphql`.
- `[mcp]`: Installs `hexastack-mcp` for Model Context Protocol AI agent tools.
- `[grpc]`: Installs `hexastack-grpc` for high-performance RPC services.
- `[web]`: Installs `hexastack-fastapi` and `uvicorn[standard]`.
- `[testing]`: Installs recommended testing tools (`hypothesis`, `inline-snapshot`, `pytest-archon`, `schemathesis`).
- `[all]`: Complete installation with all adapters and development tools.

---

## 3. Installation

```bash
# Minimal installation
pip install hexastack

# Testing toolkit (Archon boundary checks, Hypothesis fuzzing, Schemathesis)
pip install "hexastack[testing]"

# Security & RBAC
pip install "hexastack[auth]"

# OpenTelemetry Tracing
pip install "hexastack[otel]"

# CloudEvents & Transactional Outbox
pip install "hexastack[events]"

# AI Integration (LiteLLM, Instructor, PydanticAI)
pip install "hexastack[ai]"

# CLI support
pip install "hexastack[cli]"

# Full web stack (FastAPI + Uvicorn)
pip install "hexastack[web]"

# GraphQL support
pip install "hexastack[graphql]"

# Model Context Protocol support
pip install "hexastack[mcp]"

# gRPC support
pip install "hexastack[grpc]"

# Database support with migrations
pip install "hexastack[db]"

# Complete ecosystem
pip install "hexastack[all]"
```

---

## 4. CLI Diagnostic Commands

When installed with `hexastack[all]` or `hexastack[cli]`:

```bash
# Check installed packages and optional dependency statuses
hexastack info

# Inspect registered CQRS commands, queries, and configs
hexastack inspect registry

# Send a test ping command through the CQRS pipeline
hexastack ping --message "Hello Hexastack"

# Launch local FastAPI dev server with live reload (requires hexastack[web])
hexastack serve --host 127.0.0.1 --port 8000

# Launch MCP server in stdio mode (requires hexastack[mcp])
hexastack mcp run

# Launch gRPC daemon (requires hexastack[grpc])
hexastack grpc serve --host 0.0.0.0 --port 50051

# Manage database migrations (requires hexastack[db])
hexastack db init migrations/
hexastack db revision "add users table"
hexastack db upgrade head
hexastack db current
hexastack db history
```
