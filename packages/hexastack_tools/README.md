# Hexastack Tools (`packages/hexastack_tools`)

Developer tooling, repository governance, code-scanning analysis, and CI automation suite for the Hexastack monorepo.

---

## 📖 Complete Documentation & Usage

For full CLI usage instructions and command examples, see the canonical [**USAGE Guide**](USAGE.md) or the [online developer documentation](file:///docs/tools.md).

---

## 🏛️ Architectural Intent

`hexastack-tools` strictly dogfoods Hexastack's own hexagonal architecture with:
- **`domain/`**: Pure data contracts (`PrSummary`, `CheckRunFinding`, `ReviewThread`, `OutputFormat`).
- **`ports/`**: Decoupled port interfaces (`GitHubApiPort`).
- **`adapters/`**: REST/GraphQL HTTP adapters (`GitHubHttpAdapter`) and multi-format presenters (`pr.py`, `checks.py`, `security.py`).
- **`commands/`**: Clean Typer CLI entrypoints.
- **`utils/`**: Shared monorepo workspace discovery and package graph resolvers.

---

## ⚙️ Output Presentation Modes

All CLI commands support multi-format presenters:
1. **`auto` (default)**: Renders interactive Rich tables/panels if connected to a terminal TTY, or automatically switches to plain TSV when output is piped to tools like `grep`, `awk`, `cut`, or `xargs`.
2. **`rich`**: Colorized ANSI dashboards with status icons and panels.
3. **`json`**: Structured JSON payload for CI integration or agent tooling.
4. **`plain`**: Clean, newline- and tab-delimited (TSV) stream.

---

## 🛠️ Quick Command Reference

| Command | Purpose |
|---|---|
| `uv run gh-pr-examine [pr]` | Full PR dashboard inspecting checks, review threads, failed CI logs, and conflicts. |
| `uv run gh-pr-examine runs [branch]` | Lists recent workflow runs for a branch. |
| `uv run gh-checks [pr/ref]` | Detailed status checks inspector. |
| `uv run gh-security [pr]` | Review comments and bot discussion thread auditor. |
| `uv run gh-code-scanning` | CodeQL SAST security alerts browser. |
| `uv run check-test-parity` | Validates 1:1 mirroring between `src/` and `tests/unit/`. |
| `uv run check-all-statements` | Validates `__all__` alphabetical sorting. |
| `uv run fix-all-statements` | Automatically sorts and alphabetizes `__all__`. |
| `uv run import-linter-run` | Validates package and hexagonal architecture layer boundaries. |
| `uv run pypi-build` | Builds sdist and wheel packages across workspace. |
| `uv run pypi-check` | Verifies build metadata and checks for PyPI release collisions. |
| `uv run codeql-scan` | Runs local SARIF CodeQL SAST security scan. |

For detailed syntax and flags, see [**USAGE.md**](USAGE.md).
