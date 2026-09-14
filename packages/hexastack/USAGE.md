# Hexaqual Quality Suite & CLI Catalog (`hexastack` / `hs`)

> Canonical developer command reference and CLI catalog automatically generated from the complete command hierarchy.

---

## 🏛️ Dogfooding Hexagonal Architecture

`hexaqual` is built strictly according to Hexagonal Architecture design principles:
- **`domain/`**: Pure data contracts (`PrSummary`, `CheckRunFinding`, `ReviewThread`, `OutputFormat`).
- **`ports/`**: Clean interface contracts (`GitHubApiPort`, `GovernancePresenterPort`, `ToolRunnerPort`, `PyPiClientPort`).
- **`adapters/`**: Pluggable presenters (`rich`, `json`, `plain`), subcommands, and runners.
- **`cli/`**: Unified Typer CLI driving adapter (`hexaqual`).
- **`infra/`**: Command dispatchers, handlers, and execution orchestration.
- **`utils/`**: Workspace discovery, AST parsing, and package graph resolvers.

---

## ⚙️ Output Presentation Formats

All inspection commands support `--format / -f`:
- **`auto` (default)**: Automatically outputs interactive ANSI tables/panels when attached to a terminal TTY, and switches to clean, tab-delimited plain text (`TSV`) when standard output is piped into Unix filters (`grep`, `awk`, `cut`, `xargs`, etc.).
- **`rich`**: Interactive Rich tables and color-coded status badges.
- **`json`**: Structured JSON for automation, CI scripts, and AI agents.
- **`plain`**: Machine-readable TSV stream.

---

## 🚀 Unified Root Entrypoint (`hexastack` (alias: `hs`))

```text
Usage: hexastack [OPTIONS] COMMAND [ARGS]...

 Hexastack CLI Application

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --version             -v        Show the application version and exit.       │
│ --install-completion            Install completion for the current shell.    │
│ --show-completion               Show completion for the current shell, to    │
│                                 copy it or customize the installation.       │
│ --help                          Show this message and exit.                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ info     Display installed Hexastack packages and optional dependency        │
│          statuses.                                                           │
│ doctor   Display installed Hexastack packages and optional dependency        │
│          statuses.                                                           │
│ status   Display installed Hexastack packages and optional dependency        │
│          statuses.                                                           │
│ ping     Send a test ping command through the CQRS execution pipeline.       │
│ init     Initialize a new Hexastack microservice in the current working      │
│          directory.                                                          │
│ serve    Launch the Hexastack local development server (requires hexastack). │
│ dev      Launch concurrent multi-transport dev environment (REST on 8000,    │
│          gRPC on 50051, Outbox relay).                                       │
│ ui       Launch the Hexastack DevTools interactive web UI (requires          │
│          hexastack).                                                         │
│ load     Execute concurrent load/stress testing scenario using Locust.       │
│ inspect  Inspect management commands                                         │
│ demo     Demo management commands                                            │
│ new      Scaffold a new Hexagonal microservice project.                      │
│ db       Database migration management (requires hexastack).                 │
│ mcp      Model Context Protocol (MCP) AI agent tools and server.             │
│ grpc     High-performance gRPC server management.                            │
│ profile  Profile CPU performance or memory allocations with interactive      │
│          flamegraphs.                                                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

---

## 🛠️ Complete Subcommand Tree Reference

### `hexastack db`

```text
Usage: hexastack db [OPTIONS] COMMAND [ARGS]...

 Database migration management (requires hexastack).

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ init      Scaffold a new migrations directory.                               │
│ migrate   Apply pending database migrations (upgrade to head).               │
│ check     Verify there is no unapplied schema drift or missing migrations    │
│           (Alembic check).                                                   │
│ revision  Generate a new migration revision script.                          │
│ current   Show the current applied revision.                                 │
│ history   Show migration revision history.                                   │
│ stamp     Stamp the database at a revision without running migrations.       │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexastack db check`

```text
Usage: hexastack db check [OPTIONS]

 Verify there is no unapplied schema drift or missing migrations (Alembic
 check).

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --dir         <str>  Migrations directory. [default: migrations]             │
│ --url         <str>  Database URL (overrides DATABASE_URL env var).          │
│ --help               Show this message and exit.                             │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexastack db current`

```text
Usage: hexastack db current [OPTIONS]

 Show the current applied revision.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --dir         <str>  Migrations directory. [default: migrations]             │
