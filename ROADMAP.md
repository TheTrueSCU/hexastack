# Hexastack Public Roadmap

This document outlines the strategic priorities, upcoming milestones, and architecture roadmap for **Hexastack**.

---

## 🎯 Released Milestones

### v0.1.0 (Public Release & Core Verification) ✅
- [x] Pure Hexagonal Architecture kernel (`hexastack-core`, `hexastack-cqrs`)
- [x] Multi-transport adapters: FastAPI REST, Typer CLI, gRPC Protobuf, MCP AI Tools, GraphQL Strawberry
- [x] Comprehensive test harness: 100% test parity (`check_test_parity.py`), Hypothesis property fuzzing, Schemathesis ASGI contract tests
- [x] OpenSSF Best Practices (Passing & Silver 100%) and Scorecard automation

---

## 🚀 Active Milestone: v0.2.0 (High-Throughput Core, Resilient Brokers & Ergonomics)
- [x] **Developer Tooling Suite**: Dogfood Hexagonal architecture across all internal developer tools via `hexastack-tools` (PR #42).
- [x] **Enterprise Compliance & Regulatory Guide**: HIPAA, FedRAMP, SOC 2, and PCI-DSS compliance mapping (`COMPLIANCE.md` - PR #43).
- [x] **Distributed Event Streaming**: NATS JetStream distributed event bus with durable work queues & DLQ routing (`hexastack-events[nats]` - PR #50).
- [x] **Async-Sync Thread Bridge**: `JanusEventChannel` & `JanusCommandQueue[T]` thread-safe queues (`hexastack-events[janus]` - PR #50).
- [x] **High-Throughput Serialization**: Zero-copy `msgspec` JSON & MessagePack codec engine for CloudEvents 1.0 (PR #38 / #50).
- [ ] **InOutMiddleware Template Base Class**: Standardize `before`, `after`, and `on_error` interceptor hooks (Issue #56).
- [ ] **Distributed Cache Adapters**: `RedisCacheAdapter` & `AsyncRedisCacheAdapter` supporting both Redis and Valkey (`hexastack-core[redis,valkey]` - Issue #57).
- [ ] **API Rate Limiting**: `RateLimiterPort` and `slowapi`/`limits` route protection (`hexastack-fastapi[ratelimit]` - Issue #58).
- [ ] **Async gRPC Server Reflection & Streaming**: Bidirectional streaming RPC support in `hexastack-grpc`.
- [ ] **Turnkey Observability**: Prometheus `/metrics` endpoint and Sentry error tracking integration.

---

## 🔮 Future Vision: v0.3.0+ (HexaQueue Flagship & High Availability)
- **High-Availability Primitives**: `LeaderElectionPort` and distributed `LockPort` (Redis / Valkey / Etcd - Issue #59).
- **HexaQueue Distributed Task & Stream Engine**: Partitioned stream ingestion, active-standby cluster coordination, and lease renewal.
- **Kafka Distributed Event Bus**: Apache Kafka / Redpanda driven adapter with consumer group balancing.
- **WASM / MicroPython Lightweight Core**: Edge deployment compilation profile.
- **AI Agent Long-Term Memory**: Vector database driven adapters (Qdrant, pgvector) with CQRS query caching.
