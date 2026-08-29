# Hexastack Tools (`packages/hexastack_tools`)

Developer tooling, repository governance, code-scanning analysis, and CI automation suite for the Hexastack monorepo.

---

## 🏛️ Architectural Intent

`hexastack-tools` strictly dogfoods Hexastack's own hexagonal architecture with:
- **`domain/`**: Pure data contracts ([`PrSummary`](file:///home/rjdw/Projects/hexastack/packages/hexastack_tools/src/hexastack_tools/domain/github.py), [`CheckRunFinding`](file:///home/rjdw/Projects/hexastack/packages/hexastack_tools/src/hexastack_tools/domain/github.py), [`ReviewThread`](file:///home/rjdw/Projects/hexastack/packages/hexastack_tools/src/hexastack_tools/domain/github.py), [`OutputFormat`](file:///home/rjdw/Projects/hexastack/packages/hexastack_tools/src/hexastack_tools/domain/github.py)).
- **`ports/`**: Decoupled port interfaces ([`GitHubApiPort`](file:///home/rjdw/Projects/hexastack/packages/hexastack_tools/src/hexastack_tools/ports/github.py)).
- **`adapters/`**: REST/GraphQL HTTP adapters ([`GitHubHttpAdapter`](file:///home/rjdw/Projects/hexastack/packages/hexastack_tools/src/hexastack_tools/adapters/github/client.py)) and multi-format presenters ([`pr.py`](file:///home/rjdw/Projects/hexastack/packages/hexastack_tools/src/hexastack_tools/adapters/presenters/pr.py), [`checks.py`](file:///home/rjdw/Projects/hexastack/packages/hexastack_tools/src/hexastack_tools/adapters/presenters/checks.py), [`security.py`](file:///home/rjdw/Projects/hexastack/packages/hexastack_tools/src/hexastack_tools/adapters/presenters/security.py)).
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

## 🛠️ CLI Tools & Usage Catalog

### 1. `gh-pr-examine` (Unified PR Dashboard & Conversation Audit)

Examines a Pull Request in a single command, aggregating CI check runs, code scanning alerts, and GitHub GraphQL review threads with resolution status.

```bash
# Examine current branch PR (auto-detected via local git branch)
uv run gh-pr-examine

# Examine specific PR by number
uv run gh-pr-examine 42

# View full review comment discussions & thread details
uv run gh-pr-examine 42 --details

# Watch live CI & review progress until clean (exit code 0 on success, 1 on failure/unresolved threads)
uv run gh-pr-examine 42 --watch --interval 10

# Pipe plain TSV directly into Unix utilities (auto-selected when piped)
uv run gh-pr-examine 42 | grep "UNRESOLVED"

# Structured JSON output
uv run gh-pr-examine 42 --format json
```

---

### 2. `gh-checks` (CI Status Inspector)

Inspects GitHub Actions check runs and status checks for a PR number or git commit SHA/branch.

```bash
# Inspect CI checks for PR #42
uv run gh-checks 42

# Inspect CI checks for a specific git ref/commit
uv run gh-checks main
uv run gh-checks a1b2c3d

# Piped execution
uv run gh-checks 42 | grep -i "failure"
```

---

### 3. `gh-security` (Review Comments & Security Audit)

Fetches inline code review comments, bot comments, and unresolved discussion threads.

```bash
# Audit review comments on PR #42
uv run gh-security 42

# Output in JSON format
uv run gh-security 42 --format json
```

---

### 4. `gh-code-scanning` (CodeQL Security Alerts)

Queries repository code scanning and CodeQL security alerts.

```bash
# List all open CodeQL security alerts
uv run gh-code-scanning

# Filter alerts by branch or PR ref
uv run gh-code-scanning --ref feat/issue-40
```

---

### 5. `check-test-parity` (Test Parity Enforcement)

Audits 1:1 mirroring between `src/` modules and `tests/unit/` test files across every package in the monorepo.

```bash
# Check test parity across all monorepo packages
uv run check-test-parity
```

---

### 6. `check-all-statements` & `fix-all-statements` (`__all__` Integrity)

Audits and automatically formats/alphabetizes `__all__` exported symbol arrays across Python modules.

```bash
# Audit __all__ integrity
uv run check-all-statements

# Automatically sort and alphabetize __all__ lists
uv run fix-all-statements
```

---

### 7. `import-linter-generate` & `import-linter-run` (Hexagonal Boundary Enforcement)

Generates layer boundary configuration contracts and validates hexagonal dependency rules.

```bash
# Generate .importlinter configuration for all packages
uv run import-linter-generate

# Run layer boundary validation
uv run import-linter-run
```

---

### 8. `pypi-build`, `pypi-check`, and `pypi-publish` (Package Release Automation)

Builds wheels/sdists, verifies metadata & PyPI version collisions, and manages package distribution.

```bash
# Build distributions for all packages
uv run pypi-build

# Check version readiness against PyPI
uv run pypi-check
```

---

### 9. `codeql-scan` (Local CodeQL Scanner)

Performs local SARIF CodeQL SAST scans across the workspace.

```bash
uv run codeql-scan
```