│ --url         <str>  Database URL (overrides DATABASE_URL env var).          │
│ --help               Show this message and exit.                             │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexastack db history`

```text
Usage: hexastack db history [OPTIONS]

 Show migration revision history.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --dir         <str>  Migrations directory. [default: migrations]             │
│ --url         <str>  Database URL (overrides DATABASE_URL env var).          │
│ --help               Show this message and exit.                             │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexastack db init`

```text
Usage: hexastack db init [OPTIONS] [directory]

 Scaffold a new migrations directory.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   directory      <str>  Path to create the migrations directory.             │
│                         [default: migrations]                                │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexastack db migrate`

```text
Usage: hexastack db migrate [OPTIONS]

 Apply pending database migrations (upgrade to head).

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --dir             <str>  Migrations directory. [default: migrations]         │
│ --revision        <str>  Target revision. [default: head]                    │
│ --url             <str>  Database URL (overrides DATABASE_URL env var).      │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexastack db revision`

```text
Usage: hexastack db revision [OPTIONS] {message}

 Generate a new migration revision script.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    message      <str>  Short description of the migration. [required]      │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --dir                    <str>  Migrations directory. [default: migrations]  │
│ --no-autogenerate               Disable schema autogeneration.               │
│ --url                    <str>  Database URL (overrides DATABASE_URL env     │
│                                 var).                                        │
│ --help                          Show this message and exit.                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexastack db stamp`

```text
Usage: hexastack db stamp [OPTIONS] [revision]

 Stamp the database at a revision without running migrations.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   revision      <str>  Revision to stamp (default: head). [default: head]    │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --dir         <str>  Migrations directory. [default: migrations]             │
│ --url         <str>  Database URL (overrides DATABASE_URL env var).          │
│ --help               Show this message and exit.                             │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `hexastack demo`

```text
Usage: hexastack demo [OPTIONS] COMMAND [ARGS]...

 Demo management commands

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ ping  Send a test ping command through the CQRS execution pipeline.          │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexastack demo ping`

```text
Usage: hexastack demo ping [OPTIONS]

 Send a test ping command through the CQRS execution pipeline.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --message                 <str>                                              │
│ --output          -o      <str>  Output format: table, json, or plain        │
│                                  (CI/pipe friendly).                         │
│                                  [default: table]                            │
│ --input           -i      <str>  Input JSON payload string, file path, or    │
│                                  '-' for stdin.                              │
│ --quiet           -q             Quiet mode: suppress decorative terminal    │
│                                  output.                                     │
│ --debug                          Enable debug mode and render formatted      │
│                                  error tracebacks.                           │
│ --correlation-id          <str>  Explicit correlation ID for request         │
│                                  tracing.                                    │
│ --user-id                 <str>  Authenticated user context identifier.      │
│ --tenant-id               <str>  Tenant isolation identifier for             │
│                                  multi-tenancy.                              │
│ --help                           Show this message and exit.                 │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `hexastack dev`

```text
Usage: hexastack dev [OPTIONS]

 Launch concurrent multi-transport dev environment (REST on 8000, gRPC on
 50051, Outbox relay).

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --host       -h                 <str>  Bind host address.                    │
│                                        [default: 127.0.0.1]                  │
│ --port       -p                 <int>  REST HTTP port. [default: 8000]       │
│ --grpc-port                     <int>  gRPC port. [default: 50051]           │
│ --grpc           --no-grpc             Launch gRPC server. [default: grpc]   │
│ --outbox         --no-outbox           Launch Outbox relay daemon.           │
│                                        [default: outbox]                     │
│ --help                                 Show this message and exit.           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `hexastack doctor`

