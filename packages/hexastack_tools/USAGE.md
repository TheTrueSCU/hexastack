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
usage: check-all-statements [-h] [-p PACKAGES] [--path CUSTOM_PATHS] [-a]
                            [files ...]

Verify __all__ is deduplicated and sorted.

positional arguments:
  files                 Files or paths to process (defaults to all if none
                        specified).

options:
  -h, --help            show this help message and exit
  -p, --package PACKAGES
                        Target specific package(s) (e.g. -p auth -p core).
  --path CUSTOM_PATHS   Target custom directory or file path(s).
  -a, --all             Run across all packages unconditionally.
```

#### `fix-all-statements`

```text
usage: fix-all-statements [-h] [-p PACKAGES] [--path CUSTOM_PATHS] [-a]
                          [files ...]

Format, alphabetize, and deduplicate __all__ statements.

positional arguments:
  files                 Files or paths to process (defaults to all if none
                        specified).

options:
  -h, --help            show this help message and exit
  -p, --package PACKAGES
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
usage: import-linter-generate [-h] [-p PACKAGES] [--path CUSTOM_PATHS] [-a]
                              [files ...]

Generate [tool.importlinter] contracts in pyproject.toml.

positional arguments:
  files                 Files or paths to process (defaults to all if none
                        specified).

options:
  -h, --help            show this help message and exit
  -p, --package PACKAGES
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
                  [-p {ai,auth,cli,core,cqrs,db,events,fastapi,flags,graphql,grpc,hexastack,hexastack_ai,hexastack_auth,hexastack_cli,hexastack_core,hexastack_cqrs,hexastack_db,hexastack_events,hexastack_fastapi,hexastack_flags,hexastack_graphql,hexastack_grpc,hexastack_logging,hexastack_mcp,hexastack_otel,hexastack_tools,logging,mcp,otel,tools}]
                  [-A] [-U] [-P]

Run pytest test suite.

options:
  -h, --help            show this help message and exit
  -p, --package {ai,auth,cli,core,cqrs,db,events,fastapi,flags,graphql,grpc,hexastack,hexastack_ai,hexastack_auth,hexastack_cli,hexastack_core,hexastack_cqrs,hexastack_db,hexastack_events,hexastack_fastapi,hexastack_flags,hexastack_graphql,hexastack_grpc,hexastack_logging,hexastack_mcp,hexastack_otel,hexastack_tools,logging,mcp,otel,tools}
  -A, --affected
  -U, --unit
  -P, --properties
```

#### `pytest-archon-generate`

```text
usage: pytest-archon-generate [-h] [-p PACKAGES] [--path CUSTOM_PATHS] [-a]
                              [files ...]

Generate pytest-archon boundary tests for packages.

positional arguments:
  files                 Files or paths to process (defaults to all if none
                        specified).

options:
  -h, --help            show this help message and exit
  -p, --package PACKAGES
                        Target specific package(s) (e.g. -p auth -p core).
  --path CUSTOM_PATHS   Target custom directory or file path(s).
  -a, --all             Run across all packages unconditionally.
```

#### `inline-snapshot-update`

```text
usage: inline-snapshot-update [-h] [-p PACKAGES] [--path CUSTOM_PATHS] [-a]
                              [--mode {create,fix,review}]
                              [files ...]

Update or review inline-snapshots across Hexastack test suites.

positional arguments:
  files                 Files or paths to process (defaults to all if none
                        specified).

options:
  -h, --help            show this help message and exit
  -p, --package PACKAGES
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
                  [-p {ai,auth,cli,core,cqrs,db,events,fastapi,flags,graphql,grpc,hexastack,hexastack_ai,hexastack_auth,hexastack_cli,hexastack_core,hexastack_cqrs,hexastack_db,hexastack_events,hexastack_fastapi,hexastack_flags,hexastack_graphql,hexastack_grpc,hexastack_logging,hexastack_mcp,hexastack_otel,hexastack_tools,logging,mcp,otel,tools}]
                  [-a]

Run mutation tests.

options:
  -h, --help            show this help message and exit
  -p, --package {ai,auth,cli,core,cqrs,db,events,fastapi,flags,graphql,grpc,hexastack,hexastack_ai,hexastack_auth,hexastack_cli,hexastack_core,hexastack_cqrs,hexastack_db,hexastack_events,hexastack_fastapi,hexastack_flags,hexastack_graphql,hexastack_grpc,hexastack_logging,hexastack_mcp,hexastack_otel,hexastack_tools,logging,mcp,otel,tools}
  -a, --all
```

#### `mutmut-inspect`

```text
usage: mutmut-inspect [-h] [--summary] [-p PACKAGE] [-f FILE] [-a] [-c]
                      [-n LIMIT]

Inspect .mutmut-cache with automated mutant classification (Critical vs
Ignorable)

options:
  -h, --help            show this help message and exit
  --summary             Display package-level and triage classification
                        summary.
  -p, --package PACKAGE
                        Filter surviving mutants by package name (e.g. db,
                        auth, events, grpc).
  -f, --file FILE       Filter surviving mutants by filename pattern (e.g.
                        exception.py).
  -a, --actionable-only
                        Only display actionable critical mutants (skip
                        ignorable / equivalent).
  -c, --correlate-coverage
                        Cross-reference .coverage database to identify test
                        functions executing mutant lines.
  -n, --limit LIMIT     Maximum number of mutant lines to display (default:
                        25).
