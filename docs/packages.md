# Monorepo Packages Catalog

> Hexastack is divided into specialized packages that can be installed individually or consumed as a unified framework via `hexastack[extras]`.

---

| Package | Purpose & Capabilities | PyPI Extras |
|---|---|---|
| [`hexastack-core`](https://pypi.org/project/hexastack-core/) | Kernel, `rodi` DI container, bootstrap lifecycle engine. | Core dependency |
| [`hexastack-cqrs`](https://pypi.org/project/hexastack-cqrs/) | In-memory Command, Query, and Event execution buses & middleware pipelines. | Core dependency |
| [`hexastack-logging`](https://pypi.org/project/hexastack-logging/) | Structured JSON logging, PII sanitization, and Logfire integration. | Core dependency |
| [`hexastack-fastapi`](https://pypi.org/project/hexastack-fastapi/) | FastAPI routing decorators, session middleware, DevTools dashboard, and NiceGUI reactive UI. | `hexastack[fastapi]`, `hexastack[ui]` |
| [`hexastack-cli`](https://pypi.org/project/hexastack-cli/) | Typer & Rich CLI presentation adapter with `CliNarrator` demo recording. | `hexastack[cli]` |
| [`hexastack-db`](https://pypi.org/project/hexastack-db/) | SQLAlchemy 2.0 async/sync repositories, Unit of Work, and Alembic migrations. | `hexastack[db]`, `hexastack[sql]` |
| [`hexastack-auth`](https://pypi.org/project/hexastack-auth/) | JWT authentication, PBKDF2 hashing, and `@authorize` RBAC middleware. | `hexastack[auth]` |
| [`hexastack-events`](https://pypi.org/project/hexastack-events/) | CloudEvents 1.0 specifications and Transactional Outbox pattern engine. | `hexastack[events]` |
| [`hexastack-ai`](https://pypi.org/project/hexastack-ai/) | LLM integration adapters (LiteLLM, Instructor, PydanticAI) & reflective agents. | `hexastack[ai]` |
| [`hexastack-mcp`](https://pypi.org/project/hexastack-mcp/) | Model Context Protocol (MCP) server & AI tool provider adapter. | `hexastack[mcp]` |
| [`hexastack-flags`](https://pypi.org/project/hexastack-flags/) | CNCF OpenFeature integration (Flagd, Unleash, Flipt providers). | `hexastack[flags]` |
| [`hexastack-otel`](https://pypi.org/project/hexastack-otel/) | OpenTelemetry distributed tracing and OTLP exporters. | `hexastack[otel]` |
| [`hexastack-graphql`](https://pypi.org/project/hexastack-graphql/) | Strawberry GraphQL presentation adapter over CQRS. | `hexastack[graphql]` |
| [`hexastack-tools`](https://pypi.org/project/hexastack-tools/) | Developer tooling, governance, multi-format presenters, and CI inspection suite (`gh-pr-examine`). | `hexastack[tools]` |
| [`hexastack`](https://pypi.org/project/hexastack/) | Umbrella distribution, diagnostic CLI, and project scaffolding engine (`hexastack new`). | `hexastack[all]` |