```text
Usage: hexastack doctor [OPTIONS]

 Display installed Hexastack packages and optional dependency statuses.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --output          -o      <str>  Output format: table, json, or plain        │
│                                  (CI/pipe friendly).                         │
│                                  [default: table]                            │
│ --input           -i      <str>  Input JSON payload string, file path, or    │
│                                  '-' for stdin.                              │
│ --quiet           -q             Quiet mode: suppress decorative terminal    │
│                                  output.                                     │
│ --debug                          Enable debug mode and render formatted      │
│                                  error tracebacks.                           │
│ --correlation-id          <str>  Explicit correlation ID for request         │
│                                  tracing.                                    │
│ --user-id                 <str>  Authenticated user context identifier.      │
│ --tenant-id               <str>  Tenant isolation identifier for             │
│                                  multi-tenancy.                              │
│ --help                           Show this message and exit.                 │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `hexastack gRPC`

```text
Usage: hexastack [OPTIONS] COMMAND [ARGS]...
Try 'hexastack --help' for help.
╭─ Error ──────────────────────────────────────────────────────────────────────╮
│ No such command 'gRPC'.                                                      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `hexastack grpc`

```text
Usage: hexastack grpc [OPTIONS] COMMAND [ARGS]...

 High-performance gRPC server management.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ serve     Launch the gRPC server daemon.                                     │
│ compile   Compile discovered @proto_schema inline strings and @proto_file    │
│           definitions into Python stubs.                                     │
│ list      Inspect and list registered gRPC services, RPC methods, and        │
│           protobuf schemas.                                                  │
│ lint      Lint Protobuf schemas using Buf (requires buf CLI in PATH).        │
│ breaking  Detect backwards-incompatible Protobuf breaking changes against a  │
│           git reference.                                                     │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexastack grpc breaking`

```text
Usage: hexastack grpc breaking [OPTIONS]

 Detect backwards-incompatible Protobuf breaking changes against a git
 reference.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --against  -a      <str>  Git reference or branch to compare against (e.g.   │
│                           .git#branch=main).                                 │
│                           [default: .git#branch=main]                        │
│ --path     -p      <str>  Path to current proto workspace. [default: .]      │
│ --help                    Show this message and exit.                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexastack grpc compile`

```text
Usage: hexastack grpc compile [OPTIONS]

 Compile discovered @proto_schema inline strings and @proto_file definitions
 into Python stubs.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --out-dir  -o      <str>  Target output directory for generated protobuf     │
│                           stubs.                                             │
│                           [default: src/generated/grpc]                      │
│ --file     -f      <str>  Optional explicit .proto file path(s) to compile.  │
│ --help                    Show this message and exit.                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexastack grpc definitions`

```text
Usage: hexastack grpc [OPTIONS] COMMAND [ARGS]...
Try 'hexastack grpc --help' for help.
╭─ Error ──────────────────────────────────────────────────────────────────────╮
│ No such command 'definitions'.                                               │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexastack grpc git`

```text
Usage: hexastack grpc [OPTIONS] COMMAND [ARGS]...
Try 'hexastack grpc --help' for help.
╭─ Error ──────────────────────────────────────────────────────────────────────╮
│ No such command 'git'.                                                       │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexastack grpc lint`

```text
Usage: hexastack grpc lint [OPTIONS]

 Lint Protobuf schemas using Buf (requires buf CLI in PATH).

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --path  -p      <str>  Path to proto files or buf.yaml workspace.            │
│                        [default: .]                                          │
│ --help                 Show this message and exit.                           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexastack grpc list`

```text
Usage: hexastack grpc list [OPTIONS]

 Inspect and list registered gRPC services, RPC methods, and protobuf schemas.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexastack grpc protobuf`

```text
Usage: hexastack grpc [OPTIONS] COMMAND [ARGS]...
Try 'hexastack grpc --help' for help.
╭─ Error ──────────────────────────────────────────────────────────────────────╮
│ No such command 'protobuf'.                                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexastack grpc serve`

