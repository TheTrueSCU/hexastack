---
name: hexastack-qual-mcp
description: Invoking quality and governance diagnostics via hexastack-qual MCP server and CLI.
---

# Workflow: Hexastack Quality MCP & Governance Automation

This workflow defines how AI coding assistants interact with `hexastack-qual` via the Model Context Protocol (MCP) server or CLI to audit code quality, format exports, inspect surviving mutants, and verify test impact.

## 1. Running the Quality MCP Server

The quality MCP server exposes Hexastack/Hexaqual quality gates over standard stdio:

```bash
# Direct CLI invocation
uv run hexastack qual mcp
```

### Server Configuration (`mcpServers` in AI settings):
```json
{
  "hexastack-qual": {
    "command": "uv",
    "args": ["run", "hexastack", "qual", "mcp"],
    "cwd": "/path/to/hexastack"
  }
}
```

## 2. Available MCP Tools

AI agents can invoke these tools during pair programming sessions:

### `run_sanity_check`
Executes the fast sanity battery (Ruff, Ty, Complexipy, `__all__` sorting, test parity, architecture diagrams).
- **Arguments**:
  - `package` (optional string): Target package (e.g. `"core"`, `"cqrs"`, `"qual"`). Defaults to workspace.
  - `skip_tests` (optional boolean, default `true`): Skips long-running test suites for fast feedback.
- **Example Usage**:
  - Check current package: `run_sanity_check(package="qual")`
  - Full workspace gate: `run_sanity_check(skip_tests=true)`

### `format_statements`
Auto-formats, alphabetizes, and deduplicates `__all__` export lists across modules.
- **Arguments**:
  - `package` (optional string): Target package name.
- **Example Usage**:
  - `format_statements(package="qual")`

### `inspect_surviving_mutants`
Analyzes mutation testing reports (`.mutmut-cache`) to triage critical surviving mutants.
- **Arguments**:
  - `package` (optional string): Target package name.
  - `actionable_only` (optional boolean, default `true`): Restricts report to actionable critical survivors.
- **Example Usage**:
  - `inspect_surviving_mutants(package="events", actionable_only=true)`

### `query_impacted_tests`
Computes the minimal set of packages or tests impacted by changes relative to a git ref.
- **Arguments**:
  - `base_ref` (optional string, default `"origin/main"`): Git ref to compare HEAD against.
- **Example Usage**:
  - `query_impacted_tests(base_ref="origin/main")`

### `get_pr_health`
Gathers PR check run conclusions, CodeQL alerts, and unresolved review threads.
- **Arguments**:
  - `pr_number` (optional integer): PR number. Inferred from current branch if omitted.
- **Example Usage**:
  - `get_pr_health(pr_number=42)`

## 3. MCP Resources & Prompts

- **Resource `workspace_scorecard://current`**: Read-only JSON representation of the latest quality scorecard for the active repository.
- **Prompt `triage_mutants`**: Guided prompt template taking surviving mutant findings and generating targeted unit test recommendations to kill them.
