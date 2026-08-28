# Hexastack Usage Guide & Developer Recipes

This guide provides end-to-end usage examples and recipes for building resilient, decoupled Python applications with Hexastack.

---

## 1. Quickstart: Scaffolding a New Project

The fastest way to start a new service is using `hexastack new` or the interactive wizard `hexastack init`.

```bash
# Interactive wizard (select template, database, transports, release pipeline, OpenSSF pack)
hexastack init

# Or scaffold a specific archetype directly with release & OpenSSF governance:
hexastack new web-api order-service
hexastack init --name payment-service --template web-api --with-release --with-openssf
cd order-service

# Install dependencies and sync environment
uv sync

# Run tests and verify architectural layer boundaries
uv run pytest
uv run lint-imports
```

### Supported Archetypes

| Archetype | Key Components Included |
|---|---|
| `web-api` | FastAPI REST endpoints, OpenAPI docs, SQLite/Postgres DB session middleware, health probes. |
| `grpc-service` | In-process ProtoCompiler, inline Protobuf schemas, gRPC Reflection, Buf linting. |
| `mcp-agent` | Model Context Protocol (MCP) server, stdio mode for Gemini/Antigravity/Claude, reflective tools. |
| `graphql-service` | Strawberry GraphQL schema, CQRS query resolvers, GraphQL Playground. |
| `event-driven` | CloudEvents 1.0 streaming, Transactional Outbox relay daemon, consumer handlers. |
| `enterprise` | Multi-transport omnibus (FastAPI + gRPC + GraphQL + MCP + Outbox + Release + OpenSSF). |
| `minimal` | Ultra-lightweight CQRS bus kernel without transport dependencies. |

### Day 1 Production Batteries
* `--with-release`: Generates `.github/workflows/release.yml` (automated PyPI build & publish via `uv build` and `pypa/gh-action-pypi-publish`, plus SPDX & CycloneDX SBOMs via `anchore/sbom-action`) and `CHANGELOG.md`.
* `--with-openssf`: Generates `.github/workflows/scorecard.yml` (weekly automated OpenSSF security audits), `SECURITY.md`, `GOVERNANCE.md`, and `CODE_OF_CONDUCT.md`.


---

## 2. Defining Domain Entities & CQRS Handlers

Hexastack enforces strict separation of concerns. Business logic is placed in domain models and CQRS handlers that have **zero framework dependencies**.

### Step 1: Create a Command & Handler

```python
from dataclasses import dataclass
from hexastack_cqrs import command_handler


@dataclass(frozen=True)
class CreateOrderCommand:
    order_id: str
    customer_id: str
    amount: float


@command_handler(CreateOrderCommand)
class CreateOrderHandler:
    def __init__(self, order_repo: OrderRepositoryPort) -> None:
        self.order_repo = order_repo

    async def __call__(self, command: CreateOrderCommand) -> dict[str, str]:
        order = Order(
            id=command.order_id, customer_id=command.customer_id, amount=command.amount
        )
        await self.order_repo.save(order)
        return {"status": "created", "order_id": order.id}
```

### Step 2: Create a Cached Query & Handler

```python
from dataclasses import dataclass
from hexastack_cqrs import query_handler, cached_query


@dataclass(frozen=True)
class GetOrderQuery:
    order_id: str


@cached_query(ttl_seconds=300, tags=["orders"], key_fields=["order_id"])
@query_handler(GetOrderQuery)
class GetOrderHandler:
    def __init__(self, order_repo: OrderRepositoryPort) -> None:
        self.order_repo = order_repo

    async def __call__(self, query: GetOrderQuery) -> OrderDTO:
        order = await self.order_repo.find_by_id(query.order_id)
        if not order:
            raise EntityNotFoundError(f"Order {query.order_id} not found")
        return OrderDTO.from_entity(order)
```

---

## 3. Exposing Commands Across Transports (Protocol Parity)

A single CQRS Command or Query can be exposed simultaneously across HTTP, gRPC, CLI, and MCP without duplicating business logic:

### REST API Route (FastAPI)

```python
from hexastack_fastapi import api_command, api_query


@api_command(
    path="/orders",
    command_cls=CreateOrderCommand,
    status_code=201,
    tags=["Orders"],
)
def create_order_endpoint() -> None:
    """Create a new customer order."""
```

### CLI Command (Typer)

```python
from hexastack_cli import cli_command
import typer


@cli_command(name="create-order")
def create_order_cli(
    order_id: str = typer.Option(..., help="Unique Order ID"),
    customer_id: str = typer.Option(..., help="Customer ID"),
    amount: float = typer.Option(..., help="Order total amount"),
) -> None:
    """CLI presenter that dispatches CreateOrderCommand to the bus."""
```

### Model Context Protocol Tool (MCP)

```python
from hexastack_mcp import mcp_tool


@mcp_tool(
    name="create_order",
    description="Places a new customer order in the system",
    command_cls=CreateOrderCommand,
)
def create_order_tool() -> None:
    """MCP agent tool wrapper."""
```

---

## 4. Multi-Transport Local Dev Server (`hexastack dev`)

Run all primary transports and background relays concurrently in isolated processes with one command:

```bash
# Launches FastAPI (:8000), gRPC (:50051), and Outbox Relay concurrently
hexastack dev
```

---

---

## 5. Developer Tooling & Verification Scripts

The workspace provides purpose-built developer CLI commands for architecture validation, testing, and formatting:

```bash
# Alphabetize imports and export statements across packages
uv run alphabetizer

# Check 1:1 parity between src/ implementation modules and unit tests
uv run check-test-parity

# Run dependency boundary analysis (Deptry)
uv run deptry-run

# Inspect GitHub CI check runs and commit status conclusions
uv run gh-checks <pr-number-or-ref>

# Bucket and analyze GitHub CodeQL security & quality code-scanning alerts
uv run gh-code-scanning

# Inspect PR review comments and automated security findings
uv run gh-security <pr-number>


# Enforce hexagonal layer and cross-package import boundaries across packages
uv run import-linter-run

# Run pre-commit quality checks across all files
uv run pre-commit run --all-files

# Re-generate architecture dependency graphs (Pydeps SVGs)
uv run pydeps-generate

# Build distribution wheels and tarballs for all 15 monorepo packages
uv run pypi-build

# Audit version synchronization across monorepo and check against live PyPI registry
uv run pypi-check

# Dry-run publish packages or monitor GitHub Actions release workflows
uv run pypi-publish --monitor

# Run impact-driven test suite for affected packages only (based on git diff)
uv run pytest-run -A -U

# Run property-based invariant & fuzzing tests
uv run pytest-run -P

# Run unit & integration test suite (with coverage enforcement)
uv run pytest-run -U

```

---

## 6. OpenSSF Security & Best Practices Rigor

Hexastack maintains an automated security and supply-chain governance posture:

- **OpenSSF Best Practices**: Certified at **100% Silver** (with **270% cumulative progress** including Gold criteria).
- **OpenSSF Scorecard**: Scored at **7.1 / 10** with enforced GitHub Actions commit-SHA dependency pinning, least-privilege token permissions, and automated CodeQL SAST scanning on all commits.
- **Supply Chain Artifacts**: Automated SPDX and CycloneDX Software Bill of Materials (SBOMs) generated with releases.
- **Accessibility & Compliance**: DevTools interface adheres to **WCAG 2.1 AA** accessibility standards and is validated via automated axe-core Playwright suites.
