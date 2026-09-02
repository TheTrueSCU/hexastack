# Hexastack Developer Tools & Usage Guide (`hexastack-tools`)

> Comprehensive usage catalog and command reference for developer tooling, CI diagnostics, code scanning, and monorepo governance in Hexastack.

---

## 🏛️ Dogfooding Hexagonal Architecture

`hexastack-tools` is built strictly according to Hexastack's hexagonal design principles:
- **`domain/`**: Pure data contracts (`PrSummary`, `CheckRunFinding`, `ReviewThread`, `OutputFormat`).
- **`ports/`**: Clean interface contracts (`GitHubApiPort`).
- **`adapters/`**: Pluggable presenters (`rich`, `json`, `plain`) and GitHub API REST/GraphQL clients.
- **`commands/`**: High-performance Typer CLI applications with pipe auto-detection.
- **`utils/`**: Shared monorepo workspace discovery and package graph resolvers.

---

## ⚙️ Presentation Formats & Pipe Detection

All tools support `--format / -f`:
- **`auto` (default)**: Automatically outputs interactive ANSI tables/panels when attached to a terminal TTY, and switches to clean, tab-delimited plain text (`TSV`) when standard output is piped into Unix filters (`grep`, `awk`, `cut`, `xargs`, etc.).
- **`rich`**: Interactive Rich tables and color-coded status badges.
- **`json`**: Structured JSON for automation, CI scripts, and AI agents.
- **`plain`**: Machine-readable TSV stream.

---

## 🛠️ CLI Commands Catalog

### 1. `gh-pr-examine` (Unified PR Dashboard & Conversation Audit)

Aggregates PR status, CI check runs, CodeQL alerts, inline diff review comments, failed CI logs, base branch merge conflicts, and review thread resolution in a single inspection dashboard.

```bash
# Examine current branch PR (auto-detected from Git)
uv run gh-pr-examine

# Examine specific PR by number
uv run gh-pr-examine 42

# View detailed review comments & unresolved conversation threads
uv run gh-pr-examine 42 --details

# Watch live CI runs and review thread status (polling every 10s)
uv run gh-pr-examine 42 --watch --interval 10

# Inspect recent workflow runs for a branch
uv run gh-pr-examine runs feat/my-branch

# Automatic Unix pipe filtering (auto-selects TSV)
uv run gh-pr-examine 42 | grep "UNRESOLVED"

# Structured JSON output
uv run gh-pr-examine 42 --format json
```

---

### 2. `gh-checks` (CI Status Inspector)

Inspects GitHub Actions workflows and discrete check runs for a PR number or git commit SHA/branch.

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
uv run fix-all-statements -p <package_name>
uv run fix-all-statements -a
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