```text
Usage: hexastack grpc serve [OPTIONS]

 Launch the gRPC server daemon.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --host  -h      <str>  Bind host. [default: 0.0.0.0]                         │
│ --port  -p      <int>  Bind port. [default: 50051]                           │
│ --help                 Show this message and exit.                           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `hexastack info`

```text
Usage: hexastack info [OPTIONS]

 Display installed Hexastack packages and optional dependency statuses.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --output          -o      <str>  Output format: table, json, or plain        │
│                                  (CI/pipe friendly).                         │
│                                  [default: table]                            │
│ --input           -i      <str>  Input JSON payload string, file path, or    │
│                                  '-' for stdin.                              │
│ --quiet           -q             Quiet mode: suppress decorative terminal    │
│                                  output.                                     │
│ --debug                          Enable debug mode and render formatted      │
│                                  error tracebacks.                           │
│ --correlation-id          <str>  Explicit correlation ID for request         │
│                                  tracing.                                    │
│ --user-id                 <str>  Authenticated user context identifier.      │
│ --tenant-id               <str>  Tenant isolation identifier for             │
│                                  multi-tenancy.                              │
│ --help                           Show this message and exit.                 │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `hexastack init`

```text
Usage: hexastack init [OPTIONS]

 Initialize a new Hexastack microservice in the current working directory.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --name          -n      <str>  Project name (defaults to current directory   │
│                                name).                                        │
│ --template      -t      <str>  Project template: minimal, web-api,           │
│                                event-driven, mcp-agent, enterprise.          │
│ --db                    <str>  Database driver: in-memory, sqlite, postgres. │
│ --interactive   -i             Prompt with interactive questionnaire wizard. │
│ --with-release                 Include automated PyPI release & SBOM         │
│                                workflow (.github/workflows/release.yml,      │
│                                CHANGELOG.md).                                │
│ --with-openssf                 Include OpenSSF security & governance starter │
│                                (.github/workflows/scorecard.yml,             │
│                                SECURITY.md, GOVERNANCE.md).                  │
│ --help                         Show this message and exit.                   │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `hexastack inspect`

```text
Usage: hexastack inspect [OPTIONS] COMMAND [ARGS]...

 Inspect management commands

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ registry  Display registered CQRS commands, queries, and configurations.     │
│ handlers  Display registered CQRS commands, queries, and configurations.     │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexastack inspect handlers`

```text
Usage: hexastack inspect handlers [OPTIONS]

 Display registered CQRS commands, queries, and configurations.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --output          -o      <str>  Output format: table, json, or plain        │
│                                  (CI/pipe friendly).                         │
│                                  [default: table]                            │
│ --input           -i      <str>  Input JSON payload string, file path, or    │
│                                  '-' for stdin.                              │
│ --quiet           -q             Quiet mode: suppress decorative terminal    │
│                                  output.                                     │
│ --debug                          Enable debug mode and render formatted      │
│                                  error tracebacks.                           │
│ --correlation-id          <str>  Explicit correlation ID for request         │
│                                  tracing.                                    │
│ --user-id                 <str>  Authenticated user context identifier.      │
│ --tenant-id               <str>  Tenant isolation identifier for             │
│                                  multi-tenancy.                              │
│ --help                           Show this message and exit.                 │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexastack inspect registry`

```text
Usage: hexastack inspect registry [OPTIONS]

 Display registered CQRS commands, queries, and configurations.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --output          -o      <str>  Output format: table, json, or plain        │
│                                  (CI/pipe friendly).                         │
│                                  [default: table]                            │
│ --input           -i      <str>  Input JSON payload string, file path, or    │
│                                  '-' for stdin.                              │
│ --quiet           -q             Quiet mode: suppress decorative terminal    │
│                                  output.                                     │
│ --debug                          Enable debug mode and render formatted      │
│                                  error tracebacks.                           │
│ --correlation-id          <str>  Explicit correlation ID for request         │
│                                  tracing.                                    │
│ --user-id                 <str>  Authenticated user context identifier.      │
│ --tenant-id               <str>  Tenant isolation identifier for             │
│                                  multi-tenancy.                              │
│ --help                           Show this message and exit.                 │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `hexastack load`

