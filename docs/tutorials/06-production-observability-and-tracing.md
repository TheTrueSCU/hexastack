# Tutorial 6: Production Observability & Distributed Tracing

In this final chapter, you will instrument the To-Do microservice for **production observability**, **OpenTelemetry distributed tracing**, **structured JSON logging**, and live inspection via the **Hexastack DevTools Dashboard**.

> *"How do we trace an end-to-end transaction as it travels from an HTTP REST request, through CQRS handlers, into database queries, outbox event relays, and MCP AI tool calls?"*

---

## 1. Unified Telemetry Architecture

Hexastack provides an ambient correlation context that propagates across threads, async coroutines, and transport boundaries without manual parameter passing:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. Inbound Request (HTTP / CLI / MCP)                                       │
│    └─ CorrelationHttpMiddleware creates Correlation ID [corr: 8fdf00bd]     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. CQRS Execution Pipeline                                                  │
│    ├─ Span: "CQRS: CreateTodoCommand"                                       │
│    ├─ Metric: cqrs_handler_duration_seconds (p95, p99)                      │
│    └─ Structured Log: {"event": "cmd_started", "corr": "8fdf00bd"}         │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. Database Persistence & Outbox                                            │
│    ├─ Span: "SQLite: INSERT INTO todos"                                     │
│    └─ Span: "SQLite: INSERT INTO outbox_events"                             │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. Outbox Event Relay & Notification Dispatch                               │
│    ├─ Span: "Outbox: Publish AdminDeletedUserTodoEvent"                     │
│    └─ Span: "Notification: Apprise Webhook / ntfy"                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Structured JSON Logging with Ambient Correlation IDs

Configure structured logging with ambient correlation contexts:

```python
# src/todo_app/infra/logging.py
from hexastack_core.adapters.logging import StandardLogger

logger = StandardLogger("todo_app.prod")

# Inside any handler or adapter:
logger.info(
    "To-Do task successfully processed",
    extra={"todo_id": todo.id, "owner_id": todo.owner_id, "priority": todo.priority}
)
```

**JSON Output in Production**:
```json
{
  "timestamp": "2026-08-20T20:25:00.123Z",
  "level": "INFO",
  "logger": "todo_app",
  "message": "To-Do task successfully processed",
  "correlation_id": "8fdf00bd-45a2-4a0b-932f-b4e12e1098a1",
  "todo_id": "00b158af-155a-4586-a793-7f0642451199",
  "owner_id": "alice",
  "priority": "high"
}
```

---

## 3. Dedicated Scoped Entrypoint (`ch06_observability.py`)

Create `src/todo_app/entrypoints/ch06_observability.py`:

```python
"""Chapter 6 Entrypoint: Fully Instrumented Production To-Do Service."""

import uvicorn
from fastapi import FastAPI
from rodi import Container

from hexastack_core.adapters.logging import StandardLogger
from hexastack_core.adapters.notification import StdoutNotificationAdapter
from hexastack_core.infra.bootstrap import bootstrap
from hexastack_core.ports.logging import LoggingPort
from hexastack_core.ports.notification import NotificationPort

import todo_app.infra.handlers
from todo_app.adapters.driven.sqlite import (
    SqliteTodoRepository,
    create_sqlite_session_factory,
)
from todo_app.adapters.driving.http import router
from todo_app.ports.repositories import TodoRepositoryPort


def build_app(db_url: str = "sqlite:///todos_prod.db") -> FastAPI:
    di = Container()
    session_factory = create_sqlite_session_factory(db_url=db_url)
    repo = SqliteTodoRepository(session_factory=session_factory)
    notifier = StdoutNotificationAdapter()
    logger = StandardLogger("todo_app.prod")

    di.add_instance(repo, declared_class=TodoRepositoryPort)
    di.add_instance(notifier, declared_class=NotificationPort)
    di.add_instance(logger, declared_class=LoggingPort)

    res = bootstrap(
        container=di,
        packages_to_scan=[
            todo_app.infra.handlers,
        ],
    )
    app = res.container.resolve(FastAPI)
    app.include_router(router)
    return app


app = build_app()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

---

## 4. Scaffolding & Terminal Experience

Watch the CLI setup for a production-grade microservice:

<video controls autoplay loop muted playsinline width="100%" style="border-radius: 8px; margin: 16px 0; box-shadow: 0 10px 30px rgba(0,0,0,0.4);">
  <source src="../assets/demos/todo-ch06-cli-demo.webm" type="video/webm">
  <track label="English" kind="subtitles" srclang="en" src="../assets/demos/todo-ch06-cli-demo.vtt" default>
</video>

---

## 5. Verification: Observability & Endpoints

Watch the browser interaction and production telemetry walkthrough live in Chromium:

<video controls autoplay loop muted playsinline width="100%" style="border-radius: 8px; margin: 16px 0; box-shadow: 0 10px 30px rgba(0,0,0,0.4);">
  <source src="../assets/demos/todo-ch06-browser-demo.webm" type="video/webm">
  <track label="English" kind="subtitles" srclang="en" src="../assets/demos/todo-ch06-browser-demo.vtt" default>
</video>

---

## 6. Course Conclusion & Next Steps

🎉 **Congratulations!** You have built a complete, production-grade microservice with Hexastack:

1. ✅ **Pure Domain Invariants & CQRS Separation**
2. ✅ **Swappable SQLite & In-Memory Persistence**
3. ✅ **JWT Authentication & RBAC Task Ownership**
4. ✅ **Transactional Outbox & Multi-Channel Alerting (Apprise, Stdout, File)**
5. ✅ **Model Context Protocol (MCP) AI Tools & Feature Flag Gating**
6. ✅ **Distributed Tracing, Structured Logging & DevTools Visualizer**

Explore the source code on [GitHub](https://github.com/TheTrueSCU/hexastack) or check out the [Architecture Reference Guide](../index.md).
