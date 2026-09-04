# Hexastack Public Roadmap

This document outlines the strategic priorities, upcoming milestones, and architecture roadmap for **Hexastack**.

---

## 🎯 Released Milestones

### v0.1.0 (Public Release & Core Verification) ✅
- [x] Pure Hexagonal Architecture kernel (`hexastack-core`, `hexastack-cqrs`)
- [x] Multi-transport adapters: FastAPI REST, Typer CLI, gRPC Protobuf, MCP AI Tools, GraphQL Strawberry
- [x] Comprehensive test harness: 100% test parity (`check-test-parity`), Hypothesis property fuzzing, Schemathesis ASGI contract tests
- [x] OpenSSF Best Practices (Passing & Silver 100%) and Scorecard automation

### v0.2.0 (High-Throughput Core, Resilient Brokers & Ergonomics) ✅
- [x] **Developer Tooling Suite**: Dogfood Hexagonal architecture across all internal developer tools via `hexastack-tools` (PR #42).
- [x] **Enterprise Compliance & Regulatory Guide**: HIPAA, FedRAMP, SOC 2, and PCI-DSS compliance mapping (`COMPLIANCE.md` - PR #43).
- [x] **Distributed Event Streaming**: NATS JetStream distributed event bus with durable work queues & DLQ routing (`hexastack-events[nats]` - PR #50).
- [x] **Async-Sync Thread Bridge**: `JanusEventChannel` & `JanusCommandQueue[T]` thread-safe queues (`hexastack-events[janus]` - PR #50).
- [x] **High-Throughput Serialization**: Zero-copy `msgspec` JSON & MessagePack codec engine for CloudEvents 1.0 (PR #38 / #50).
- [x] **InOutMiddleware Template Base Class**: Standardize `before`, `after`, and `on_error` interceptor hooks across CQRS pipelines (`hexastack-cqrs` - Issue #56, PR #61).
- [x] **Distributed & Persistent Cache Adapters**: `RedisCacheAdapter` / `AsyncRedisCacheAdapter` (Redis/Valkey) and `DiskCacheAdapter` / `AsyncDiskCacheAdapter` (`hexastack-core[redis,valkey,diskcache]` - Issues #57, #32, PR #66).
- [x] **API Rate Limiting**: `RateLimiterPort` and `slowapi`/`limits` route protection with user/tenant/IP extraction (`hexastack-fastapi[ratelimit]` - Issue #58, PR #63).
- [x] **High-Availability Primitives & Multi-Process Locks**: `LockPort` / `AsyncLockPort` (In-Memory `threading.RLock`, `FileLockAdapter`, `RedisLockAdapter`) and `LeaderElectionPort` (In-Memory, Redis lease renewals) (Issues #32, #59, PRs #65, #66).
- [x] **Multi-Process Transactional Outbox Coordination**: Synchronized background polling across daemon processes via `filelock` / `LockPort` in `AsyncioOutboxRelay` and `HueyOutboxRelay` (Issue #32, PR #66).

---

## 🚀 Active Milestone: v0.3.0 (HexaQueue Flagship, Real-Time Streams & Quality Gate)
- [x] **Unified Object & Cloud Storage**: `StoragePort` / `AsyncStoragePort` with `InMemoryStorage`, `LocalStorageAdapter`, and `FsspecStorageAdapter` (`hexastack-core[fsspec]` - Issue #85, PR #88).
- [x] **Native Async Circuit Breaker Resilience Engine**: `CircuitBreakerPort` / `AsyncCircuitBreakerPort` with `InMemoryCircuitBreaker`, `CacheCircuitBreaker` (Redis/Valkey), `CircuitBreakerMiddleware`, and `@circuit_breaker` (Issue #83, PR #89).
- [x] **Server-Sent Events (SSE) Real-Time Streaming Adapter**: `ServerSentEvent`, `EventSourceResponse`, and CQRS streaming queries (`hexastack-fastapi` - Issue #90, PR #93).
- [x] **WebSockets Connection Manager & Channel Bridge**: Bidirectional real-time channels with Redis clustering (`hexastack-fastapi` - Issue #91, PR #94).
- [x] **Async gRPC Server Reflection, Health Checking & Streaming**: `GrpcHealthServicer`, server reflection, and bidirectional streaming dispatch (`hexastack-grpc` - Issue #77, PR #95).
- [x] **Turnkey Observability, Prometheus & Sentry**: `MetricsPort`, `PrometheusMetricsAdapter`, `/metrics` endpoint, and `SentryErrorAdapter` (`hexastack-otel`, `hexastack-logging`, `hexastack-fastapi` - Issue #76, PR #96).
- [x] **Optional Extras Parity Auditor**: CLI validator enforcing subpackage extras forwarding into umbrella package (`hexastack-tools` - Issue #97, PR #102).
- [x] **Standardized In-Memory Test Harness**: Unify unit test mocks onto canonical `InMemory*` adapters (`hexastack-core` - Issue #98, PR #103).
- [x] **Hypothesis Invariant Fuzzing**: Property-based fuzzing for CircuitBreaker, Storage, SSE/WS, and Metrics (Issue #99, PR #104).
- [x] **Tutorial Series Refresh**: Update To-Do microservice tutorial series with `/metrics`, streaming, and unified chapter navigation (Issue #101, PR #105).
- [ ] **HexaQueue Distributed Task & Stream Engine**: Partitioned stream ingestion, active-standby cluster coordination, and lease renewal (Issue #74).

---



## 🔮 Upcoming Milestones

### v0.4.0 (Interactive Frontends, AI Memory & Enterprise Mesh)
- [ ] **Hexastack UI Presentation Package**: Spin out NiceGUI reactive UI and interactive DevTools dashboard into `hexastack-ui` (Issue #100).
- [ ] **Kafka Distributed Event Bus**: Apache Kafka / Redpanda driven adapter with consumer group balancing (`hexastack-events[kafka]` - Issue #75).
- [ ] **AI Agent Long-Term Memory**: Vector database driven adapters (Qdrant, pgvector) with CQRS query caching (`hexastack-ai` - Issue #78).

### v0.5.0 (Edge, WASM & Multimodal Consoles)
- [ ] **WASM / MicroPython Lightweight Core**: Edge deployment compilation profile (Issue #81).
- [ ] **Textual Interactive Terminal UI**: Fullscreen terminal monitoring and operations console (`hexastack-ui[textual]`).
- [ ] **Voice & WebRTC Audio Pipeline**: Real-time conversational audio bridge (`hexastack-ui[voice]`).
