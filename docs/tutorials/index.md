# 🎓 Hexastack Tutorials & Guides

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/TheTrueSCU/hexastack)

Explore hands-on, step-by-step tutorials demonstrating how to build robust, modular, and strictly partitioned microservices using **Hexastack**. All tutorials and runnable microservice examples are pre-configured to run directly in your browser with zero setup.

---

## 🌟 Flagship Multi-Chapter Series: The Hexagonal To-Do Microservice

A complete 7-chapter walkthrough building a microservice from a clean in-memory core up to enterprise-grade events, AI tooling, OpenTelemetry, and high-performance gRPC.

| Chapter | Title | Architectural Focus |
| :--- | :--- | :--- |
| **[Chapter 1](todo-app/01-building-a-todo-service.md)** | **Building a To-Do Service** | Hexagonal Core, CQRS Command/Query Buses, In-Memory Ports |
| **[Chapter 2](todo-app/02-sqlite-persistence-and-migrations.md)** | **SQLite & Migrations** | SQLModel Repositories, Unit of Work, Alembic Migrations |
| **[Chapter 3](todo-app/03-jwt-authentication-and-rbac.md)** | **Authentication & RBAC** | JWT Tokens, Role-Based Access Control, User Context |
| **[Chapter 4](todo-app/04-events-outbox-and-notifications.md)** | **Events & Outbox** | Transactional Outbox, CloudEvents 1.0, NATS/In-Memory Relays |
| **[Chapter 5](todo-app/05-experimental-ai-and-mcp.md)** | **AI Assistant & MCP** | Model Context Protocol Tools, Claude/Gemini Integration |
| **[Chapter 6](todo-app/06-production-observability-and-tracing.md)** | **Observability & Tracing** | OpenTelemetry Distributed Tracing, Structured JSON Logging |
| **[Chapter 7](todo-app/07-high-performance-grpc-and-microservices.md)** | **High-Performance gRPC** | Protobuf Contracts, Inline Schemas, gRPC Server Reflection |

---

## 🏦 Specialized Reference Architecture Tutorials

Focused architectural deep dives addressing mission-critical enterprise engineering patterns:

- [**Double-Entry Financial Ledger & Invariants**](financial-ledger.md)
  Learn how to build a high-integrity financial ledger enforcing strict mathematical invariants ($\sum \text{Debits} = \sum \text{Credits}$), exact `Decimal` arithmetic, and property-based fuzzing with Hypothesis.
