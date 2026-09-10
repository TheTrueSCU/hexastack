# AI Guardrails & Agent Pair Programming Context

> **Architectural Guardrails in Practice**: This document serves as the primary local protocol handbook and memory context for AI coding assistants (such as Antigravity / Gemini / Claude). It defines the active constraints, hexagonal invariants, and developer tooling that prevent AI drift.  This can serve as the basis of `GEMINI.md` or the equivalent for a given AI coding assistant.

---

## 1. Project Standards & Invariants

1. **Architecture & Hexagonal Boundaries**:
   - `domain/` contains models, entities, and pure business logic (no external dependencies).
   - `ports/` defines abstract ABC interfaces (`@abstractmethod`).
   - `adapters/` contains concrete implementations (e.g. database, HTTP, Redis, buses). Adapters must **never** import from `infra/`.
   - `infra/` contains pipeline orchestrators, registries, middlewares, and bootstrap logic.
   - Enforced by `import-linter` via `uv run import-linter-run` or pre-commit.

2. **Docstrings & Public APIs**:
   - Every public module, class, method, and function must have **Google-style docstrings**.
   - Must include `Args:`, `Returns:`, `Raises:`, and a **`Notes/Architectural Intent:`** section documenting design decisions and invariants.

3. **`__all__` Integrity**:
   - Every `__all__` list must be strictly sorted alphabetically (casefold ordering).
   - Enforced by `check-all-statements`. Auto-fix with `uv run fix-all-statements -p <package>` or `uv run fix-all-statements -a`.

4. **Testing Rigor & Parity**:
   - Every `src/<pkg>/<path>.py` file requires a matching `tests/unit/<path>/test_<name>.py` and `__init__.py`.
   - Pre-commit quality gate checks test symmetry and fails if parity is broken.
   - Target test coverage is $\ge 90\%$.
   - When writing assertions in tests, assign method return values to variables first (e.g., `res = cache.delete("key"); assert res is True`) to prevent CodeQL *"assert statement with side-effect"* warnings.

---

## 2. Developer Tools & Workspace Commands

### GitHub & PR Diagnostic Tools
| Tool Command | Purpose |
|---|---|
| `uv run gh-pr-examine <pr-number>` | Single-step PR dashboard inspecting CI check runs, review threads, and conclusion. |
| `uv run gh-pr-examine <pr-number> --details` | Expands review threads and full comment body snippets. |
| `uv run gh-pr-examine --watch` | Continuously polls CI check status until completion. |
| `uv run gh-checks <pr-number>` | Lists detailed GitHub Actions status checks and run conclusions. |
| `uv run gh-repo [owner/repo]` | Inspects GitHub repository settings, Actions permissions, and environments. |
| `uv run gh-code-scanning` | Queries CodeQL alerts and scanning status. |
| `uv run gh-security` | Summarizes GitHub security advisories and Dependabot alerts. |

### Mutation Testing & Coverage Fortification Tools
| Tool Command | Purpose |
|---|---|
| `uv run mutmut-run -p <pkg>` | Runs mutation testing scoped to a specific package. |
| `uv run mutmut-run -p <pkg> -r` | Clears package cache and re-runs mutation tests from scratch. |
| `uv run mutmut-run -a` | Sequentially executes mutation testing across all workspace packages. |
| `uv run mutmut-inspect --summary` | High-level triage summary of surviving mutants (Critical, Equivalent, Ignorable). |
| `uv run mutmut-inspect -p <pkg> -a` | Displays actionable critical surviving mutants for a package. |
| `uv run mutmut-inspect -p <pkg> -a -c` | Correlates surviving mutants with `.coverage` to show covering test functions. |
| `uv run pytest-run -p <pkg>` | Runs pytest for a specific package with dynamic xdist and coverage. |
| `uv run pytest-run -e <example>` | Runs pytest for an example project (e.g. `financial-ledger`), configuring `PYTHONPATH` automatically. |
| `uv run pytest-run --with-context` | Runs tests capturing per-test execution contexts into `.coverage`. |
| `uv run pytest-boundary-audit` | Audits test suites for branch boundary and edge-case assertions. |
| `uv run pytest-redundancy-audit` | Analyzes test execution overlap and flags duplicate test paths. |
| `uv run pytest-impact` | Selectively runs tests impacted by current git diff changes. |
| `uv run inline-snapshot-update` | Updates inline snapshots across workspace test suites. |

