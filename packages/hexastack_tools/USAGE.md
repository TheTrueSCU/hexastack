# Hexastack Developer Tools & Usage Guide (`hexastack-tools`)

> Canonical developer command reference and CLI catalog automatically generated from tool entrypoints.

---

## 🏛️ Dogfooding Hexagonal Architecture

`hexastack-tools` is built strictly according to Hexastack's hexagonal design principles:
- **`domain/`**: Pure data contracts (`PrSummary`, `CheckRunFinding`, `ReviewThread`, `OutputFormat`).
- **`ports/`**: Clean interface contracts (`GitHubApiPort`).
- **`adapters/`**: Pluggable presenters (`rich`, `json`, `plain`) and GitHub API REST/GraphQL clients.
- **`commands/`**: High-performance Typer/Argparse CLI applications with pipe auto-detection.
- **`utils/`**: Shared monorepo workspace discovery and package graph resolvers.

---

## ⚙️ Output Presentation Formats

All inspection commands support `--format / -f`:
- **`auto` (default)**: Automatically outputs interactive ANSI tables/panels when attached to a terminal TTY, and switches to clean, tab-delimited plain text (`TSV`) when standard output is piped into Unix filters (`grep`, `awk`, `cut`, `xargs`, etc.).
- **`rich`**: Interactive Rich tables and color-coded status badges.
- **`json`**: Structured JSON for automation, CI scripts, and AI agents.
- **`plain`**: Machine-readable TSV stream.

---

## 🛠️ CLI Commands & Usage Catalog

### 🔍 GitHub & PR Examination Tools

#### `gh-pr-examine`

```text
Usage: gh-pr-examine [OPTIONS] [pr_number] COMMAND [ARGS]...

 Examine a Pull Request's complete health dashboard.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   pr_number      <str>  Pull request number (defaults to current branch PR). │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --format    -f      <auto|rich|json|plain>  Output format: auto (detects     │
│                                             pipes), rich (interactive        │
│                                             panels), json (structured),      │
│                                             plain (TSV).                     │
│                                             [default: auto]                  │
│ --details   -d                              Display full review comment      │
│                                             discussions.                     │
│ --watch     -w                              Continuously poll and refresh    │
│                                             until all checks and reviews     │
│                                             resolve.                         │
│ --interval  -i      <int>                   Polling interval in seconds when │
│                                             watching.                        │
│                                             [default: 15]                    │
│ --help                                      Show this message and exit.      │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ runs  List recent GitHub Actions workflow runs for a branch.                 │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `gh-checks`

```text
Usage: gh-checks [OPTIONS] {ref_or_pr}

 Inspect CI status checks for a given PR number or Git ref.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    ref_or_pr      <str>  Pull request number or commit ref/branch name.    │
│                            [required]                                        │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --format  -f      <auto|rich|json|plain>  Output format: auto (detects       │
│                                           pipes), rich (interactive tables), │
│                                           json (structured), plain (TSV).    │
│                                           [default: auto]                    │
│ --help                                    Show this message and exit.        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `gh-security`

```text
Usage: gh-security [OPTIONS] {pr_number}

 Fetch and display review comments and security findings for a PR.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    pr_number      <int>  Pull request number. [required]                   │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --format  -f      <auto|rich|json|plain>  Output format: auto (detects       │
│                                           pipes), rich (interactive tables), │
│                                           json (structured), plain (TSV).    │
│                                           [default: auto]                    │
│ --help                                    Show this message and exit.        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `gh-code-scanning`

```text
usage: gh-code-scanning [-h] [--rule RULE] [--package PACKAGE]
                        [--severity SEVERITY]
                        [--state {open,closed,dismissed,all}] [--details]
                        [alert]

Bucket and inspect GitHub CodeQL security & quality code-scanning alerts.

positional arguments:
  alert                 Inspect a specific alert number in detail (e.g. 98).