```text
Usage: hexastack load [OPTIONS]

 Execute concurrent load/stress testing scenario using Locust.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --host        -h           <str>  Target service host URL.                   │
│                                   [default: http://127.0.0.1:8000]           │
│ --users       -u           <int>  Peak number of concurrent virtual users.   │
│                                   [default: 50]                              │
│ --spawn-rate  -r           <int>  Rate to spawn users per second.            │
│                                   [default: 10]                              │
│ --run-time    -t           <str>  Total benchmark run time (e.g. 15s, 1m).   │
│                                   [default: 15s]                             │
│ --locustfile  -f           <str>  Locustfile scenario filepath.              │
│                                   [default: locustfile.py]                   │
│ --headless        --web           Run headlessly in CLI without Web UI.      │
│                                   [default: headless]                        │
│ --help                            Show this message and exit.                │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `hexastack mcp`

```text
Usage: hexastack mcp [OPTIONS] COMMAND [ARGS]...

 Model Context Protocol (MCP) AI agent tools and server.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ run     Launch the MCP server in stdio mode (for Claude, Cursor, Gemini,     │
│         Antigravity).                                                        │
│ config  Generate MCP JSON configuration for Gemini / Antigravity, Claude     │
│         Desktop, or Cursor.                                                  │
│ list    Inspect and list registered MCP tools, prompt templates, and         │
│         resources.                                                           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexastack mcp config`

```text
Usage: hexastack mcp config [OPTIONS]

 Generate MCP JSON configuration for Gemini / Antigravity, Claude Desktop, or
 Cursor.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --client   -c      <str>  Target client: 'antigravity', 'gemini', 'claude',  │
