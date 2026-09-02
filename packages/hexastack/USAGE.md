# Hexastack CLI & Framework Usage Guide (`hexastack`)

> Canonical reference guide and command catalog for the Hexastack Unified Developer CLI.

---

## 🚀 Unified Entrypoint (`hexastack`)

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

## 🛠️ Subcommand Reference Catalog

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

### `hexastack gRPC`

```text
Usage: hexastack [OPTIONS] COMMAND [ARGS]...
Try 'hexastack --help' for help.
╭─ Error ──────────────────────────────────────────────────────────────────────╮
│ No such command 'gRPC'.                                                      │
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