options:
  -h, --help            show this help message and exit
  --rule, -r RULE       Filter alerts by rule ID substring (e.g. 'unused-
                        import').
  --package, -p PACKAGE
                        Filter alerts by package name substring (e.g.
                        'hexastack_core').
  --severity, -s SEVERITY
                        Filter alerts by severity ('error', 'warning',
                        'note').
  --state {open,closed,dismissed,all}
                        Alert state ('open', 'closed', 'dismissed', 'all').
  --details, -d         Print detailed contextual panels for all matching
                        alerts.
```

### 🛡️ Security & Code Quality Gateways

#### `codeql-scan`

```text
usage: codeql-scan [-h] [--suite SUITE] [--output OUTPUT] [--threads THREADS]

Run local CodeQL security and quality analysis with auto-detection.

options:
  -h, --help            show this help message and exit
  --suite, -s SUITE     CodeQL query suite or pack (default: 'codeql/python-
                        queries').
  --output, -o OUTPUT   Optional destination path for generated SARIF report.
  --threads, -t THREADS
                        Number of analysis threads (0 for auto).
```

#### `check-test-parity`

```text
╭──────────────────────────────────────────────────────────────────────────────╮
│ ✅ All source modules mirror unit tests 1:1 and all test directories contain │
│ __init__.py.                                                                 │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `check-all-statements`

```text
usage: check-all-statements [-h]
                            [-p {ai,auth,cli,core,cqrs,db,events,fastapi,flags,graphql,grpc,hexastack,logging,mcp,otel,tools}]
                            [--path CUSTOM_PATHS] [-a]
                            [files ...]

Verify __all__ is deduplicated and sorted.

positional arguments:
  files                 Files or paths to process (defaults to all if none
                        specified).

options:
  -h, --help            show this help message and exit
  -p, --package {ai,auth,cli,core,cqrs,db,events,fastapi,flags,graphql,grpc,hexastack,logging,mcp,otel,tools}
                        Target specific package(s) (e.g. -p auth -p core).
  --path CUSTOM_PATHS   Target custom directory or file path(s).
  -a, --all             Run across all packages unconditionally.
```

#### `fix-all-statements`

```text
usage: fix-all-statements [-h]
                          [-p {ai,auth,cli,core,cqrs,db,events,fastapi,flags,graphql,grpc,hexastack,logging,mcp,otel,tools}]
                          [--path CUSTOM_PATHS] [-a]
                          [files ...]

Format, alphabetize, and deduplicate __all__ statements.

positional arguments:
  files                 Files or paths to process (defaults to all if none
                        specified).

options:
  -h, --help            show this help message and exit
  -p, --package {ai,auth,cli,core,cqrs,db,events,fastapi,flags,graphql,grpc,hexastack,logging,mcp,otel,tools}
                        Target specific package(s) (e.g. -p auth -p core).
  --path CUSTOM_PATHS   Target custom directory or file path(s).
  -a, --all             Run across all packages unconditionally.
```

#### `import-linter-run`

```text
usage: import-linter-run [-h] [--all] [files ...]

Run import-linter per package.

positional arguments:
  files       Changed files passed by pre-commit

options:
  -h, --help  show this help message and exit
  --all       Run across all packages unconditionally
```

#### `import-linter-generate`

```text
usage: import-linter-generate [-h]
                              [-p {ai,auth,cli,core,cqrs,db,events,fastapi,flags,graphql,grpc,hexastack,logging,mcp,otel,tools}]
                              [--path CUSTOM_PATHS] [-a]
                              [files ...]

Generate [tool.importlinter] contracts in pyproject.toml.

positional arguments:
  files                 Files or paths to process (defaults to all if none
                        specified).

options:
  -h, --help            show this help message and exit
  -p, --package {ai,auth,cli,core,cqrs,db,events,fastapi,flags,graphql,grpc,hexastack,logging,mcp,otel,tools}
                        Target specific package(s) (e.g. -p auth -p core).
  --path CUSTOM_PATHS   Target custom directory or file path(s).
  -a, --all             Run across all packages unconditionally.
```

#### `deptry-run`

```text
usage: deptry-run [-h]

Run deptry per package.

options:
  -h, --help  show this help message and exit
```

#### `generate-usage-docs`

```text
usage: generate-usage-docs [-h] [-p {tools,hexastack,all}] [-A] [--check]
                           [--fix]

Generate, verify, and fix USAGE.md documentation for Hexastack packages.

options:
  -h, --help            show this help message and exit
  -p, --package {tools,hexastack,all}
                        Target package to process (default: auto-detected
                        based on git changes or all)
  -A, --affected        Detect and process only affected packages with CLI
                        impact.
  --check, --verify     Verify whether USAGE.md files match in-memory
                        generation (pre-commit quality gate).
  --fix                 Re-generate and format USAGE.md files directly on
                        disk.
```

### 🧪 Test Execution, Contracts & Mutation

#### `pytest-run`

```text
usage: pytest-run [-h]
                  [-p {ai,auth,cli,core,cqrs,db,events,fastapi,flags,graphql,grpc,hexastack,logging,mcp,otel,tools}]
                  [-A] [-U] [-P]

Run pytest test suite.

options:
  -h, --help            show this help message and exit
  -p, --package {ai,auth,cli,core,cqrs,db,events,fastapi,flags,graphql,grpc,hexastack,logging,mcp,otel,tools}
  -A, --affected
  -U, --unit
  -P, --properties
```

#### `pytest-archon-generate`

```text
usage: pytest-archon-generate [-h]
                              [-p {ai,auth,cli,core,cqrs,db,events,fastapi,flags,graphql,grpc,hexastack,logging,mcp,otel,tools}]
                              [--path CUSTOM_PATHS] [-a]
                              [files ...]

Generate pytest-archon boundary tests for packages.

positional arguments:
  files                 Files or paths to process (defaults to all if none
                        specified).

options:
  -h, --help            show this help message and exit
  -p, --package {ai,auth,cli,core,cqrs,db,events,fastapi,flags,graphql,grpc,hexastack,logging,mcp,otel,tools}
                        Target specific package(s) (e.g. -p auth -p core).
  --path CUSTOM_PATHS   Target custom directory or file path(s).
  -a, --all             Run across all packages unconditionally.
```

#### `inline-snapshot-update`

```text
usage: inline-snapshot-update [-h]
                              [-p {ai,auth,cli,core,cqrs,db,events,fastapi,flags,graphql,grpc,hexastack,logging,mcp,otel,tools}]
                              [--path CUSTOM_PATHS] [-a]
                              [--mode {create,fix,review}]
                              [files ...]

Update or review inline-snapshots across Hexastack test suites.

positional arguments:
  files                 Files or paths to process (defaults to all if none
                        specified).

options:
  -h, --help            show this help message and exit
  -p, --package {ai,auth,cli,core,cqrs,db,events,fastapi,flags,graphql,grpc,hexastack,logging,mcp,otel,tools}
                        Target specific package(s) (e.g. -p auth -p core).
  --path CUSTOM_PATHS   Target custom directory or file path(s).
  -a, --all             Run across all packages unconditionally.
  --mode, -m {create,fix,review}
                        inline-snapshot mode: 'create' for new snapshots,
                        'fix' to update changed values, 'review' to diff
                        (default: fix).
```

#### `mutmut-run`

```text
usage: mutmut-run [-h]
                  [-p {ai,auth,cli,core,cqrs,db,events,fastapi,flags,graphql,grpc,hexastack,logging,mcp,otel,tools}]
                  [-a]

Run mutation tests.

options:
  -h, --help            show this help message and exit
  -p, --package {ai,auth,cli,core,cqrs,db,events,fastapi,flags,graphql,grpc,hexastack,logging,mcp,otel,tools}
  -a, --all
```

#### `mutmut-inspect`

```text
usage: mutmut-inspect [-h]

Inspect mutation testing results and cached mutants.

options:
  -h, --help  show this help message and exit
```

### 📦 Code Architecture & Distribution

#### `pydeps-generate`

```text
usage: pydeps-generate [-h]
                       [-p {ai,auth,cli,core,cqrs,db,events,fastapi,flags,graphql,grpc,hexastack,logging,mcp,otel,tools}]
                       [--path CUSTOM_PATHS] [-a]
                       [files ...]

Generate architecture dependency diagrams using pydeps.

positional arguments:
  files                 Files or paths to process (defaults to all if none
                        specified).

options:
  -h, --help            show this help message and exit
  -p, --package {ai,auth,cli,core,cqrs,db,events,fastapi,flags,graphql,grpc,hexastack,logging,mcp,otel,tools}
                        Target specific package(s) (e.g. -p auth -p core).
  --path CUSTOM_PATHS   Target custom directory or file path(s).
  -a, --all             Run across all packages unconditionally.
```

#### `pypi-check`

```text
usage: pypi-check [-h]

Verify package release version availability against PyPI index.

options:
  -h, --help  show this help message and exit
```

#### `pypi-build`

```text
PyPI Monorepo Distribution Builder ->
          /home/rjdw/Projects/hexastack/dist
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ Package Name      ┃ Version      ┃ Status           ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ hexastack         │ 0.1.0        │ ✓ Built          │
│ hexastack-ai      │ 0.1.0        │ ✓ Built          │
│ hexastack-auth    │ 0.1.0        │ ✓ Built          │
│ hexastack-cli     │ 0.1.0        │ ✓ Built          │
│ hexastack-core    │ 0.1.0        │ ✓ Built          │
│ hexastack-cqrs    │ 0.1.0        │ ✓ Built          │
│ hexastack-db      │ 0.1.0        │ ✓ Built          │
│ hexastack-events  │ 0.1.0        │ ✓ Built          │
│ hexastack-fastapi │ 0.1.0        │ ✓ Built          │
│ hexastack-flags   │ 0.1.0        │ ✓ Built          │
│ hexastack-graphql │ 0.1.0        │ ✓ Built          │
│ hexastack-grpc    │ 0.1.0        │ ✓ Built          │
│ hexastack-logging │ 0.1.0        │ ✓ Built          │
│ hexastack-mcp     │ 0.1.0        │ ✓ Built          │
│ hexastack-otel    │ 0.1.0        │ ✓ Built          │
│ hexastack-tools   │ 0.1.0        │ ✓ Built          │
└───────────────────┴──────────────┴──────────────────┘
```

#### `pypi-publish`

```text
usage: pypi-publish [-h]

Build distribution packages and prepare for PyPI release publishing.

options:
  -h, --help  show this help message and exit
```

#### `alphabetizer`

```text
usage: alphabetizer [-h]
                    [-p {ai,auth,cli,core,cqrs,db,events,fastapi,flags,graphql,grpc,hexastack,logging,mcp,otel,tools}]
                    [--path CUSTOM_PATHS] [-a]
                    [files ...]

Alphabetize functions and class methods across packages deterministically.

positional arguments:
  files                 Files or paths to process (defaults to all if none
                        specified).

options:
  -h, --help            show this help message and exit
  -p, --package {ai,auth,cli,core,cqrs,db,events,fastapi,flags,graphql,grpc,hexastack,logging,mcp,otel,tools}
                        Target specific package(s) (e.g. -p auth -p core).
  --path CUSTOM_PATHS   Target custom directory or file path(s).
  -a, --all             Run across all packages unconditionally.
```

#### `rope-run`

```text
usage: rope-run [-h]
                [-p {ai,auth,cli,core,cqrs,db,events,fastapi,flags,graphql,grpc,hexastack,logging,mcp,otel,tools}]
                [--path CUSTOM_PATHS] [-a]
                [files ...]

Alphabetize functions and class methods across packages deterministically.

positional arguments:
  files                 Files or paths to process (defaults to all if none
                        specified).

options:
  -h, --help            show this help message and exit
  -p, --package {ai,auth,cli,core,cqrs,db,events,fastapi,flags,graphql,grpc,hexastack,logging,mcp,otel,tools}
                        Target specific package(s) (e.g. -p auth -p core).
  --path CUSTOM_PATHS   Target custom directory or file path(s).
  -a, --all             Run across all packages unconditionally.
```

### 🔧 Additional Workspace Tools

#### `rope-alphabetizer`

```text
usage: rope-alphabetizer [-h]
                         [-p {ai,auth,cli,core,cqrs,db,events,fastapi,flags,graphql,grpc,hexastack,logging,mcp,otel,tools}]
                         [--path CUSTOM_PATHS] [-a]
                         [files ...]

Alphabetize functions and class methods across packages deterministically.

positional arguments:
  files                 Files or paths to process (defaults to all if none
                        specified).

options:
  -h, --help            show this help message and exit
  -p, --package {ai,auth,cli,core,cqrs,db,events,fastapi,flags,graphql,grpc,hexastack,logging,mcp,otel,tools}
                        Target specific package(s) (e.g. -p auth -p core).
  --path CUSTOM_PATHS   Target custom directory or file path(s).
  -a, --all             Run across all packages unconditionally.
```
