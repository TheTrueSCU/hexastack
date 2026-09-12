# Hexastack Tools (`packages/hexastack_tools`)

Developer tooling, repository governance, code-scanning analysis, and CI automation suite for the Hexastack monorepo.

---

## 📖 Complete Documentation & Usage

For full CLI usage instructions and command examples, see the canonical [**USAGE Guide**](USAGE.md) or the [online developer documentation](file:///docs/tools.md).

---

## 🏛️ Architectural Intent & CQRS Flow

`hexastack-tools` strictly dogfoods Hexastack's hexagonal architecture and CQRS patterns across every CLI command, eliminating framework sprawl and decoupling business execution from presentation:

- **`domain/`**: Pure data contracts, typed command objects (`RunSanityCheckCommand`, `ExaminePrCommand`, `GeneratePydepsCommand`, `ScanCodeQlCommand`, etc.), and immutable domain reports (`SanityCheckReport`, `PydepsReport`, `CodeQlScanReport`, `MediumPublishReport`, etc.).
- **`ports/`**: Abstract boundary interfaces separating execution runners (`ToolRunnerPort`, `DependencyAuditorPort`, `TestingRunnerPort`, `GitHubApiPort`, `PyPiClientPort`) from formatting presenters (`SanityPresenterPort`, `GitHubPresenterPort`, `TestingPresenterPort`, `DependencyPresenterPort`, `PyPiPresenterPort`, `GeneratorPresenterPort`, `AnalysisPresenterPort`, `RefactoringPresenterPort`).
- **`adapters/runners/`**: Concrete infrastructure adapters driving subprocesses (`uv`, `ruff`, `ty`, `mutmut`, `pytest`, `atheris`, `codeql`), AST analyzers (`libcst`), or external cloud APIs (GitHub REST/GraphQL, PyPI Warehouse).
- **`adapters/presenters/`**: Decoupled presentation adapters rendering to interactive Rich ANSI dashboards, structured JSON payloads, or CI-ready GitHub Flavored Markdown (`$GITHUB_STEP_SUMMARY`).
- **`infra/handlers/`**: CQRS command handlers orchestrating execution across ports, catching infrastructure exceptions, and emitting typed domain reports.
- **`infra/bootstrap.py`**: Centralized governance command bus factory (`create_governance_bus`) that registers every command-to-handler mapping into an `InProcessCommandBus`.
- **`commands/`**: Lightweight driving CLI adapters parsing command-line flags, dispatching domain commands via the bus, and invoking selected presenters.

---

### Architecture & Invocation Lifecycle

```mermaid
flowchart TD
    subgraph Driving["1. Driving Adapters (CLI Entrypoints)"]
        direction TB
        subgraph G1["Group 1: Governance & Linting"]
            CLI_Sanity["sanity-check"]
            CLI_Complexity["complexipy-run"]
            CLI_All["check-all-statements / fix-all-statements"]
        end
        subgraph G2["Group 2: GitHub PR & CI Diagnostics"]
            CLI_GH["gh-pr-examine / gh-checks / gh-repo / gh-security / gh-code-scanning"]
        end
        subgraph G3["Group 3: Testing Rigor, Dependencies & Packaging"]
            CLI_Mut["mutmut-run / mutmut-inspect"]
            CLI_Test["pytest-run / pytest-impact / pytest-boundary-audit / pytest-redundancy-audit"]
            CLI_Deps["deps-audit / check-extras-parity / check-test-parity / import-linter-run"]
            CLI_PyPI["pypi-build / pypi-check / pypi-publish"]
        end
        subgraph G4["Group 4: Generators, Analysis & Publishing"]
            CLI_Gen["pydeps-generate / generate-usage-docs / archon-generate"]
            CLI_Analysis["codeql-scan / fuzz-run / inline-snapshot-update"]
            CLI_Refactor["fix-rope / medium-publish"]
        end
    end

    subgraph CQRS["2. Governance Command Bus & Domain Core"]
        direction TB
        Commands["Domain Commands<br/>(RunSanityCheckCommand, ExaminePrCommand, GeneratePydepsCommand, ScanCodeQlCommand...)"]
        Bus["InProcessCommandBus (create_governance_bus)"]

        subgraph Handlers["Domain Command Handlers"]
            H_Sanity["Sanity & Linter Handlers"]
            H_GH["GitHub Suite Handlers"]
            H_Test["Testing & Mutation Handlers"]
            H_Deps["Dependency & Parity Handlers"]
            H_PyPI["PyPI Release Handlers"]
            H_Gen["Generator Handlers (Pydeps, Usage Docs, Archon)"]
            H_Analysis["Analysis Handlers (CodeQL, Fuzz, Inline Snapshots)"]
            H_Refactor["Refactoring Handlers (LibCST Alphabetize, Medium Publish)"]
        end

        Reports["Domain Reports & DTOs<br/>(SanityCheckReport, PydepsReport, CodeQlScanReport, MediumPublishReport...)"]
    end

    subgraph DrivenRunners["3. Driven Execution Ports & Runners"]
        direction TB
        Port_GH["GitHubApiPort (GitHub REST / GraphQL / gh CLI)"]
        Port_Subproc["ToolRunnerPort & TestingRunnerPort (Ruff, Ty, Pytest, Mutmut, UV)"]
        Port_Deps["DependencyAuditorPort (Deptry, Extras Parity)"]
        Port_PyPI["PyPiClientPort (PyPI Warehouse API & Build Verification)"]
        Port_Engines["Engines & AST (LibCST, Atheris Fuzzer, CodeQL CLI, Graphviz Pydeps)"]
    end

    subgraph DrivenPresenters["4. Driven Presenter Ports & Multi-Format Adapters"]
        direction TB
        subgraph Ports["Presenter Abstract Ports"]
            Port_Pres["SanityPresenterPort / GitHubPresenterPort / TestingPresenterPort /<br/>DependencyPresenterPort / PyPiPresenterPort / GeneratorPresenterPort /<br/>AnalysisPresenterPort / RefactoringPresenterPort"]
        end
        subgraph Formats["Format Adapters (--format / -f)"]
            P_Rich["Rich Presenter<br/>(Interactive TTY ANSI Tables & Panels)"]
            P_JSON["JSON Presenter<br/>(Machine-Readable CI & Agent Automation)"]
            P_MD["Markdown Presenter<br/>(PR Comments & GitHub Step Summaries)"]
        end
    end

    Driving -->|1. Instantiate & Dispatch| Commands
    Commands --> Bus
    Bus -->|2. Route to Handler| Handlers
    Handlers -->|3. Query & Execute| DrivenRunners
    Handlers -->|4. Return Typed Domain Report| Reports
    Reports -->|5. Pass Report to Presenter| DrivenPresenters
    DrivenPresenters -->|6. Render to stdout & Return Exit Code| Driving
```

---

## ⚙️ Output Presentation Modes

All modernized CLI commands support multi-format presenters via `--format` / `-f`:

1. **`rich` / `table` (default)**: Colorized ANSI dashboards with status icons, panels, and live terminal styling.
2. **`json`**: Pure, machine-readable JSON payload suited for automated CI gating, scripts, and AI coding agents.
3. **`markdown`**: GitHub Flavored Markdown tables and callouts ready for GitHub Actions job summaries (`$GITHUB_STEP_SUMMARY`) or PR comments.

---

## 🛠️ Quick Command Reference

| Command | Purpose | Output Formats |
|---|---|---|
| `uv run sanity-check [-p <pkg>] [-e <ex>]` | Fast scoped pre-commit validator (Ruff, Ty, complexipy, `__all__`, test parity, pytest). | `table`, `json`, `markdown` |
| `uv run complexipy-run` | Cognitive complexity auditing across workspace. | `table`, `json`, `markdown` |
| `uv run gh-pr-examine [pr]` | Full PR dashboard inspecting checks, review threads, failed CI logs, and conclusions. | `table`, `json`, `markdown` |
| `uv run gh-checks [pr/ref]` | Detailed status checks inspector. | `table`, `json`, `markdown` |
| `uv run gh-code-scanning` | CodeQL SAST security alerts browser. | `table`, `json`, `markdown` |
| `uv run gh-repo [owner/repo]` | Inspects GitHub repository settings, Actions permissions, and environments. | `table`, `json`, `markdown` |
| `uv run gh-security [pr]` | Review comments and bot security discussion thread auditor. | `table`, `json`, `markdown` |
| `uv run mutmut-run -p <pkg>` | Scoped mutation testing runner. | `table`, `json`, `markdown` |
| `uv run mutmut-inspect --summary` | High-level triage summary of surviving mutants (Critical, Equivalent, Ignorable). | `table`, `json`, `markdown` |
| `uv run pytest-run -p <pkg>` | Runs pytest with coverage across target packages or examples. | `table`, `json`, `markdown` |
| `uv run pytest-boundary-audit` | Audits test suites for branch boundary and edge-case assertions. | `table`, `json`, `markdown` |
| `uv run pytest-redundancy-audit` | Analyzes test execution overlap and flags duplicate test paths. | `table`, `json`, `markdown` |
| `uv run pytest-impact` | Selectively runs tests impacted by current git diff changes. | `table`, `json`, `markdown` |
| `uv run check-test-parity` | Validates 1:1 mirroring between `src/` and `tests/unit/`. | `table`, `json`, `markdown` |
| `uv run check-all-statements` | Validates `__all__` alphabetical sorting. | `table`, `json`, `markdown` |
| `uv run fix-all-statements` | Automatically sorts and alphabetizes `__all__`. | `table`, `json`, `markdown` |
| `uv run check-extras-parity` | Audits subpackage optional extras forwarding into umbrella packaging. | `table`, `json`, `markdown` |
| `uv run deps-audit` | Unified dependency runner (deptry + extras parity audit across workspace). | `table`, `json`, `markdown` |
| `uv run import-linter-run` | Validates package and hexagonal architecture layer boundaries. | `table`, `json`, `markdown` |
| `uv run pypi-build` | Builds sdist and wheel packages across workspace with optional reproducible audit. | `table`, `json`, `markdown` |
| `uv run pypi-check` | Verifies build metadata and checks for PyPI release collisions. | `table`, `json`, `markdown` |
| `uv run pypi-publish` | Smart PyPI publisher skipping existing releases and handling rate limits. | `table`, `json`, `markdown` |
| `uv run pydeps-generate` | Generates Pydeps architecture dependency SVGs across packages. | `table`, `json`, `markdown` |
| `uv run generate-usage-docs` | Regenerates or checks USAGE.md documentation parity. | `table`, `json`, `markdown` |
| `uv run archon-generate` | Generates and audits Archon architecture conformance tests. | `table`, `json`, `markdown` |
| `uv run codeql-scan` | Runs local SARIF CodeQL SAST security scan. | `table`, `json`, `markdown` |
| `uv run fuzz-run` | Executes Atheris coverage-guided and OWASP security fuzz harnesses. | `table`, `json`, `markdown` |
| `uv run inline-snapshot-update` | Updates inline snapshots across workspace test suites. | `table`, `json`, `markdown` |
| `uv run fix-rope` | Sorts and alphabetizes methods and functions using LibCST. | `table`, `json`, `markdown` |
| `uv run medium-publish <slug>` | Formats, inspects status, or assists publication of Medium / DEV.to articles. | `table`, `json`, `markdown` |

For detailed syntax and flags, see [**USAGE.md**](USAGE.md).
