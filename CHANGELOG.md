# CHANGELOG

## v0.6.0 (2026-09-16)

### Highlights & Features
* **Interactive Terminal UI (`hexastack-ui[textual]`)**: Fullscreen interactive terminal operational dashboard built on Textual (`TextualDevToolsApp`, `TextualDevToolsPresenter`, `mount_textual_dashboard`), providing rich live inspection of CQRS contracts, runtime feature flags, DI container bindings, and middleware chains without browser or JavaScript dependencies.
* **Packaging Modernization (`importlib.resources`)**: Migrated `hexastack-ui` (`devtools.py`) static asset discovery from `Path(__file__)` to PEP 451/616 compliant `importlib.resources.files()`, ensuring full zip-safe and isolated virtual environment compliance.
* **Turnkey CI Quality Gate via Hexaqual**: Modernized `.github/workflows/ci.yml` `quality-gate` job to use `TheTrueSCU/hexaqual@v0.4.0` turnkey composite action with automated `uv`, Python, and pre-commit caching.
* **CLI Output Formatting Alignment (`hexastack-cli`)**: Standardized `OutputFormat` enum (`auto`, `json`, `markdown`, `plain`, `rich`, `table`), `format_option()` factory, and `resolve_format()` pipe-detection in `hexastack-cli` alongside markdown presentation support in `RichTerminalPresenter`, fulfilling cross-ecosystem CLI alignment with `hexaqual` and `hexaqueue`.
* **Workflow Engine Upgrade (`hexaflow>=0.3.0`)**: Upgraded `hexastack-flow` dependency to `hexaflow>=0.3.0`, introducing dynamic step mapping (`@wf.map_step`), runtime collection fan-out, dependency inference, and Mermaid/ASCII DAG exporters.
* **Quality Suite Upgrade (`hexaqual>=0.4.0`)**: Upgraded workspace dev toolchain to `hexaqual[all]>=0.4.0`.
* **Unified Workspace Lockstep Versioning (v0.6.0)**: Synchronized version bump across root workspace and all 17 subpackages (`hexastack`, `hexastack_ai`, `hexastack_auth`, `hexastack_cli`, `hexastack_core`, `hexastack_cqrs`, `hexastack_db`, `hexastack_events`, `hexastack_fastapi`, `hexastack_flags`, `hexastack_flow`, `hexastack_graphql`, `hexastack_grpc`, `hexastack_logging`, `hexastack_mcp`, `hexastack_otel`, `hexastack_ui`).

## v0.5.0 (2026-09-14)

### Highlights & Features
* **Tooling Extraction & Modularization (`hexaqual`)**: Formally extracted internal `hexastack-tools` into the standalone [`hexaqual`](https://github.com/TheTrueSCU/hexaqual) quality, governance, and release engineering toolchain (`hexaqual[all]>=0.3.0`). Subsumed all legacy CLI entrypoints into unified, CQRS-dispatched commands (`hexaqual sanity`, `hexaqual parity`, `hexaqual mutate`, `hexaqual release`, `hexaqual gh`, `hexaqual statements`).
* **Workflow Engine Extraction & Integration (`hexaflow`)**: Extracted declarative DAG execution and orchestration primitives into the standalone [`hexaflow`](https://github.com/TheTrueSCU/hexaflow) engine (`hexaflow>=0.2.0`), powering `hexastack-flow` with durable saga orchestration, `TriggerRule.ALL_SUCCESS_OR_SKIPPED` skip propagation, and dynamic Typer CLI binding (`WorkflowCliBinder`).
* **Colocated Dynamic Fuzz Harnesses**: Relocated root fuzz harnesses into package test suites (`packages/hexastack_logging/tests/fuzz/test_fuzz_log_sanitizer.py` and `packages/hexastack_grpc/tests/fuzz/test_fuzz_proto_compiler.py`), supported by dynamic fuzz discovery in `hexaqual test fuzz`.
* **Full Architectural Test Parity**: Added dedicated hexagonal boundary tests (`test_hexagonal_boundaries.py`) across all 17 packages, including `hexastack_flow` and `hexastack_ui`, verified by `hexaqual parity architecture`.
* **Dynamic Package Boundary Verification**: Updated `tests/architecture/test_package_boundaries.py` with dynamic package discovery and validation across all workspace packages.
* **Unified Workspace Lockstep Versioning (v0.5.0)**: Synchronized version bump across root workspace and all 17 packages (`hexastack`, `hexastack_ai`, `hexastack_auth`, `hexastack_cli`, `hexastack_core`, `hexastack_cqrs`, `hexastack_db`, `hexastack_events`, `hexastack_fastapi`, `hexastack_flags`, `hexastack_flow`, `hexastack_graphql`, `hexastack_grpc`, `hexastack_logging`, `hexastack_mcp`, `hexastack_otel`, `hexastack_ui`).

## v0.4.0 (2026-09-10)

### Highlights & Features
* **Interactive DevTools & UI Presentation (`hexastack-ui`)**: Extracted NiceGUI reactive UI presentation primitives and the interactive DevTools dashboard from `hexastack-fastapi` into a dedicated presentation package (`hexastack-ui`) with standalone CSS styling and Biome code quality integration (Issue #100, PR #111).
* **Apache Kafka & Redpanda Event Bus (`hexastack-events`)**: Introduced high-throughput distributed event bus adapter supporting consumer group partition rebalancing, CloudEvents 1.0 framing, dead-letter routing, and graceful connection lifecycle management (Issue #75, PR #119).
* **AI Agent Long-Term Memory & Semantic CQRS Caching (`hexastack-ai`)**: Added vector database memory adapters (`VectorMemoryPort`, `AsyncVectorMemoryPort`, `InMemoryVectorMemoryAdapter`, `QdrantVectorMemoryAdapter`, and `PgVectorMemoryAdapter` bridge) alongside semantic CQRS query caching (`SemanticVectorCache`, `SemanticQueryCacheMiddleware`) with similarity thresholds, TTL expiration, and `hexastack[qdrant]` extra forwarding (Issue #78).
* **Command Aliases (`hs` / `HQ`)**: Added fast command-line aliases `hs` (equivalent to `hexastack`) and `HQ` (equivalent to `hexaqueue`) to streamline developer ergonomics.
* **Hypothesis Monorepo Profile**: Standardized monorepo test profile and headless subprocess isolation to ensure deterministic 92%+ coverage execution.
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