```

### 📦 Code Architecture & Distribution

#### `pydeps-generate`

```text
usage: pydeps-generate [-h] [-p PACKAGES] [--path CUSTOM_PATHS] [-a]
                       [files ...]

Generate architecture dependency diagrams using pydeps.

positional arguments:
  files                 Files or paths to process (defaults to all if none
                        specified).

options:
  -h, --help            show this help message and exit
  -p, --package PACKAGES
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
usage: pypi-build [-h] [--out-dir OUT_DIR]

Build distribution packages (wheels and sdists) for all workspace packages.

options:
  -h, --help         show this help message and exit
  --out-dir OUT_DIR  Target directory for generated distribution packages
                     (default: dist/)
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
usage: alphabetizer [-h] [-p PACKAGES] [--path CUSTOM_PATHS] [-a] [files ...]

Alphabetize functions and class methods across packages deterministically.

positional arguments:
  files                 Files or paths to process (defaults to all if none
                        specified).

options:
  -h, --help            show this help message and exit
  -p, --package PACKAGES
                        Target specific package(s) (e.g. -p auth -p core).
  --path CUSTOM_PATHS   Target custom directory or file path(s).
  -a, --all             Run across all packages unconditionally.
```

#### `rope-run`

```text
usage: rope-run [-h] [--root ROOT] [--dry-run]
                {change-signature,extract-method,extract-var,find-occurrences,inline,move-module,move-symbol,rename,sort-methods,use-function} ...

Deterministic Python Refactoring Engine for AI Agents

positional arguments:
  {change-signature,extract-method,extract-var,find-occurrences,inline,move-module,move-symbol,rename,sort-methods,use-function}
    change-signature    Change arguments on a function project-wide
    extract-method      Extract code block to method
    extract-var         Extract expression to variable
    find-occurrences    Find all semantic occurrences of a symbol
    inline              Inline variable, method, or function project-wide
    move-module         Move module/package to another folder
    move-symbol         Move function/class to another file
    rename              Rename a symbol project-wide
    sort-methods        Alphabetize class methods in a file
    use-function        Replace duplicated logic with calls to this function

options:
  -h, --help            show this help message and exit
  --root ROOT           Project root (default: .)
  --dry-run             Preview changes without modifying source files.
```

### 🔧 Additional Workspace Tools

#### `check-extras-parity`

```text
usage: check-extras-parity [-h] [--diagram]

Audit optional extras parity across workspace subpackages and umbrella
package.

options:
  -h, --help  show this help message and exit
  --diagram   Generate and print Mermaid dependency diagram of package extras.
```

#### `deps-audit`

```text
usage: deps-audit [-h] [--diagrams] [--deptry-only] [--extras-only]

Unified dependency, optional extras, and architecture auditor for Hexastack.

options:
  -h, --help     show this help message and exit
  --diagrams     Regenerate all Pydeps SVG import graphs and Mermaid extras
                 diagrams.
  --deptry-only  Only run deptry source import audits.
  --extras-only  Only run optional extras parity checks.
```

#### `pytest-boundary-audit`

```text
usage: pytest-boundary-audit [-h] [--cov-file COV_FILE]

Audit .coverage execution contexts for hexagonal architectural layer leaks.

options:
  -h, --help           show this help message and exit
  --cov-file COV_FILE  Path to .coverage database (default: .coverage)
```

#### `pytest-impact`

```text
usage: pytest-impact [-h] [--base BASE] [--cov-file COV_FILE] [--dry-run] ...

Run only tests impacted by modified lines using git diff and .coverage data.

positional arguments:
  pytest_args          Extra flags passed directly to pytest (e.g. -- -v -s)

options:
  -h, --help           show this help message and exit
  --base BASE          Git ref or branch to diff against (e.g. 'main',
                       'origin/main', 'HEAD~1'). Defaults to unstaged/staged
                       working tree.
  --cov-file COV_FILE  Path to .coverage database (default: .coverage)
  --dry-run            Print selected test targets without executing pytest.
```

#### `pytest-redundancy-audit`

```text
usage: pytest-redundancy-audit [-h] [--cov-file COV_FILE] [-n LIMIT]

Identify redundant unit tests providing zero unique branch coverage.

options:
  -h, --help           show this help message and exit
  --cov-file COV_FILE  Path to .coverage database (default: .coverage)
  -n, --limit LIMIT    Maximum redundant tests to display (default: 25)
```

#### `rope-alphabetizer`

```text
usage: rope-alphabetizer [-h] [-p PACKAGES] [--path CUSTOM_PATHS] [-a]
                         [files ...]

Alphabetize functions and class methods across packages deterministically.

positional arguments:
  files                 Files or paths to process (defaults to all if none
                        specified).

options:
  -h, --help            show this help message and exit
  -p, --package PACKAGES
                        Target specific package(s) (e.g. -p auth -p core).
  --path CUSTOM_PATHS   Target custom directory or file path(s).
  -a, --all             Run across all packages unconditionally.
```
