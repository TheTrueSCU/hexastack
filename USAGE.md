# Hexastack Usage Guide & Developer Recipes

This guide provides end-to-end usage examples and recipes for building resilient, decoupled Python applications with Hexastack.

---

## 1. Quickstart: Scaffolding a New Project

The fastest way to start a new service is using `hexastack new` or the interactive wizard `hexastack init`.

```bash
# Interactive wizard (select template, database, auth, transports, telemetry)
hexastack init

# Or scaffold a specific archetype directly:
hexastack new web-api order-service
cd order-service

# Install dependencies and sync environment
uv sync

# Run tests and verify architectural layer boundaries
uv run pytest
uv run import-linter-run
```

### Supported Archetypes

| Archetype | Key Components Included |
|---|---|
| `web-api` | FastAPI REST endpoints, OpenAPI docs, SQLite/Postgres DB session middleware, health probes. |
| `grpc-service` | In-process ProtoCompiler, inline Protobuf schemas, gRPC Reflection, Buf linting. |
| `mcp-agent` | Anthropic Model Context Protocol (MCP) server, stdio & SSE transports, reflective tools. |
| `graphql-service` | Strawberry GraphQL schema, CQRS query resolvers, GraphQL Playground. |
| `event-driven` | CloudEvents 1.0 streaming, Transactional Outbox relay daemon, consumer handlers. |
| `enterprise` | Multi-transport omnibus (FastAPI + gRPC + GraphQL + MCP + Outbox + RBAC Auth). |
| `minimal` | Ultra-lightweight CQRS bus kernel without transport dependencies. |

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
        order = Order(id=command.order_id, customer_id=command.customer_id, amount=command.amount)
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

## 5. Testing Recipes & Invariant Verification

Hexastack projects come configured with automated testing tools:

```bash
# Run unit and integration tests
uv run pytest

# Check hexagonal boundary import rules
uv run import-linter-run

# Run static type checking
uv run ty check packages

# Run property-based invariant fuzzing
uv run pytest -k "test_hypothesis"

# Run Schemathesis ASGI OpenAPI negative fuzzing
uv run pytest -k "test_openapi"

# Run full pre-commit pipeline
uv run pre-commit run --all-files
```
