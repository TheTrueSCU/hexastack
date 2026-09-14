# Monorepo Packages Catalog

> Hexastack is divided into specialized packages that can be installed individually or consumed as a unified framework via `hexastack[extras]`.

---

| Package | Purpose & Capabilities | PyPI Extras |
|---|---|---|
| [`hexastack`](https://pypi.org/project/hexastack/) | Umbrella distribution, diagnostic CLI, and project scaffolding engine (`hexastack new`). | `hexastack[all]` |
| [`hexastack-ai`](https://pypi.org/project/hexastack-ai/) | LLM integration adapters (LiteLLM, Instructor, PydanticAI) & reflective agents. | `hexastack[ai]` |
| [`hexastack-auth`](https://pypi.org/project/hexastack-auth/) | JWT authentication, PBKDF2 hashing, and `@authorize` RBAC middleware. | `hexastack[auth]` |
| [`hexastack-cli`](https://pypi.org/project/hexastack-cli/) | Typer & Rich CLI presentation adapter with `CliNarrator` demo recording. | `hexastack[cli]` |
| [`hexastack-core`](https://pypi.org/project/hexastack-core/) | Kernel, `rodi` DI container, bootstrap lifecycle engine. | Core dependency |
| [`hexastack-cqrs`](https://pypi.org/project/hexastack-cqrs/) | In-memory Command, Query, and Event execution buses & middleware pipelines. | Core dependency |
| [`hexastack-db`](https://pypi.org/project/hexastack-db/) | SQLAlchemy 2.0 async/sync repositories, Unit of Work, and Alembic migrations. | `hexastack[db]`, `hexastack[sql]` |
| [`hexastack-events`](https://pypi.org/project/hexastack-events/) | CloudEvents 1.0 specifications and Transactional Outbox pattern engine. | `hexastack[events]` |
| [`hexastack-fastapi`](https://pypi.org/project/hexastack-fastapi/) | FastAPI routing decorators, session middleware, CQRS routing, and auth. | `hexastack[fastapi]` |
| [`hexastack-flags`](https://pypi.org/project/hexastack-flags/) | CNCF OpenFeature integration (Flagd, Unleash, Flipt providers). | `hexastack[flags]` |
| [`hexastack-flow`](https://pypi.org/project/hexastack-flow/) | Hexagonal workflow engine adapter integrating `hexaflow>=0.2.0` with CQRS, DB, and Events. | `hexastack[flow]` |
| [`hexastack-graphql`](https://pypi.org/project/hexastack-graphql/) | Strawberry GraphQL presentation adapter over CQRS. | `hexastack[graphql]` |
| [`hexastack-grpc`](https://pypi.org/project/hexastack-grpc/) | Protobuf schema compilation, async gRPC server, and bidirectional streaming. | `hexastack[grpc]` |
| [`hexastack-logging`](https://pypi.org/project/hexastack-logging/) | Structured JSON logging, PII sanitization, and Logfire integration. | Core dependency |
| [`hexastack-mcp`](https://pypi.org/project/hexastack-mcp/) | Model Context Protocol (MCP) server & AI tool provider adapter. | `hexastack[mcp]` |
| [`hexastack-otel`](https://pypi.org/project/hexastack-otel/) | OpenTelemetry distributed tracing and OTLP exporters. | `hexastack[otel]` |
| [`hexastack-ui`](https://pypi.org/project/hexastack-ui/) | Interactive NiceGUI reactive DevTools console, command dispatcher, and telemetry visualizer. | `hexastack[ui]` |

*(Note: Quality, testing, and release engineering are powered by the standalone [`hexaqual`](https://github.com/TheTrueSCU/hexaqual) suite).*

---

## In-Depth Articles

!!! tip "On DEV.to"
    [What Is Hexastack?](devto://what-is-hexastack) — a full package tour with the CNCF integration
    story and the compliance motivations behind each architectural choice.

!!! tip "On DEV.to"
    [Your FastAPI Service, Now AI-Native: LLM Agents + MCP](devto://ai-native-backend-mcp) —
    `hexastack-ai` and `hexastack-mcp` in practice: CQRS agent reflection, `@mcp_tool` decorators,
    and PydanticAI offline testing.

!!! tip "On DEV.to"
    [Beyond `if os.getenv`: Feature Flags with OpenFeature](devto://feature-flags-openfeature) —
    `hexastack-flags`, the `FeatureFlagPort`, and the CNCF OpenFeature provider factory.

!!! tip "On DEV.to"
    [Logging and Tracing That Don't Fight Your Architecture](devto://observability-ports) —
    `hexastack-logging` and `hexastack-otel`: swappable backends behind `LoggingPort` and `TracingPort`,
    automatic CQRS pipeline tracing, and PII sanitization.
