# CHANGELOG

## v0.1.0 (2026-08-27)

### Highlights & Features
* **Modular Monorepo Architecture**: 15 cohesive, decoupled hexagonal architecture microservice packages (`core`, `cqrs`, `logging`, `fastapi`, `db`, `auth`, `events`, `ai`, `mcp`, `flags`, `graphql`, `grpc`, `otel`, `cli`, and `hexastack` umbrella).
* **Dual Execution Pipelines**: Pure sync and high-throughput `asyncio` execution flows across all ports and middleware with automatic sync/async bridging.
* **Pluggable Transports**: Built-in first-class adapters for FastAPI REST API, gRPC (Protobuf reflection), GraphQL (Strawberry), MCP AI Agent tools, and Event Buses (CloudEvents + Outbox).
* **Enterprise Security & Identity**: JWT & RBAC with OPA and OpenFGA policy evaluation, Argon2id password hashing, and SPIFFE/SPIRE workload attestation.
* **Multi-Backend Persistence**: Async SQLAlchemy 2.0 repository with transaction isolation, Unit of Work middleware, and in-memory vector embeddings with cosine similarity.
* **360° Quality & Verification Rigor**: 100% OpenSSF Best Practices Silver Badge, Hypothesis property-based fuzzing, 90%+ code coverage, import-linter boundary gates, mutation testing triage, and automated SPDX & CycloneDX SBOM generation.
