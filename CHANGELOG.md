# CHANGELOG

## [Unreleased] (v0.4.0)

### Highlights & Features
* **Hexastack UI Presentation Package (`hexastack-ui`)**: Extracted NiceGUI reactive UI presentation primitives and the interactive DevTools dashboard from `hexastack-fastapi` into a dedicated presentation package (Issue #100, PR #111).
* **Static Asset Decoupling**: Extracted DevTools dashboard styling into standalone `devtools.css`, eliminating Python AST mutation noise.
* **Biome Code Quality Integration**: Added `biome-check` pre-commit hook targeting static CSS and web assets.

## v0.3.5 (2026-09-06)

### Security & Hardening
* **Zero-Dependency Native SQLite Cache (`hexastack-core`)**: Replaced `diskcache` with a native standard-library `sqlite3` and `json` serializer in `DiskCacheAdapter` and `AsyncDiskCacheAdapter`. Eliminates unsafe Python pickle deserialization vulnerability (CVE-2025-69872) and drops all external C/binary dependencies for disk-based caching.
* **Async File Lock Verification**: Hardened `AsyncFileLockAdapter.locked()` to query underlying filesystem lock state across concurrent worker threads.

### Developer Tooling & Diagrams (`hexastack-tools`)
* **GitHub Repository Diagnostics (`gh-repo`)**: Added `gh-repo` CLI tool to inspect GitHub repository visibility, actions permissions, branch protection environments, and configuration.
* **Pydeps Generation Fix**: Corrected keyword argument mapping in `pydeps-generate` (`output` / `format`) to write architecture SVGs directly into `docs/assets/pydeps/` without creating temporary or untracked `.svg` files in the repository root.

## v0.3.4 (2026-09-06)

### Tooling & Mutation Testing
* **Mutation Runner Cache Refresh**: Added `-r` / `--refresh` option to `mutmut-run` CLI to selectively purge cached mutants for a specific package or workspace before executing mutation testing runs.
* **Safe Mutation Rollback**: Hardened `_revert_bak_and_disk_mutations` in `hexastack-tools` to target only active mutated source files during test interruptions, safeguarding unstaged working tree changes.

### Bug Fixes & Tooling
* **CI & Parallel Test Execution**: Resolved `pytest-cov` / `pytest-xdist` conflict by decoupling dynamic coverage context from global configuration. Parallel test execution (`-n auto`) now runs across all workers cleanly without `DistCovError`.
* **Context-Aware Coverage**: Added `--with-context` option to `pytest-run` CLI to enable single-worker context recording (`--cov-context=test -n 0`) on demand for Test Impact Analysis (`pytest-impact`) and architectural boundary audits (`pytest-boundary-audit`).
* **Cognitive Complexity**: Refactored `show_file_mutants` in `hexastack-tools` (`mutmut.py`), reducing function complexity from 27 down to 8.

## v0.3.2 (2026-09-05)

### Bug Fixes & Improvements
* **Pydeps Generation**: Fixed empty file creation bug when invoking `pydeps` without a GUI display by setting `show=False, noshow=True`.
* **Mutmut Inspection Suite**: Added full unit test coverage and correlation verification for `show_file_mutants`, `show_summary`, and `--correlate-coverage`.

## v0.3.1 (2026-09-05)

### Highlights & Features
* **Test Impact Analysis (TIA)**: Added `pytest-impact` command to dynamically detect modified source lines from git diffs and execute only impacted test nodes.
* **Mutation-Coverage Correlation**: Added `--correlate-coverage` option to `mutmut-inspect` to map surviving mutant source lines directly to executing test functions.
* **Architectural Test Boundary Audit**: Added `pytest-boundary-audit` to ensure domain tests never inadvertently execute infrastructure/adapter layers.
* **Redundant Test Audit**: Added `pytest-redundancy-audit` to detect tests that contribute zero unique branch coverage across the suite.

## v0.3.0 (2026-09-04)

### Highlights & Features
* **HexaQueue Core Primitives**: Introduced partitioned streams and worker-leased task queue primitives in `hexastack-events` (Issue #74).
* **Hexagonal Boundary Enforcement**: Enforced pure hexagonal boundaries across all packages; migrated configurations to domain layer and decoupled adapter dependencies.
* **Universal Dependency & Extras Auditing**: Added `deps-audit` and `check-extras-parity` tools to enforce workspace-wide dependency integrity and umbrella package parity.
* **Workspace-Agnostic Developer Tooling**: Generalized `hexastack-tools` to discover packages dynamically in standalone single-package or multi-package monorepos (Issue #106).
* **Property-Based Fuzzing Suite**: Expanded Hypothesis property-based testing for `CircuitBreaker`, `StoragePort`, SSE/WebSocket bridges, and Prometheus metrics (Issue #99).

## v0.2.0 (2026-09-02)

### Highlights & Features
* **Distributed Event Bus & Messaging**: Added NATS JetStream adapter with durable consumer management, dead-letter queues, and `janus` async/sync queue bridge (Issue #25).
* **Distributed Coordination & HA**: Introduced `LeaderElectionPort` and `LockPort` distributed coordination primitives with Redis & Valkey implementations (Issue #59).
* **Rate Limiting & Protection**: Added `RateLimiterPort` and `slowapi`/`limits` integration for FastAPI route protection (Issue #58).
* **Two-Way CQRS Middleware**: Introduced `InOutMiddleware` template base class and migrated pipeline interceptors for bidirectional lifecycle wrapping (Issue #56).
* **Caching & Resilience**: Added Redis and Valkey `CachePort` & `AsyncCachePort` adapters (Issue #57), persistent `diskcache` L2 storage, and multi-process transactional outbox filelock (Issue #32).
* **Ultra-Fast Serialization & Retries**: Added `msgspec` JSON encoding/decoding and `stamina` exponential backoff resilience middleware (Issue #38).
* **Dogfooded Developer Tools (`hexastack-tools`)**: Added `gh-pr-examine`, `gh-code-scanning`, `codeql-scan`, `generate-usage-docs`, and automated monorepo release automation.

## v0.1.0 (2026-08-27)

### Highlights & Features
* **Modular Monorepo Architecture**: 15 cohesive, decoupled hexagonal architecture microservice packages (`core`, `cqrs`, `logging`, `fastapi`, `db`, `auth`, `events`, `ai`, `mcp`, `flags`, `graphql`, `grpc`, `otel`, `cli`, and `hexastack` umbrella).
* **Dual Execution Pipelines**: Pure sync and high-throughput `asyncio` execution flows across all ports and middleware with automatic sync/async bridging.
* **Pluggable Transports**: Built-in first-class adapters for FastAPI REST API, gRPC (Protobuf reflection), GraphQL (Strawberry), MCP AI Agent tools, and Event Buses (CloudEvents + Outbox).
* **Enterprise Security & Identity**: JWT & RBAC with OPA and OpenFGA policy evaluation, Argon2id password hashing, and SPIFFE/SPIRE workload attestation.
* **Multi-Backend Persistence**: Async SQLAlchemy 2.0 repository with transaction isolation, Unit of Work middleware, and in-memory vector embeddings with cosine similarity.
* **360° Quality & Verification Rigor**: 100% OpenSSF Best Practices Silver Badge, Hypothesis property-based fuzzing, 90%+ code coverage, import-linter boundary gates, mutation testing triage, and automated SPDX & CycloneDX SBOM generation.
