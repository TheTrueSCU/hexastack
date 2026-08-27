# Hexastack Public Roadmap

This document outlines the strategic priorities, upcoming milestones, and architecture roadmap for **Hexastack**.

---

## 🎯 Current Milestone: v0.1.0 (Public Release & Verification)
- [x] Pure Hexagonal Architecture kernel (`hexastack-core`, `hexastack-cqrs`)
- [x] Multi-transport adapters: FastAPI REST, Typer CLI, gRPC Protobuf, MCP AI Tools, GraphQL Strawberry
- [x] NiceGUI DevTools with WCAG 2.1 AA accessibility conformance
- [x] Comprehensive test harness: 100% test parity (`check_test_parity.py`), Hypothesis property fuzzing, Schemathesis ASGI contract tests
- [x] Automated OpenSSF Scorecard and Best Practices passing badge integration

---

## 🚀 Near-Term Priorities (v0.2.0)
- **High-Throughput Serialization**: Zero-copy `msgspec` JSON & MessagePack codec engine for high-throughput CQRS bus dispatches.
- **Async gRPC Server Reflection**: Native streaming RPC support with bidirectional flow control in `hexastack-grpc`.
- **WebSocket & SSE Outbox Streaming**: Real-time frontend client notifications dispatched from the Transactional Outbox.
- **OpenTelemetry Metrics Export**: Prometheus and OTLP metrics emission alongside existing distributed trace spans.

---

## 🔮 Future Vision (v0.3.0+)
- **Distributed Event Broker Adapters**: Kafka and NATS JetStream driven adapters with exactly-once delivery guarantees.
- **WASM / MicroPython Lightweight Core**: Ultra-lightweight domain core compilation for edge environments.
- **AI Agent Memory Adapter**: Vector database driven adapters (Qdrant, pgvector) with CQRS query caching.
