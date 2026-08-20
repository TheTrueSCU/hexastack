# Hexastack

> **Production-grade Hexagonal Architecture (Ports & Adapters) monorepo framework for Python 3.13+.**

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Architecture](https://img.shields.io/badge/architecture-hexagonal-emerald.svg)](architecture.md)

---

## 🌟 Why Hexastack?

Modern backend microservices often suffer from leaky abstractions, tightly coupled ORMs, fragmented logging, and brittle presentation layers. **Hexastack** solves this by establishing strict architectural boundaries backed by automated conformance tests and tiered CI gates:

```mermaid
graph TD
    subgraph DrivingAdapters ["Driving Adapters (Inbound / Presentation)"]
        CLI["hexastack-cli (Typer & Rich)"]
        FASTAPI["hexastack-fastapi (FastAPI REST)"]
        GRPC["hexastack-grpc (gRPC Services)"]
        MCP["hexastack-mcp (AI MCP Tools)"]
        UI["hexastack-fastapi[ui] (NiceGUI DevTools)"]
    end

    subgraph Hexagon ["Hexagonal Core"]
        PORTS_IN["Driving Ports (CommandBus, QueryBus, Pipeline)"]
        DOMAIN["Pure Domain Models & Business Invariants"]
        PORTS_OUT["Driven Ports (RepositoryPort, OutboxPort, LoggerPort)"]
    end

    subgraph DrivenAdapters ["Driven Adapters (Outbound / Infrastructure)"]
        DB["hexastack-db (SQLAlchemy & Alembic)"]
        EVENTS["hexastack-events (CloudEvents 1.0 & Outbox)"]
        LOGGING["hexastack-logging (JSON Telemetry & Redaction)"]
        OTEL["hexastack-otel (OpenTelemetry Distributed Tracing)"]
        FLAGS["hexastack-flags (OpenFeature Flagd/Unleash)"]
    end

    CLI --> PORTS_IN
    FASTAPI --> PORTS_IN
    GRPC --> PORTS_IN
    MCP --> PORTS_IN
    UI --> PORTS_IN

    PORTS_IN --> DOMAIN
    DOMAIN --> PORTS_OUT

    PORTS_OUT --> DB
    PORTS_OUT --> EVENTS
    PORTS_OUT --> LOGGING
    PORTS_OUT --> OTEL
    PORTS_OUT --> FLAGS
```

---

## 🚀 Instant Scaffolding

Generate a standardized, production-ready hexagonal microservice with zero local dependencies using `uvx`:

```bash
# REST Web API service with FastAPI and SQLite
uvx hexastack new web-api billing-service --db sqlite

# Event-driven streaming microservice with CloudEvents & Transactional Outbox
uvx hexastack new event-driven order-service

# Model Context Protocol (MCP) server & AI tools
uvx hexastack new mcp-agent agent-service

# Minimal CLI or background worker
uvx hexastack new minimal worker-service
```

---

## 📚 Explore Documentation

- [**Feature Demos & Interactive Walkthroughs**](demos.md): Watch recorded demonstrations of the Scaffolding CLI and DevTools Console.
- [**Tutorial: Building a Complete Todo Service**](tutorials/01-building-a-todo-service.md): Step-by-step guide from zero to production.
- [**Architecture & Invariants**](architecture.md): Deep dive into strict package boundaries, tiered CI, and hexagonal rules.
- [**Monorepo Packages Catalog**](packages.md): Complete index of all 13 specialized packages in the monorepo.
