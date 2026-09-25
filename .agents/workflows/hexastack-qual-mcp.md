---
name: hexastack-qual-mcp
description: Invoking quality and governance diagnostics via hexastack-qual MCP server and CLI.
---

# Workflow: Hexastack Quality MCP & Governance Automation

This workflow defines how AI coding assistants interact with `hexastack-qual` via the standard Hexastack Model Context Protocol (MCP) server or CLI to audit code quality, format exports, inspect surviving mutants, and verify test impact.

## 1. Running the Unified MCP Server

Quality tools, resources, and prompt templates are automatically registered into Hexastack's unified MCP server via `QualBootstrapper` (order 36).

### Launching the Server (stdio)
```bash
uv run hexastack mcp run
```

### Inspecting Capabilities
```bash
uv run hexastack mcp list
```

### Portable Client Configuration
Generate the portable configuration snippet for any supported AI coding assistant:
```bash
# For Antigravity / Gemini CLI:
uv run hexastack mcp config -c antigravity

# For Claude Desktop:
uv run hexastack mcp config -c claude

# For Cursor:
uv run hexastack mcp config -c cursor
```

Standard configuration (`mcpServers` in AI client settings):
```json
{
  "mcpServers": {
    "hexastack": {
      "command": "uv",
      "args": ["run", "hexastack", "mcp", "run"],
      "env": {
        "HEXASTACK_AI__PROVIDER": "gemini",
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

## 2. Available Quality MCP Tools

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

- **Resource `quality://workspace/scorecard`**: Read-only JSON representation of the latest quality scorecard for the active repository.
- **Prompt `triage-mutants`**: Guided prompt template taking surviving mutant findings and generating targeted unit test recommendations to kill them.
