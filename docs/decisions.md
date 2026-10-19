# Architectural Decision Records (ADRs) & Infrastructure Invariants

> **Scope**: Authoritative historical log of foundational architectural decisions, structural constraints, and infrastructure invariants governing **Hexastack** and its federated ecosystem.
>
> This document captures **why** specific paradigms were chosen, **what was rejected**, and the **machine gates** that physically prevent architectural drift. It serves as persistent memory across developer onboarding, release cycles, and AI pair-programming sessions.

---

## Decision Index

| ADR ID | Title | Date / Milestone | Status | Key Invariant |
|---|---|---|---|---|
| [**ADR-001**](#adr-001-strict-hexagonal-layer-boundaries--import-linter-enforcement) | Strict Hexagonal Layer Boundaries & Import-Linter Enforcement | 2026-09-03 (`v0.3.0`) | **Accepted** | `domain/` has 0 external dependencies; enforced via `import-linter`. |
| [**ADR-002**](#adr-002-dynamic-inversion-of-control-via-rodi-and-visitor-scanning) | Dynamic IoC via `rodi` and Single-Pass Visitor Scanning | 2026-08-27 (`v0.1.0`) | **Accepted** | No global singletons or module state; pure composable container DI. |
| [**ADR-003**](#adr-003-multi-transport-universal-cqrs-bus-with-protocol-neutrality) | Multi-Transport Universal CQRS Bus with Protocol Neutrality | 2026-08-27 (`v0.1.0`) | **Accepted** | Single `@command_handler` serves REST, gRPC, GraphQL, MCP, and CLI. |
| [**ADR-004**](#adr-004-dual-implementation-oracle-testing--hypothesis-state-fuzzing) | Dual-Implementation Oracle Testing & Hypothesis State Fuzzing | 2026-09-05 (`v0.3.1`) | **Accepted** | Stateful adapters cross-evaluated against naive Python oracles ($f_{\text{prod}} \equiv f_{\text{oracle}}$). |
| [**ADR-005**](#adr-005-decoupled-quality--governance-tooling-via-standalone-hexaqual) | Decoupled Quality & Governance Tooling via Standalone `hexaqual` | 2026-09-14 (`v0.5.0`) | **Accepted** | Developer tools isolated into standalone `hexaqual` dev dependency. |
| [**ADR-006**](#adr-006-distributed-saga-orchestration-via-hexaflow-dag-engine) | Distributed Saga Orchestration via Hexaflow DAG Engine | 2026-09-10 (`v0.4.0`) | **Accepted** | Multi-step workflows pair forward steps with backward `on_failure` compensations. |
| [**ADR-007**](#adr-007-ambient-context-propagation-for-distributed-tracing--tenancy) | Ambient Context Propagation for Distributed Tracing & Tenancy | 2026-08-27 (`v0.1.0`) | **Accepted** | Context variables propagate spans and correlation IDs without signature pollution. |
| [**ADR-008**](#adr-008-zero-trust-dark-microservice-hosting-via-openziti--zrok) | Zero-Trust Dark Microservice Hosting via OpenZiti & zrok | 2026-09-28 (`v0.6.0`) | **Accepted** | Services can bind dark overlay networks without public inbound listening ports. |
| [**ADR-009**](#adr-009-chapterized-visual-narration--sliced-demo-generation) | Chapterized Visual Narration & Sliced Demo Generation | 2026-10-15 (`v0.9.0`) | **Accepted** | `CliNarrator.checkpoint_segment()` and Hexaflow DAGs slice tutorial demos into chapters. |
| [**ADR-010**](#adr-010-typo-tolerant-non-interactive-safe-cli-via-typersuggest) | Typo-Tolerant, Non-Interactive Safe CLI via `TyperSuggest` | 2026-10-17 (`v0.9.0`) | **Accepted** | Levenshtein suggestion with negative number immunity and non-interactive CI fallback. |
| [**ADR-011**](#adr-011-strict-wcag-21-aa-ui-accessibility-invariants-via-axe-core) | Strict WCAG 2.1 AA UI Accessibility Invariants via `axe-core` | 2026-09-22 (`v0.6.0`) | **Accepted** | NiceGUI DevTools console must pass Playwright + `axe-core` with 0 critical/serious errors. |
| [**ADR-012**](#adr-012-lockstep-monorepo-versioning-across-all-18-subpackages) | Lockstep Monorepo Versioning Across All 18 Subpackages | 2026-08-27 (`v0.1.0`) | **Accepted** | All 18 workspace subpackages bump version in lockstep to avoid dependency matrix hell. |
| [**ADR-013**](#adr-013-model-context-protocol-mcp-as-first-class-driving-adapter) | Model Context Protocol (MCP) as First-Class Driving Adapter | 2026-09-10 (`v0.4.0`) | **Accepted** | LLM agents drive CQRS handlers via standardized, hardened MCP server bridges. |
| [**ADR-014**](#adr-014-lifecycle-managed-scaffolding-via-copier-and-devcontainers) | Lifecycle-Managed Scaffolding via Copier and Devcontainers | 2026-10-18 (`v0.9.0`) | **Accepted** | Projects scaffolded via Copier retain answers to enable downstream `copier update`. |

---

### ADR-001: Strict Hexagonal Layer Boundaries & Import-Linter Enforcement

- **Date & Milestone**: 2026-09-03 (`v0.3.0`, commit `e2cd6ea`)
- **Status**: Accepted
- **Context & Problem Statement**:
  In Python microservices, domain logic frequently becomes corrupted by framework dependencies (e.g., importing FastAPI `Request`, SQLAlchemy `Session`, or Pydantic serialization helpers directly inside domain entities). Over time, this leads to circular dependencies, untestable core logic, and prevents switching persistence engines or transport layers.
- **Decision**:
  Enforce a strict 4-tier Hexagonal layer model with hardware-enforced directional constraints:
  - `domain/`: Pure business models and entities with **0** external framework dependencies.
  - `ports/`: Pure abstract base interfaces (`abc.ABC`) defining inbound driving ports and outbound driven ports.
  - `adapters/`: Concrete technological implementations (SQLAlchemy, Redis, FastAPI, gRPC, NATS). Adapters may **never** import from `infra/`.
  - `infra/`: Dependency injection wiring, runtime registries, and application bootstrap logic.
- **The Invariant ("The Why")**:
  If a domain model imports Typer, FastAPI, or SQLAlchemy, or an adapter imports application assembly logic from `infra/`, the software architecture has failed.
- **Alternatives Considered & Rejected**:
  - *Pydantic models in `domain/`*: Rejected because coupling domain validation to Pydantic v1/v2 breaking changes and serialization decorators leaks framework concerns into pure business rules.
  - *Convention-only documentation*: Rejected because without a compiler or linter, human and AI contributors silently introduce cross-layer shortcuts within weeks.
- **Enforcement Mechanism**:
  - Enforced by `.importlinter` via `uv run hexaqual imports check` and pre-commit Git hooks.
  - Architectural tests in each package: `tests/architecture/test_hexagonal_boundaries.py`.

---

### ADR-002: Dynamic Inversion-of-Control via `rodi` and Visitor Scanning

- **Date & Milestone**: 2026-08-27 (`v0.1.0`)
- **Status**: Accepted
- **Context & Problem Statement**:
  Python applications commonly rely on global singleton variables, module-level state, or web-framework-specific dependency injection (like FastAPI's `Depends`). Global state causes test suite pollution and concurrency races, while framework DI locks dependency injection to HTTP requests only.
- **Decision**:
  Adopt `rodi` as the unified IoC / Dependency Injection container combined with a single-pass reflection scanner. Service bootstrapping is explicit, declarative, and isolated to `infra/di.py`.
- **The Invariant ("The Why")**:
  Handlers and adapters must be fully instantiable and testable in hermetic unit tests simply by passing mock or in-memory port implementations to their constructors without monkeypatching `unittest.mock.patch`.
- **Alternatives Considered & Rejected**:
  - *FastAPI `Depends`*: Rejected as the primary DI mechanism because CLI commands, gRPC workers, event consumers, and MCP tools cannot access FastAPI request-scoped dependency graphs.
  - *Global singleton instances*: Rejected due to test-isolation leaks and thread/coroutine state bleeding.
- **Enforcement Mechanism**:
  - DI container tests in `hexastack-core/tests/unit/test_di.py`.
  - Sanity check verifying that all adapters accept ports via `__init__`.

---

### ADR-003: Multi-Transport Universal CQRS Bus with Protocol Neutrality

- **Date & Milestone**: 2026-08-27 (`v0.1.0`)
- **Status**: Accepted
- **Context & Problem Statement**:
  Exposing the same business capability across REST endpoints, command-line tools, gRPC RPCs, and AI tools typically requires writing duplicate controllers, request parsers, and validation layers for each protocol.
- **Decision**:
  Decouple execution into Command Query Responsibility Segregation (CQRS). A single `@command_handler` or `@query_handler` acts as the sole implementation of a domain capability. Driving adapters (FastAPI, Typer CLI, Strawberry GraphQL, gRPC, and MCP) simply transform incoming transport envelopes into a CQRS Command/Query object and dispatch it onto the `MessageBus`.
- **The Invariant ("The Why")**:
  Business logic exists in exactly one place. Adding a new transport (e.g. MCP for Claude/Gemini) requires 0 changes to domain entities or application command handlers.
- **Alternatives Considered & Rejected**:
  - *Fat route handlers*: Putting business logic inside FastAPI `@app.post()` routes. Rejected because CLI and gRPC cannot invoke route handlers without fabricating fake HTTP requests.
- **Enforcement Mechanism**:
  - CQRS bus pipeline tests in `hexastack-cqrs`.
  - Multi-transport integration tests verifying identical outcomes across HTTP, CLI, and gRPC.

---

### ADR-004: Dual-Implementation Oracle Testing & Hypothesis State Fuzzing

- **Date & Milestone**: 2026-09-05 (`v0.3.1`)
- **Status**: Accepted
- **Context & Problem Statement**:
  Unit tests with handwritten mocks often achieve high "code coverage" while asserting nothing of substance ("mocking that a mock was called"). When complex adapters (like an SQLite outbox, Redis cache, or rate limiter) encounter concurrency or edge-case state sequences, subtle data corruption bugs occur.
- **Decision**:
  Adopt **Dual-Implementation Oracle Testing** powered by Hypothesis stateful testing (`RuleBasedStateMachine`). Stateful production adapters are cross-evaluated against naive, mathematically obvious in-memory Python references to prove equivalence:
  $$f_{\text{prod}}(x) \equiv f_{\text{oracle}}(x)$$
- **The Invariant ("The Why")**:
  An adapter cannot be declared production-ready based solely on static tests. It must withstand thousands of pseudo-random, interleaved operations (inserts, updates, deletes, rollbacks, concurrent leases) and produce outputs identical to the reference oracle.
- **Alternatives Considered & Rejected**:
  - *Static fixture assertions*: Rejected because hand-crafted fixtures only test the scenarios the author anticipated.
- **Enforcement Mechanism**:
  - Fuzzing suites located in `packages/<pkg>/tests/fuzz/` and `tests/properties/`.
  - Executed in CI via `uv run hexaqual test fuzz` and `uv run hexaqual test run -P`.

---

### ADR-005: Decoupled Quality & Governance Tooling via Standalone `hexaqual`

- **Date & Milestone**: 2026-09-14 (`v0.5.0`, commit `effbfa5`)
- **Status**: Accepted
- **Context & Problem Statement**:
  Quality tools, Git hook managers, test parity validators, and release scripts initially lived inside `packages/hexastack_tools`. As the federated ecosystem grew to include `hexaflow`, `hexaqueue`, and `hexastack-template`, having governance scripts locked inside Hexastack created circular dependencies and tooling drift.
- **Decision**:
  Extract all quality, governance, and release engineering tooling into a standalone, independently versioned package: [**`hexaqual`**](https://github.com/TheTrueSCU/hexaqual) (`hexaqual[all]>=0.9.0`), integrated into Hexastack via dev dependencies and the lightweight `hexastack-qual` adapter package.
- **The Invariant ("The Why")**:
  All repositories across the `hexa-` family must execute identical quality gates (`hexaqual sanity`), identical Git lifecycle hooks, and identical release reproducibility checks from a unified, external authority.
- **Alternatives Considered & Rejected**:
  - *In-tree git submodules*: Rejected due to submodule synchronization friction and developer ergonomic issues.
  - *Duplicate bash scripts per repository*: Rejected because security, linting, and AST tooling rules immediately drift out of sync.
- **Enforcement Mechanism**:
  - `uv run hexaqual sanity -a` in pre-commit and CI workflows.
  - `hexaqual agents sync` maintaining agent rules in lockstep.

---

### ADR-006: Distributed Saga Orchestration via Hexaflow DAG Engine

- **Date & Milestone**: 2026-09-10 (`v0.4.0`, commit `2a7844b`)
- **Status**: Accepted
- **Context & Problem Statement**:
  Coordinating multi-service distributed transactions (e.g. order placement, payment capture, inventory reservation) via ad-hoc event choreography makes compensating rollbacks unpredictable, prone to state leaks, and impossible to debug when a node fails mid-transaction.
- **Decision**:
  Consolidate all distributed saga orchestration into explicit Directed Acyclic Graphs (DAGs) powered by [**`hexaflow`**](https://github.com/TheTrueSCU/hexaflow). Workflows register forward steps paired with deterministic backward compensations (`on_failure`), middleware telemetry (`StepMiddlewarePort`), and SQLite Memento crash-recovery checkpoints.
- **The Invariant ("The Why")**:
  A failure at any step in a distributed transaction must trigger backward compensations in reverse topological order, guaranteeing zero partial-state leaks. Long-running executions must be inspectable (`hexaflow status <run_id>`) and resumable from durable checkpoints (`hexaflow resume <run_id>`).
- **Alternatives Considered & Rejected**:
  - *Two-Phase Commit (2PC)*: Rejected due to blocking coordinator locks, latency, and single points of failure in distributed microservices.
  - *Choreographed Kafka events*: Rejected because visualizing the distributed state machine and verifying rollback guarantees becomes unmanageable across distributed workers.
- **Enforcement Mechanism**:
  - `hexastack-flow` workflow runner and saga simulation tests (`tests/e2e/test_devtools_ui.py`).
  - Hermetic compensation verification in `hexaflow` (`tests/unit/test_saga_compensation.py`).

---

### ADR-007: Ambient Context Propagation for Distributed Tracing & Tenancy

- **Date & Milestone**: 2026-08-27 (`v0.1.0`)
- **Status**: Accepted
- **Context & Problem Statement**:
  Passing correlation IDs, tenant identifiers, and OpenTelemetry spans through dozens of function arguments across layers pollutes pure domain method signatures with infrastructure bookkeeping.
- **Decision**:
  Use Python `contextvars` to manage an **Ambient Context Engine**. Request middleware populates the context at entrypoints (HTTP, gRPC, CLI, MCP), and downstream loggers, tracer spans, and database connection pools ambiently read from the context without explicit parameter threading.
- **The Invariant ("The Why")**:
  Domain business methods must not accept `correlation_id: str` or `span: trace.Span` in their signatures. Tracing and correlation are ambient infrastructure concerns.
- **Alternatives Considered & Rejected**:
  - *Threading correlation arguments everywhere*: Rejected due to severe signature bloat and violation of domain isolation.
  - *Thread-local storage (`threading.local`)*: Rejected because `threading.local` corrupts state across async/await coroutine switches in `asyncio`.
- **Enforcement Mechanism**:
  - Ambient context tests in `hexastack-core/tests/unit/test_context.py`.
  - OpenTelemetry span propagation assertions in `hexastack-otel`.

---

### ADR-008: Zero-Trust Dark Microservice Hosting via OpenZiti & zrok

- **Date & Milestone**: 2026-09-28 (`v0.6.0`, commit `50f5d37`, `880efb1`)
- **Status**: Accepted
- **Context & Problem Statement**:
  Deploying internal microservices often requires managing complex VPNs, public ingress controllers, cloud firewall rules, or exposing public inbound IP addresses that invite bot scanning and attack surfaces.
- **Decision**:
  Incorporate native Zero-Trust overlay networking adapters (`OpenZitiASGIAdapter`, `AsyncSshAdapter`, and `zrok`) into `hexastack-fastapi`. Services can bind directly to programmable zero-trust overlays without opening public listening ports on the host.
- **The Invariant ("The Why")**:
  Services can be completely "dark" to the public internet while securely serving authenticated clients, distributed workers, and peer microservices with end-to-end cryptographic mutual TLS.
- **Alternatives Considered & Rejected**:
  - *Standard reverse proxies (Nginx/Traefik) with public IPs*: Rejected because exposed open ports remain vulnerable to zero-day vulnerabilities and DDoS attacks.
- **Enforcement Mechanism**:
  - `OpenZitiASGIAdapter` and `RemoteExecutionPort` unit and integration tests.

---

### ADR-009: Chapterized Visual Narration & Sliced Demo Generation

- **Date & Milestone**: 2026-10-15 (`v0.9.0`, commits `3422fc4`, `1438fcc`)
- **Status**: Accepted
- **Context & Problem Statement**:
  Monolithic 5-minute video demos suffer from severe viewer drop-off. Furthermore, when generating automated end-to-end tutorial videos in CI, a test failure in Chapter 6 required re-executing Chapters 1–5 from scratch, causing massive pipeline delays.
- **Decision**:
  Adopt **Hexaflow-orchestrated demo pipelines** with `CliNarrator.checkpoint_segment()`. Long-running tutorial journeys are modeled as discrete DAG stages that flush sliced `.webm` videos and synchronized millisecond-accurate `.vtt` caption tracks at chapter boundaries while preserving execution state.
- **The Invariant ("The Why")**:
  Videos must be consumable in bite-sized chapters (<60 seconds). Flaky or failed recordings must resume from the last successful checkpoint via `hexaflow resume <run_id>` without re-recording earlier segments.
- **Alternatives Considered & Rejected**:
  - *Single monolithic `.webm` recordings*: Rejected due to high cognitive overload for users and slow, all-or-nothing CI re-runs.
- **Enforcement Mechanism**:
  - `hexastack_cli.testing.CliNarrator` segment assertions.
  - Pre-commit file size gates (`check-added-large-files` with `--maxkb=5120`).

---

### ADR-010: Typo-Tolerant, Non-Interactive Safe CLI via `TyperSuggest`

- **Date & Milestone**: 2026-10-17 (`v0.9.0`, commit `18ac92c`, PR #218)
- **Status**: Accepted
- **Context & Problem Statement**:
  Command-line interfaces across Hexastack (`hexastack`, `hexaqual`, `hexaflow`, `hq`) have deep subcommand hierarchies and rich option flags. A user mistyping a single character (e.g. `--prt=8000`) receives an abrupt Click error without guidance.
- **Decision**:
  Replace standard `typer.Typer` with **`TyperSuggest`** as a drop-in replacement. It intercepts unrecognized commands and flags, calculates Levenshtein string distances, preserves inline assignments (`--flag=value`), provides interactive prompts in terminals, and falls back cleanly to stderr with exit code `2` in non-interactive CI environments without hanging.
- **The Invariant ("The Why")**:
  - CI pipelines and automated scripts must **never** hang waiting for user stdin.
  - Negative numbers (e.g. `-1`, `-0.5`) must never be mistakenly treated as unknown option flags.
  - An explicit `--` token strictly halts flag processing.
- **Alternatives Considered & Rejected**:
  - *Standard Typer/Click defaults*: Rejected due to poor developer ergonomics and zero discoverability for typos.
  - *External unmaintained Click plugins*: Rejected due to missing negative number immunity and potential hanging in CI pipelines.
- **Enforcement Mechanism**:
  - Comprehensive unit suite: `packages/hexastack_cli/tests/unit/adapters/suggest/test_suggest.py`.
  - Non-interactive TTY detection checks.

---

### ADR-011: Strict WCAG 2.1 AA UI Accessibility Invariants via `axe-core`

- **Date & Milestone**: 2026-09-22 (`v0.6.0`, commit `49bf4f8`)
- **Status**: Accepted
- **Context & Problem Statement**:
  Modern developer tools and web consoles are frequently built without accessibility considerations, introducing color contrast failures, keyboard navigation traps, and missing ARIA landmarks that exclude developers using assistive technologies.
- **Decision**:
  Enforce **WCAG 2.1 AA compliance** across all NiceGUI DevTools consoles (`hexastack-ui`) and FastAPI web presentations, verified end-to-end in CI using Playwright and `axe-core`.
- **The Invariant ("The Why")**:
  Every rendered DOM view in Hexastack DevTools must pass `axe-core` analysis with **0** `critical` and **0** `serious` violations under the `['wcag2a', 'wcag2aa', 'wcag21aa']` standards tags. Icon-only buttons must declare an `aria-label` or accessible tooltip.
- **Alternatives Considered & Rejected**:
  - *Manual visual checks*: Rejected because human reviewers cannot reliably detect color contrast ratios (<4.5:1) or screen reader landmark hierarchies.
- **Enforcement Mechanism**:
  - Dedicated E2E accessibility suite: `tests/e2e/test_ui_accessibility.py`.
  - Automated agent guardrail: `.agents/rules/hexastack-accessibility.md`.

---

### ADR-012: Lockstep Monorepo Versioning Across All 18 Subpackages

- **Date & Milestone**: 2026-08-27 (`v0.1.0`)
- **Status**: Accepted
- **Context & Problem Statement**:
  In monorepos with dozens of interconnected packages, allowing individual packages to drift onto independent version numbers creates severe dependency resolution conflicts ("dependency hell") for downstream users installing multiple extras.
- **Decision**:
  Maintain all 18 subpackages in the Hexastack monorepo in strict lockstep version synchronization on minor and patch releases (e.g. `v0.9.0`).
- **The Invariant ("The Why")**:
  When an end-user runs `pip install hexastack[web,db,cqrs]`, the package manager must resolve mutually compatible, lockstep subpackage wheels without dependency graph backtracking.
- **Alternatives Considered & Rejected**:
  - *Independent semantic versioning per subpackage*: Rejected due to high cognitive overhead for consumers and brittle dependency resolution across 18 packages.
- **Enforcement Mechanism**:
  - Verified by `hexaqual parity extras` and root release build scripts.
  - Automated version bump checklist in release engineering workflow.

---

### ADR-013: Model Context Protocol (MCP) as First-Class Driving Adapter

- **Date & Milestone**: 2026-09-10 (`v0.4.0`, commit `94f8b2c`)
- **Status**: Accepted
- **Context & Problem Statement**:
  Integrating LLM coding agents and AI assistants typically involves writing custom, vendor-specific function-calling glue code that bypasses application authorization and validation layers.
- **Decision**:
  Implement the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) as a first-class driving adapter package (`hexastack-mcp`). The MCP server exposes CQRS command and query handlers directly as structured tools for Claude, Gemini, and Antigravity, complete with parameter validation and SSE security controls.
- **The Invariant ("The Why")**:
  An AI agent interacting with Hexastack must pass through the exact same CQRS validation, rate limiting, and authorization middleware pipelines as an HTTP REST client or gRPC worker.
- **Alternatives Considered & Rejected**:
  - *Model-specific prompt injections / ad-hoc tool dictionaries*: Rejected because they fail to enforce security boundaries and require rewriting for each new AI model provider.
- **Enforcement Mechanism**:
  - `packages/hexastack_mcp/tests/unit/test_mcp.py` verifying tool registration, parameter injection defense, and authentication.

---

### ADR-014: Lifecycle-Managed Scaffolding via Copier and Devcontainers

- **Date & Milestone**: 2026-10-18 (`v0.9.0`, commit `da9d835`)
- **Status**: Accepted
- **Context & Problem Statement**:
  Static starter templates (`git clone` or traditional Cookiecutter generators) become technical debt immediately after instantiation. When the upstream framework releases security patches, updated CI workflows, or performance improvements, downstream projects have no clean way to pull those changes.
- **Decision**:
  Standardize [`hexastack-template`](https://github.com/TheTrueSCU/hexastack-template) on **Copier** with preserved `.copier-answers.yml`, paired with turnkey GitHub Codespaces devcontainer configurations.
- **The Invariant ("The Why")**:
  Downstream applications generated from the template must be able to run `uvx copier update` to pull upstream architectural improvements and dependency upgrades without overwriting their custom domain entities or business logic in `domain/`.
- **Alternatives Considered & Rejected**:
  - *Traditional Cookiecutter generation*: Rejected because Cookiecutter is a one-way generation tool with zero ongoing lifecycle update capabilities.
- **Enforcement Mechanism**:
  - Canary drift monitoring workflow: `.github/workflows/canary.yml` in `hexastack-template`.
  - Automated Copier instantiation test journey (`HT-01`).

---

## Forward Maintenance Protocol

When proposing or implementing an architectural change in Hexastack:
1. **Author a new ADR entry** before merging code, detailing: Title, Status, Decision, The Invariant, Alternatives Rejected, and Machine Enforcement.
2. **Never delete historical ADRs**: If a decision is superseded, change its status to `Superseded by ADR-00X` and record the rationale for the change.
3. **Verify Machine Gate Alignment**: Ensure the enforcement mechanism declared in the ADR is active in `hexaqual sanity` or pre-commit hooks.