│                           'cursor'.                                          │
│                           [default: antigravity]                             │
│ --name     -n      <str>  Server name in the MCP client config.              │
│                           [default: hexastack]                               │
│ --command          <str>  Custom executable command (defaults to 'uv run     │
│                           hexastack mcp run').                               │
│ --help                    Show this message and exit.                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexastack mcp list`

```text
Usage: hexastack mcp list [OPTIONS]

 Inspect and list registered MCP tools, prompt templates, and resources.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexastack mcp run`

```text
Usage: hexastack mcp run [OPTIONS]

 Launch the MCP server in stdio mode (for Claude, Cursor, Gemini, Antigravity).

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `hexastack new`

```text
Usage: hexastack new [OPTIONS] COMMAND [ARGS]...

 Scaffold a new Hexagonal microservice project.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ web-api          Scaffold a RESTful Web API microservice (FastAPI + UoW +    │
│                  DevTools UI).                                               │
│ minimal          Scaffold a lightweight CLI or worker service (Core + CQRS + │
│                  Logging).                                                   │
│ event-driven     Scaffold an Event-Driven service with CloudEvents and       │
│                  Transactional Outbox.                                       │
│ mcp-agent        Scaffold an AI Model Context Protocol (MCP) server & agent  │
│                  tools service.                                              │
│ grpc-service     Scaffold a high-performance gRPC microservice (Protobuf +   │
│                  Server Reflection).                                         │
│ graphql-service  Scaffold a GraphQL data-graph gateway microservice          │
│                  (Strawberry + GraphiQL).                                    │
│ enterprise       Scaffold a production Enterprise microservice with all      │
│                  modules enabled.                                            │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexastack new DevTools`

```text
Usage: hexastack new [OPTIONS] COMMAND [ARGS]...
Try 'hexastack new --help' for help.
╭─ Error ──────────────────────────────────────────────────────────────────────╮
│ No such command 'DevTools'.                                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexastack new Server`

```text
Usage: hexastack new [OPTIONS] COMMAND [ARGS]...
Try 'hexastack new --help' for help.
╭─ Error ──────────────────────────────────────────────────────────────────────╮
│ No such command 'Server'.                                                    │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexastack new Transactional`

```text
Usage: hexastack new [OPTIONS] COMMAND [ARGS]...
Try 'hexastack new --help' for help.
╭─ Error ──────────────────────────────────────────────────────────────────────╮
│ No such command 'Transactional'.                                             │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexastack new enterprise`

```text
Usage: hexastack new enterprise [OPTIONS] {name}

 Scaffold a production Enterprise microservice with all modules enabled.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    name      <str>  Name of the new microservice project. [required]       │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --description  -d      <str>  Project description.                           │
│                               [default: A full-featured enterprise Hexastack │
│                               microservice.]                                 │
│ --db                   <str>  Database driver: in-memory, sqlite, postgres.  │
│                               [default: sqlite]                              │
│ --help                        Show this message and exit.                    │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexastack new event-driven`

```text
Usage: hexastack new event-driven [OPTIONS] {name}

 Scaffold an Event-Driven service with CloudEvents and Transactional Outbox.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    name      <str>  Name of the new microservice project. [required]       │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --description  -d      <str>  Project description.                           │
│                               [default: An event-driven Hexastack service.]  │
│ --help                        Show this message and exit.                    │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexastack new graphql-service`

```text
Usage: hexastack new graphql-service [OPTIONS] {name}

 Scaffold a GraphQL data-graph gateway microservice (Strawberry + GraphiQL).

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    name      <str>  Name of the new microservice project. [required]       │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --description  -d      <str>  Project description.                           │
│                               [default: A modern GraphQL microservice        │
│                               powered by Hexastack.]                         │
│ --db                   <str>  Database driver: in-memory, sqlite, postgres.  │
│                               [default: in-memory]                           │
│ --help                        Show this message and exit.                    │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexastack new grpc-service`

```text
Usage: hexastack new grpc-service [OPTIONS] {name}

 Scaffold a high-performance gRPC microservice (Protobuf + Server Reflection).

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    name      <str>  Name of the new microservice project. [required]       │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --description  -d      <str>  Project description.                           │
│                               [default: A high-performance gRPC microservice │
│                               powered by Hexastack.]                         │
│ --db                   <str>  Database driver: in-memory, sqlite, postgres.  │
│                               [default: in-memory]                           │
│ --help                        Show this message and exit.                    │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexastack new mcp-agent`

```text
Usage: hexastack new mcp-agent [OPTIONS] {name}

 Scaffold an AI Model Context Protocol (MCP) server & agent tools service.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    name      <str>  Name of the new microservice project. [required]       │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --description  -d      <str>  Project description.                           │
│                               [default: An MCP AI agent tools service        │
│                               powered by Hexastack.]                         │
│ --help                        Show this message and exit.                    │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexastack new minimal`

```text
Usage: hexastack new minimal [OPTIONS] {name}

 Scaffold a lightweight CLI or worker service (Core + CQRS + Logging).

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    name      <str>  Name of the new microservice project. [required]       │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --description  -d      <str>  Project description.                           │
│                               [default: A lightweight Hexastack service.]    │
│ --help                        Show this message and exit.                    │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexastack new modules`

```text
Usage: hexastack new [OPTIONS] COMMAND [ARGS]...
Try 'hexastack new --help' for help.
╭─ Error ──────────────────────────────────────────────────────────────────────╮
│ No such command 'modules'.                                                   │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexastack new tools`

```text
Usage: hexastack new [OPTIONS] COMMAND [ARGS]...
Try 'hexastack new --help' for help.
╭─ Error ──────────────────────────────────────────────────────────────────────╮
│ No such command 'tools'.                                                     │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexastack new web-api`

```text
Usage: hexastack new web-api [OPTIONS] {name}

 Scaffold a RESTful Web API microservice (FastAPI + UoW + DevTools UI).

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    name      <str>  Name of the new microservice project. [required]       │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --description  -d      <str>  Project description.                           │
│                               [default: A modern RESTful microservice        │
│                               powered by Hexastack.]                         │
│ --db                   <str>  Database driver: in-memory, sqlite, postgres.  │
│                               [default: in-memory]                           │
│ --help                        Show this message and exit.                    │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `hexastack ping`

```text
Usage: hexastack ping [OPTIONS]

 Send a test ping command through the CQRS execution pipeline.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --message                 <str>                                              │
│ --output          -o      <str>  Output format: table, json, or plain        │
│                                  (CI/pipe friendly).                         │
│                                  [default: table]                            │
│ --input           -i      <str>  Input JSON payload string, file path, or    │
│                                  '-' for stdin.                              │
│ --quiet           -q             Quiet mode: suppress decorative terminal    │
│                                  output.                                     │
│ --debug                          Enable debug mode and render formatted      │
│                                  error tracebacks.                           │
│ --correlation-id          <str>  Explicit correlation ID for request         │
│                                  tracing.                                    │
│ --user-id                 <str>  Authenticated user context identifier.      │
│ --tenant-id               <str>  Tenant isolation identifier for             │
│                                  multi-tenancy.                              │
│ --help                           Show this message and exit.                 │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `hexastack profile`

```text
Usage: hexastack profile [OPTIONS] COMMAND [ARGS]...

 Profile CPU performance or memory allocations with interactive flamegraphs.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ cpu     Capture CPU flamegraph with py-spy (attach to PID or wrap server     │
│         command).                                                            │
│ memory  Generate memory allocation flamegraph using memray.                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexastack profile cpu`

```text
Usage: hexastack profile cpu [OPTIONS]

 Capture CPU flamegraph with py-spy (attach to PID or wrap server command).

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --pid       -p      <int>  Target process ID to attach to.                   │
│ --duration  -d      <int>  Profiling duration in seconds. [default: 15]      │
│ --output    -o      <str>  Output SVG flamegraph filepath.                   │
│                            [default: cpu_flamegraph.svg]                     │
│ --rate      -r      <int>  Samples per second. [default: 100]                │
│ --help                     Show this message and exit.                       │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### `hexastack profile memory`

```text
Usage: hexastack profile memory [OPTIONS]

 Generate memory allocation flamegraph using memray.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --bin     -b      <str>  Intermediate binary memory capture file.            │
│                          [default: mem_profile.bin]                          │
│ --output  -o      <str>  Output HTML flamegraph filepath.                    │
│                          [default: mem_flamegraph.html]                      │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `hexastack serve`

```text
Usage: hexastack serve [OPTIONS]

 Launch the Hexastack local development server (requires hexastack).

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --host    -h                 <str>  Bind host address. [default: 127.0.0.1]  │
│ --port    -p                 <int>  Bind port number. [default: 8000]        │
│ --reload      --no-reload           Enable live reloading. [default: reload] │
│ --help                              Show this message and exit.              │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `hexastack status`

```text
Usage: hexastack status [OPTIONS]

 Display installed Hexastack packages and optional dependency statuses.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --output          -o      <str>  Output format: table, json, or plain        │
│                                  (CI/pipe friendly).                         │
│                                  [default: table]                            │
│ --input           -i      <str>  Input JSON payload string, file path, or    │
│                                  '-' for stdin.                              │
│ --quiet           -q             Quiet mode: suppress decorative terminal    │
│                                  output.                                     │
│ --debug                          Enable debug mode and render formatted      │
│                                  error tracebacks.                           │
│ --correlation-id          <str>  Explicit correlation ID for request         │
│                                  tracing.                                    │
│ --user-id                 <str>  Authenticated user context identifier.      │
│ --tenant-id               <str>  Tenant isolation identifier for             │
│                                  multi-tenancy.                              │
│ --help                           Show this message and exit.                 │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `hexastack ui`

```text
Usage: hexastack ui [OPTIONS]

 Launch the Hexastack DevTools interactive web UI (requires hexastack).

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --host    -h                 <str>  Bind host. [default: 127.0.0.1]          │
│ --port    -p                 <int>  Bind port. [default: 8000]               │
│ --reload      --no-reload           Enable auto-reloading.                   │
│                                     [default: no-reload]                     │
│ --help                              Show this message and exit.              │
╰──────────────────────────────────────────────────────────────────────────────╯
```
