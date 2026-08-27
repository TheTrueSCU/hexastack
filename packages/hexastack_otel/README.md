![hexastack-otel](../../docs/assets/static/logos/packages/hexastack_otel.png)

# hexastack-otel

**Vendor-agnostic OpenTelemetry distributed tracing and CQRS telemetry middleware for Hexastack.**

Part of the [Hexastack Framework](https://github.com/TheTrueSCU/hexastack).

[![PyPI: hexastack-otel](https://img.shields.io/pypi/v/hexastack-otel.svg)](https://pypi.org/project/hexastack-otel/)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Coverage](https://codecov.io/github/TheTrueSCU/hexastack/graph/badge.svg?component=hexastack_otel)](https://codecov.io/github/TheTrueSCU/hexastack)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](../../LICENSE)

---

## 1. Architectural Overview

`hexastack-otel` provides a pure hexagonal port interface ([`TracingPort`](file:///home/rjdw/Projects/hexastack/packages/hexastack_otel/src/hexastack_otel/ports/tracing.py)) backed by the official **OpenTelemetry Python SDK**.

It enables 100% vendor-agnostic distributed tracing, automatically linking correlation IDs and creating spans across CQRS Command/Query executions, HTTP endpoints, and gRPC RPCs.

```mermaid
graph TD
    CQRS["CQRS Command / Query Dispatch"]
    MW["TracingMiddleware (order=12)"]
    PORT["TracingPort"]
    OTEL["OtelTracingAdapter\n(OpenTelemetry SDK)"]
    MEM["InMemoryTracingAdapter\n(Test Isolation)"]
    OTLP["OTLP Exporter\n(gRPC / HTTP)"]
    COLLECTOR["OTel Collector / Jaeger / Grafana Tempo / Sift"]

    CQRS --> MW
    MW --> PORT
    PORT -.-> OTEL
    PORT -.-> MEM
    OTEL --> OTLP
    OTLP --> COLLECTOR
```

---

## 2. Quickstart

### Installation

```bash
# Core OpenTelemetry SDK & TracingPort
pip install hexastack-otel

# With OTLP Protobuf Exporters (gRPC & HTTP)
pip install hexastack-otel[otlp]
```

### Configuration (`hexastack.toml` or `pyproject.toml`)

```toml
[hexastack.otel]
service_name = "order-service"
endpoint = "http://localhost:4317"
exporter = "otlp_grpc" # "memory", "console", "otlp_grpc", "otlp_http"
sample_rate = 1.0
enabled = true
```

---

## 3. Automatic CQRS Tracing & Dynamic Feature Flagging

The [`TracingMiddleware`](file:///home/rjdw/Projects/hexastack/packages/hexastack_otel/src/hexastack_otel/infra/middleware.py) automatically wraps every dispatched command or query in a scoped span:

- **Dynamic Feature Flag Control**: Evaluates `features.otel.tracing` via `FeatureFlagPort` dynamically per-message, enabling zero-downtime activation/deactivation of telemetry spans.
- **Span Name**: `cqrs.CreateOrderCommand`
- **Attributes**:
  - `message.name`: `CreateOrderCommand`
  - `message.type`: `command`
  - `correlation.id`: `0724ec78-f952-4467...`
  - `tenant.id`: `tenant-alpha`
  - `user.id`: `usr_123`
- **Error Capture**: Automatically catches unhandled exceptions, records them as span exception events, and sets span status to `ERROR`.
