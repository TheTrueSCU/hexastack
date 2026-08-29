# Developer Tools & Repository Governance

> `hexastack-tools` provides a unified suite of developer CLI commands, code scanning automation, multi-format presenters, and quality gate checkers across the Hexastack workspace.

---

## 🏛️ Dogfooding Hexagonal Architecture

`hexastack-tools` is built strictly according to Hexastack's hexagonal design principles:
- **`domain/`**: Pure domain models (`PrSummary`, `CheckRunFinding`, `ReviewThread`, `OutputFormat`).
- **`ports/`**: Clean interface contracts (`GitHubApiPort`).
- **`adapters/`**: Pluggable presenters (`rich`, `json`, `plain`) and GitHub API REST/GraphQL clients.
- **`commands/`**: High-performance Typer CLI applications with pipe auto-detection.

---

## ⚙️ Presentation Formats & Pipe Detection

All tools support `--format / -f`:
- **`auto` (default)**: Automatically outputs interactive ANSI tables/panels when attached to a terminal TTY, and switches to clean, tab-delimited plain text (`TSV`) when standard output is piped into Unix filters (`grep`, `awk`, `cut`, `xargs`, etc.).
- **`rich`**: Interactive Rich tables and color-coded status badges.
- **`json`**: Structured JSON for automation, CI scripts, and AI agents.
- **`plain`**: Machine-readable TSV stream.

---

## 🚀 CLI Commands & Usage

### 1. `gh-pr-examine` (Unified PR Dashboard & Conversation Audit)

Aggregates PR status, CI check runs, CodeQL alerts, and review thread resolution in a single inspection dashboard.

```bash
# Examine current branch PR (auto-detected from Git)
uv run gh-pr-examine

# Examine specific PR by number
uv run gh-pr-examine 42

# View detailed review comments & unresolved conversation threads
uv run gh-pr-examine 42 --details

# Watch live CI runs and review thread status
uv run gh-pr-examine 42 --watch --interval 10

# Automatic Unix pipe filtering
uv run gh-pr-examine 42 | grep "UNRESOLVED"

# Structured JSON output
uv run gh-pr-examine 42 --format json
```

---

### 2. `gh-checks` (CI Status Inspector)

Inspects GitHub Actions workflows and discrete check runs for a PR or commit SHA.

```bash
# Inspect checks for PR #42
uv run gh-checks 42

# Inspect checks for main or a specific commit SHA
uv run gh-checks main
uv run gh-checks a1b2c3d

# Piped execution
uv run gh-checks 42 | grep -i "failure"
```

---

### 3. `gh-security` (Security & Code Review Comments)

Fetches inline code review comments, bot comments, and unresolved discussion threads.

```bash
# Audit comments on PR #42
uv run gh-security 42

# Export to JSON
uv run gh-security 42 --format json
```

---

### 4. `check-test-parity` (1:1 Test Parity Auditor)

Enforces complete parity between `src/` modules and unit test files across every package.

```bash
uv run check-test-parity
```

---

### 5. `check-all-statements` & `fix-all-statements` (`__all__` Integrity)

Audits and automatically formats/alphabetizes `__all__` exported symbol arrays.

```bash
# Audit __all__ integrity
uv run check-all-statements

# Automatically fix and sort __all__
uv run fix-all-statements
```

---

### 6. `import-linter-generate` & `import-linter-run` (Hexagonal Boundary Enforcement)

Generates layer boundary contracts and validates that no layer violations occur.

```bash
# Generate .importlinter configuration
uv run import-linter-generate

# Run layer boundary validation
uv run import-linter-run
```

---

### 7. `pypi-build` & `pypi-check` (Release Automation)

Builds wheels/sdists and verifies PyPI version collision readiness.

```bash
# Build distributions
uv run pypi-build

# Check version readiness
uv run pypi-check
```