### Governance, Architecture & Packaging Tools
| Tool Command | Purpose |
|---|---|
| `uv run check-all-statements` | Validates that `__all__` is sorted and deduplicated across all packages. |
| `uv run fix-all-statements -p <pkg>` | Auto-formats and alphabetizes `__all__` in a specific package. |
| `uv run fix-all-statements -a` | Auto-formats and alphabetizes `__all__` across all packages. |
| `uv run check-test-parity` | Validates 1:1 symmetry between `src/` modules and `tests/unit/` files. |
| `uv run check-extras-parity` | Audits subpackage optional extras forwarding into umbrella packaging. |
| `uv run deps-audit` | Unified dependency runner (deptry + extras parity audit across workspace). |
| `uv run deps-audit --diagrams` | Regenerates Pydeps architecture SVGs and Mermaid extras dependency graph. |
| `uv run import-linter-run` | Validates package and hexagonal architecture layer boundaries. |
| `uv run deptry-run` | Audits declared dependencies, unused deps, and transitive dependencies across packages. |
| `uv run generate-usage-docs --check` | Verifies whether USAGE.md files are up to date with CLI entrypoints. |
| `uv run generate-usage-docs --fix` | Regenerates and formats USAGE.md files for tools and umbrella CLI. |
| `uv run pypi-build` | Builds sdist and wheel packages for distribution. |
| `uv run pypi-check` | Validates package build distributions and PyPI release version status. |
| `uv run pypi-publish` | Smart PyPI publisher skipping existing releases and handling rate limits. |
| `uv run medium-publish <slug>` | Two-pass article publisher (DEV.to draft/publish, doc link resolution, Medium syndication helper). |
| `uv run codeql-scan` | Runs local CodeQL database creation and query scanning. |
| `uv run ruff check packages/<pkg>` | Runs Ruff linter on target package. |
| `uv run ty check packages/<pkg>/src` | Fast static type analysis with Ty. |

### Knowledge Graph & Architecture Navigation (Graphify)
| Tool Command | Purpose |
|---|---|
| `graphify query "<question>"` | Performs BFS traversal across the codebase knowledge graph for conceptual or architectural questions. |
| `graphify query "<question>" --dfs` | Performs DFS traversal to trace deep execution paths through layers. |
| `graphify path "<SymbolA>" "<SymbolB>"` | Finds the shortest dependency / invocation path between two components across packages. |
| `graphify explain "<Symbol>"` | Retrieves a structured architectural summary of a node and its neighborhood. |
| `graphify update .` | Incrementally synchronizes `graphify-out/graph.json` after code changes (AST-only, 0 token cost). |
| `graphify export html` | Re-exports the interactive community visualization to `graphify-out/graph.html`. |

---

## 3. GitHub PR & CI Inspection Shortcuts

When diagnosing GitHub Actions CI runs or review threads:

```bash
# 1. View overall PR status & checks
gh pr view <pr-number>
gh pr checks <pr-number>

# 2. View failed logs for a specific GitHub workflow run
gh run view <run-id> --log-failed

# 3. View inline review comments and CodeQL scanning alerts on a PR
gh api repos/TheTrueSCU/hexastack/pulls/<pr-number>/comments

# 4. List recent workflow runs for a specific branch
gh run list --branch <branch-name>
```

---

## 4. Active Packages in Workspace

- `hexastack-core`: Primitives, ports, events, domain models, caching, rate limiting, and in-memory adapters.
- `hexastack-cqrs`: Command and Query execution pipelines, registries, buses, and middleware.
- `hexastack-fastapi`: FastAPI presentation layer, CQRS routing, rate limiting (`slowapi`/`limits`), auth, and UI.
- `hexastack-db`: Sync/Async SQLAlchemy and SQLModel repositories and UnitOfWork adapters.
- `hexastack-events`: Distributed events, CloudEvent envelopes, NATS JetStream, Huey, Apprise, and Janus bridge.
- `hexastack-flags`: Dynamic feature flagging adapters (OpenFeature, Redis, YAML, env).
- `hexastack-graphql`: Strawberry GraphQL schema registration, queries, and mutations.
- `hexastack-grpc`: Protobuf and gRPC service adapters, interceptors, and decorators.
- `hexastack-ai`: LLM agents, memory adapters, and tool executors.
- `hexastack-auth`: Authentication, JWT/OAuth2 token validation, and RBAC policies.
- `hexastack-logging`: Structured JSON logging and Logfire tracing.
- `hexastack-otel`: OpenTelemetry metrics and distributed tracing instrumentation.
- `hexastack-tools`: Internal developer tooling (`gh-pr-examine`, `check-all-statements`, linters, smart PyPI publisher).
- `hexastack-ui`: Interactive NiceGUI DevTools console, command dispatcher, and telemetry visualizer.
- `hexastack-cli`: CLI scaffolding engine and Typer driving adapters.
