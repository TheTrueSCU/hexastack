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
To apply a mutant on disk:
    mutmut apply <id>

To show a mutant:
    mutmut show <id>


Timed out ⏰ (34)

---- packages/hexastack_core/src/hexastack_core/adapters/logging/in_memory.py (3) ----

1730, 1733, 1735

---- packages/hexastack_core/src/hexastack_core/infra/autodiscovery.py (1) ----

1813

---- packages/hexastack_cqrs/src/hexastack_cqrs/infra/middleware/logging.py (7) ----

2276, 2278-2280, 2282, 2290-2291

---- packages/hexastack_events/src/hexastack_events/adapters/cloudevents/serializer.py (13) ----

2936-2937, 2944-2945, 2948-2949, 2953-2954, 2956-2958, 2964, 2966

---- packages/hexastack_fastapi/src/hexastack_fastapi/infra/exception_handlers.py (1) ----

3926

---- packages/hexastack_logging/src/hexastack_logging/infra/sanitizer.py (3) ----

4671-4673

---- packages/hexastack_otel/src/hexastack_otel/adapters/tracing/in_memory.py (6) ----

4945, 4952-4953, 4962, 4965, 4967

Survived 🙁 (1863)

---- packages/hexastack_ai/src/hexastack_ai/adapters/litellm.py (15) ----

5, 7-9, 11, 13-15, 17, 19-21, 23, 38, 54

---- packages/hexastack_ai/src/hexastack_ai/adapters/pydantic_ai.py (2) ----

111, 114

---- packages/hexastack_ai/src/hexastack_ai/domain/exceptions.py (4) ----

203-205, 207

---- packages/hexastack_ai/src/hexastack_ai/infra/bootstrap.py (4) ----

115, 124, 134-135

---- packages/hexastack_ai/src/hexastack_ai/infra/config.py (5) ----

167, 176-178, 193

---- packages/hexastack_ai/src/hexastack_ai/infra/tools.py (9) ----

137-140, 143, 146, 153-155

---- packages/hexastack_auth/src/hexastack_auth/adapters/fastapi.py (19) ----

244-246, 254, 257, 260-261, 264, 266, 273, 275-282, 285

---- packages/hexastack_auth/src/hexastack_auth/adapters/grpc.py (10) ----

289, 299-303, 308-309, 317-318

---- packages/hexastack_auth/src/hexastack_auth/adapters/in_memory.py (5) ----

217, 219, 233, 236, 238

---- packages/hexastack_auth/src/hexastack_auth/adapters/jwt.py (10) ----

320, 350, 352-353, 355, 358, 367-369, 373

---- packages/hexastack_auth/src/hexastack_auth/adapters/opa/policy.py (11) ----

468-471, 473, 475-478, 480, 506

---- packages/hexastack_auth/src/hexastack_auth/adapters/openfga/policy.py (9) ----

419-421, 425-426, 428, 433, 444, 450

---- packages/hexastack_auth/src/hexastack_auth/adapters/password.py (8) ----

382, 384, 387, 389, 398, 409, 417-418

---- packages/hexastack_auth/src/hexastack_auth/adapters/spiffe/workload.py (12) ----

452-454, 456-463, 466

---- packages/hexastack_auth/src/hexastack_auth/domain/models.py (8) ----

701, 705, 712, 718, 723, 727, 729, 731

---- packages/hexastack_auth/src/hexastack_auth/infra/bootstrap.py (6) ----

515, 529-533

---- packages/hexastack_auth/src/hexastack_auth/infra/config.py (26) ----

542-565, 577, 580

---- packages/hexastack_auth/src/hexastack_auth/infra/decorators.py (12) ----

672, 674, 684-692, 694

---- packages/hexastack_auth/src/hexastack_auth/infra/middleware.py (26) ----

604, 608, 610, 613, 615, 622, 630-633, 639, 641, 645, 647-653, 656, 662-665, 671

---- packages/hexastack_auth/src/hexastack_auth/ports/password.py (2) ----

213-214

---- packages/hexastack_auth/src/hexastack_auth/ports/policy.py (1) ----

212

---- packages/hexastack_auth/src/hexastack_auth/ports/security.py (2) ----

209-210

---- packages/hexastack_auth/src/hexastack_auth/ports/workload.py (1) ----

211

---- packages/hexastack_cli/src/hexastack_cli/adapters/app.py (5) ----

1140, 1142, 1147, 1152-1153

---- packages/hexastack_cli/src/hexastack_cli/adapters/presenter.py (15) ----

1097-1098, 1101-1102, 1105, 1109, 1112, 1115, 1117, 1119, 1123-1124, 1126, 1133-1134

---- packages/hexastack_cli/src/hexastack_cli/adapters/routing.py (20) ----

947-948, 966, 975, 995, 998, 1002-1003, 1009, 1012, 1041-1043, 1047, 1049-1052, 1054, 1078

---- packages/hexastack_cli/src/hexastack_cli/infra/autodiscovery.py (17) ----

1201-1203, 1205, 1208-1209, 1211-1213, 1218, 1221, 1225, 1227-1228, 1232, 1241, 1244

---- packages/hexastack_cli/src/hexastack_cli/infra/bootstrap.py (14) ----

1154-1156, 1160-1169, 1172

---- packages/hexastack_cli/src/hexastack_cli/infra/config.py (2) ----

1177-1178

---- packages/hexastack_cli/src/hexastack_cli/infra/decorators.py (15) ----

1247, 1249, 1251, 1254-1256, 1258, 1260, 1263, 1265-1266, 1269, 1279, 1281-1282

---- packages/hexastack_cli/src/hexastack_cli/testing/narrator.py (66) ----

734, 736-737, 739-740, 743-744, 748-749, 755-758, 761-767, 769-777, 779-784, 786, 788-790, 793-796, 798-799, 801-803, 805, 807, 812, 814-816, 818-819, 821-824, 826-827, 829-831, 833

---- packages/hexastack_cli/src/hexastack_cli/testing/terminal.py (72) ----

835, 837-840, 843, 845-846, 849-853, 855-856, 863-864, 869-871, 876-886, 889-894, 896-898, 901-904, 907-914, 916-918, 921, 923-926, 928-929, 931-934, 936-937, 939-941, 943

---- packages/hexastack_core/src/hexastack_core/adapters/ai/in_memory.py (34) ----

1648-1652, 1655, 1658, 1661-1671, 1678-1682, 1687, 1689-1690, 1694, 1697, 1707-1710, 1716-1717

---- packages/hexastack_core/src/hexastack_core/adapters/cache/in_memory.py (4) ----

1625, 1632, 1638, 1640

---- packages/hexastack_core/src/hexastack_core/adapters/feature_flags/config.py (15) ----

1529, 1539, 1545, 1549, 1551-1555, 1565, 1569, 1573, 1577, 1581, 1590

---- packages/hexastack_core/src/hexastack_core/adapters/feature_flags/in_memory.py (2) ----

1601, 1604

---- packages/hexastack_core/src/hexastack_core/adapters/logging/in_memory.py (7) ----

1722, 1724-1727, 1729, 1731

---- packages/hexastack_core/src/hexastack_core/adapters/notification.py (6) ----

1440, 1445, 1447, 1449, 1451, 1455

---- packages/hexastack_core/src/hexastack_core/adapters/unit_of_work/in_memory.py (10) ----

1459, 1478, 1483, 1486, 1495-1496, 1499-1500, 1505, 1510

---- packages/hexastack_core/src/hexastack_core/domain/feature_flags.py (27) ----

1874-1890, 1892, 1894, 1902, 1904-1910

---- packages/hexastack_core/src/hexastack_core/domain/generic.py (1) ----

1862

---- packages/hexastack_core/src/hexastack_core/domain/result.py (5) ----

1864-1866, 1868-1869

---- packages/hexastack_core/src/hexastack_core/infra/autodiscovery.py (12) ----

1805-1808, 1812, 1814-1817, 1820, 1822-1823

---- packages/hexastack_core/src/hexastack_core/infra/bootstrap.py (31) ----

1741-1744, 1746-1751, 1757, 1759, 1762-1766, 1771-1772, 1775-1776, 1778-1780, 1782, 1785, 1787-1790, 1792

---- packages/hexastack_core/src/hexastack_core/infra/config.py (2) ----

1802, 1804

---- packages/hexastack_core/src/hexastack_core/infra/decorators.py (2) ----

1827, 1829

---- packages/hexastack_core/src/hexastack_core/infra/registries/config.py (2) ----

1831, 1833

---- packages/hexastack_core/src/hexastack_core/infra/registries/generic.py (4) ----

1844, 1849, 1851, 1854

---- packages/hexastack_core/src/hexastack_core/ports/ai.py (6) ----

1302-1307

---- packages/hexastack_core/src/hexastack_core/ports/bootstrap.py (1) ----

1284

---- packages/hexastack_core/src/hexastack_core/ports/cache.py (10) ----

1285-1294

---- packages/hexastack_core/src/hexastack_core/ports/clock.py (2) ----

1341-1342

---- packages/hexastack_core/src/hexastack_core/ports/feature_flags.py (4) ----

1327-1330

---- packages/hexastack_core/src/hexastack_core/ports/logging.py (6) ----

1295-1300

---- packages/hexastack_core/src/hexastack_core/ports/notification.py (5) ----

1320-1323, 1326

---- packages/hexastack_core/src/hexastack_core/ports/presenter.py (1) ----

1301

---- packages/hexastack_core/src/hexastack_core/ports/repository.py (10) ----

1308-1317

---- packages/hexastack_core/src/hexastack_core/ports/unit_of_work.py (6) ----

1331, 1334-1336, 1339-1340

---- packages/hexastack_core/src/hexastack_core/testing/architecture.py (31) ----

1344-1347, 1349-1351, 1353, 1355-1361, 1363-1378

---- packages/hexastack_core/src/hexastack_core/testing/flags.py (3) ----

1428, 1432, 1436

---- packages/hexastack_core/src/hexastack_core/testing/harness.py (4) ----

1409-1411, 1414

---- packages/hexastack_core/src/hexastack_core/testing/hypothesis.py (6) ----

1394-1395, 1399-1400, 1402, 1408

---- packages/hexastack_core/src/hexastack_core/testing/isolation.py (2) ----

1423, 1425

---- packages/hexastack_core/src/hexastack_core/testing/synthetic.py (8) ----

1379-1382, 1385, 1390-1392

---- packages/hexastack_core/src/hexastack_core/utils/context.py (8) ----

1911, 1913-1917, 1919-1920

---- packages/hexastack_core/src/hexastack_core/utils/inspection.py (6) ----

1928-1929, 1931, 1936, 1938-1939

---- packages/hexastack_cqrs/src/hexastack_cqrs/adapters/buses/command/asynchronous.py (5) ----

2018-2019, 2025, 2035, 2038

---- packages/hexastack_cqrs/src/hexastack_cqrs/adapters/buses/event/asynchronous.py (3) ----

1958-1959, 1980

---- packages/hexastack_cqrs/src/hexastack_cqrs/adapters/buses/event/recording.py (4) ----

1995-1996, 2000-2001

---- packages/hexastack_cqrs/src/hexastack_cqrs/domain/handlers.py (1) ----

2437

---- packages/hexastack_cqrs/src/hexastack_cqrs/infra/autodiscovery.py (7) ----

2141, 2156, 2158, 2160, 2164, 2166-2167

---- packages/hexastack_cqrs/src/hexastack_cqrs/infra/bootstrap.py (8) ----

2053, 2067, 2071-2072, 2083-2084, 2092-2093

---- packages/hexastack_cqrs/src/hexastack_cqrs/infra/decorators.py (24) ----

2211, 2213, 2215, 2217-2220, 2223-2225, 2229, 2232, 2234, 2236, 2238, 2240-2245, 2247, 2249-2250

---- packages/hexastack_cqrs/src/hexastack_cqrs/infra/middleware/caching.py (31) ----

2320-2325, 2327-2331, 2333, 2339, 2343, 2345, 2348, 2350, 2352, 2359-2362, 2369, 2377, 2379, 2383-2388

---- packages/hexastack_cqrs/src/hexastack_cqrs/infra/middleware/correlation.py (2) ----

2310, 2317

---- packages/hexastack_cqrs/src/hexastack_cqrs/infra/middleware/feature_flag.py (7) ----

2426-2427, 2429-2430, 2433-2434, 2436

---- packages/hexastack_cqrs/src/hexastack_cqrs/infra/middleware/logging.py (8) ----

2271, 2274, 2283, 2285-2289

---- packages/hexastack_cqrs/src/hexastack_cqrs/infra/middleware/retry.py (4) ----

2405, 2408, 2412, 2414

---- packages/hexastack_cqrs/src/hexastack_cqrs/infra/middleware/timing.py (6) ----

2298, 2300, 2303, 2306, 2308-2309

---- packages/hexastack_cqrs/src/hexastack_cqrs/infra/middleware/unit_of_work.py (1) ----

2425

---- packages/hexastack_cqrs/src/hexastack_cqrs/infra/pipeline.py (6) ----

2190, 2193-2194, 2198, 2204, 2207

---- packages/hexastack_cqrs/src/hexastack_cqrs/infra/registries/presenter.py (3) ----

2255-2256, 2260

---- packages/hexastack_cqrs/src/hexastack_cqrs/ports/buses.py (3) ----

1940-1942

---- packages/hexastack_db/src/hexastack_db/adapters/repository.py (8) ----

2440-2441, 2453, 2459, 2462-2463, 2473, 2479

---- packages/hexastack_db/src/hexastack_db/adapters/unit_of_work.py (8) ----

2601, 2604-2605, 2610, 2613, 2616-2617, 2622

---- packages/hexastack_db/src/hexastack_db/adapters/vector.py (11) ----

2488, 2493, 2504, 2533, 2538, 2548, 2575, 2593-2594, 2596, 2598

---- packages/hexastack_db/src/hexastack_db/domain/exceptions.py (2) ----

2905-2906

---- packages/hexastack_db/src/hexastack_db/infra/bootstrap.py (18) ----

2623, 2625, 2632-2637, 2643, 2653, 2666-2667, 2670-2671, 2674-2675, 2678-2679

---- packages/hexastack_db/src/hexastack_db/infra/config.py (4) ----

2734, 2737, 2768-2769

---- packages/hexastack_db/src/hexastack_db/infra/engine.py (38) ----

2829-2830, 2837-2838, 2841, 2843-2850, 2858, 2861-2868, 2870-2873, 2880, 2886, 2890-2897, 2899-2900

---- packages/hexastack_db/src/hexastack_db/infra/migrations.py (19) ----

2686, 2689-2690, 2695-2696, 2701, 2704-2712, 2716-2719

---- packages/hexastack_db/src/hexastack_db/infra/mixins.py (4) ----

2811-2812, 2817, 2823

---- packages/hexastack_events/src/hexastack_events/adapters/cloudevents/serializer.py (5) ----

2943, 2965, 2973-2975

---- packages/hexastack_events/src/hexastack_events/adapters/notifications/apprise.py (5) ----

2920-2921, 2925, 2927-2928

---- packages/hexastack_events/src/hexastack_events/adapters/outbox/asyncio.py (14) ----

2978, 2986-2987, 2991-2996, 3002-3003, 3006, 3014, 3016

---- packages/hexastack_events/src/hexastack_events/adapters/outbox/huey.py (5) ----

3089, 3093, 3097, 3099-3100

---- packages/hexastack_events/src/hexastack_events/adapters/outbox/in_memory.py (3) ----

3018, 3020-3021

---- packages/hexastack_events/src/hexastack_events/adapters/outbox/sqlalchemy.py (12) ----

3030-3031, 3037, 3041-3043, 3048, 3056, 3060, 3063-3064, 3067

---- packages/hexastack_events/src/hexastack_events/domain/context.py (3) ----

3236, 3242, 3244

---- packages/hexastack_events/src/hexastack_events/domain/models.py (11) ----

3186, 3188, 3190, 3194, 3207, 3210, 3214, 3216, 3219, 3232, 3234

---- packages/hexastack_events/src/hexastack_events/infra/bootstrap.py (4) ----

3114, 3120, 3122, 3124

---- packages/hexastack_events/src/hexastack_events/infra/config.py (2) ----

3144-3145

---- packages/hexastack_events/src/hexastack_events/infra/middleware.py (2) ----

3178, 3183

---- packages/hexastack_events/src/hexastack_events/ports/buses.py (2) ----

2917-2918

---- packages/hexastack_events/src/hexastack_events/ports/outbox.py (10) ----

2907-2916

---- packages/hexastack_fastapi/src/hexastack_fastapi/adapters/app.py (4) ----

3738, 3741, 3748-3749

---- packages/hexastack_fastapi/src/hexastack_fastapi/adapters/db_session.py (3) ----

3696, 3700, 3702

---- packages/hexastack_fastapi/src/hexastack_fastapi/adapters/dependencies.py (13) ----

3704-3706, 3708-3712, 3717-3718, 3729-3730, 3732

---- packages/hexastack_fastapi/src/hexastack_fastapi/adapters/docs.py (12) ----

3668-3670, 3675, 3677, 3679-3682, 3687-3688, 3692

---- packages/hexastack_fastapi/src/hexastack_fastapi/adapters/health.py (4) ----

3755, 3761, 3774-3775

---- packages/hexastack_fastapi/src/hexastack_fastapi/adapters/routing.py (5) ----

3640-3641, 3645-3647

---- packages/hexastack_fastapi/src/hexastack_fastapi/adapters/ui.py (205) ----

3414-3416, 3419-3422, 3424, 3426-3430, 3432-3435, 3438-3463, 3465-3523, 3526-3531, 3533-3564, 3567-3568, 3570-3574, 3576-3577, 3580-3635

---- packages/hexastack_fastapi/src/hexastack_fastapi/infra/autodiscovery.py (4) ----

3868, 3871, 3874, 3877

---- packages/hexastack_fastapi/src/hexastack_fastapi/infra/bootstrap.py (10) ----

3785, 3787-3795

---- packages/hexastack_fastapi/src/hexastack_fastapi/infra/config.py (7) ----

3823-3827, 3836-3837

---- packages/hexastack_fastapi/src/hexastack_fastapi/infra/decorators.py (19) ----

3929, 3931, 3933-3936, 3938, 3940, 3943, 3945-3946, 3950, 3954, 3961, 3963-3965, 3970, 3972

---- packages/hexastack_fastapi/src/hexastack_fastapi/infra/exception_handlers.py (5) ----

3885, 3896, 3898, 3900, 3903

---- packages/hexastack_fastapi/src/hexastack_fastapi/infra/middleware/correlation.py (3) ----

4038, 4056, 4058

---- packages/hexastack_fastapi/src/hexastack_fastapi/infra/middleware/logging.py (16) ----

3978, 3988, 3992, 3995, 4002-4003, 4009, 4012-4016, 4018, 4023, 4028-4029

---- packages/hexastack_fastapi/src/hexastack_fastapi/testing/cursor.py (27) ----

3285-3311

---- packages/hexastack_fastapi/src/hexastack_fastapi/testing/recorder.py (102) ----

3312-3413

---- packages/hexastack_fastapi/src/hexastack_fastapi/testing/server.py (32) ----

3252-3283

---- packages/hexastack_flags/src/hexastack_flags/adapters/openfeature.py (35) ----

4079, 4081-4086, 4088-4101, 4105-4112, 4114-4119

---- packages/hexastack_flags/src/hexastack_flags/adapters/providers/factory.py (32) ----

4126-4153, 4156, 4159-4160, 4165

---- packages/hexastack_flags/src/hexastack_flags/domain/models.py (10) ----

4211, 4217, 4219-4226

---- packages/hexastack_flags/src/hexastack_flags/infra/bootstrap.py (3) ----

4179, 4181, 4184

---- packages/hexastack_flags/src/hexastack_flags/infra/config.py (9) ----

4186-4187, 4189, 4196-4197, 4199-4200, 4203, 4206

---- packages/hexastack_grpc/src/hexastack_grpc/adapters/server.py (2) ----

4228, 4231

---- packages/hexastack_grpc/src/hexastack_grpc/domain/models.py (9) ----

4428, 4430-4437

---- packages/hexastack_grpc/src/hexastack_grpc/infra/autodiscovery.py (1) ----

4330

---- packages/hexastack_grpc/src/hexastack_grpc/infra/bootstrap.py (9) ----

4233, 4235-4237, 4239, 4243, 4245, 4247, 4249

---- packages/hexastack_grpc/src/hexastack_grpc/infra/compiler.py (17) ----

4267-4269, 4271-4272, 4274-4275, 4280, 4289, 4294, 4297-4298, 4302-4303, 4307-4308, 4310

---- packages/hexastack_grpc/src/hexastack_grpc/infra/config.py (2) ----

4311-4312

---- packages/hexastack_grpc/src/hexastack_grpc/infra/decorators.py (2) ----

4333, 4335

---- packages/hexastack_grpc/src/hexastack_grpc/infra/dispatch.py (2) ----

4258, 4266

---- packages/hexastack_grpc/src/hexastack_grpc/infra/interceptors/exception.py (1) ----

4392

---- packages/hexastack_grpc/src/hexastack_grpc/infra/interceptors/generic.py (12) ----

4410, 4417-4427

---- packages/hexastack_grpc/src/hexastack_grpc/infra/interceptors/logging.py (11) ----

4364, 4366-4367, 4369-4371, 4373-4377

---- packages/hexastack_grpc/src/hexastack_grpc/infra/registries/service.py (8) ----

4347, 4349, 4353-4356, 4359-4360

---- packages/hexastack_logging/src/hexastack_logging/adapters/logger/loguru.py (1) ----

4470

---- packages/hexastack_logging/src/hexastack_logging/adapters/logger/rich.py (2) ----

4442, 4447

---- packages/hexastack_logging/src/hexastack_logging/adapters/logger/structlog.py (1) ----

4490

---- packages/hexastack_logging/src/hexastack_logging/adapters/logger/structured.py (2) ----

4501, 4506

---- packages/hexastack_logging/src/hexastack_logging/infra/bootstrap.py (8) ----

4510-4513, 4515-4516, 4520-4521

---- packages/hexastack_logging/src/hexastack_logging/infra/config.py (12) ----

4553-4554, 4574, 4576, 4578-4579, 4591-4594, 4598, 4602

---- packages/hexastack_logging/src/hexastack_logging/infra/filters.py (23) ----

4611-4633

---- packages/hexastack_logging/src/hexastack_logging/infra/formatters/console.py (7) ----

4692-4693, 4702, 4712-4713, 4715, 4727

---- packages/hexastack_logging/src/hexastack_logging/infra/formatters/json.py (2) ----

4729, 4738

---- packages/hexastack_logging/src/hexastack_logging/infra/sanitizer.py (10) ----

4645, 4647-4651, 4653-4656

---- packages/hexastack_mcp/src/hexastack_mcp/adapters/fastapi.py (4) ----

4748-4751

---- packages/hexastack_mcp/src/hexastack_mcp/domain/metadata.py (10) ----

4909, 4911-4912, 4915, 4917, 4919, 4923, 4925, 4927, 4929

---- packages/hexastack_mcp/src/hexastack_mcp/infra/autodiscovery.py (3) ----

4811, 4814, 4817

---- packages/hexastack_mcp/src/hexastack_mcp/infra/bootstrap.py (14) ----

4753, 4755-4757, 4759, 4764-4770, 4774-4775

---- packages/hexastack_mcp/src/hexastack_mcp/infra/config.py (15) ----

4777-4778, 4782, 4784, 4792, 4794-4795, 4798-4805

---- packages/hexastack_mcp/src/hexastack_mcp/infra/decorators.py (11) ----

4820, 4822, 4824, 4827-4828, 4834-4836, 4842-4844

---- packages/hexastack_mcp/src/hexastack_mcp/infra/registries/server.py (13) ----

4855, 4859-4862, 4874, 4876, 4884, 4886, 4888, 4892, 4897, 4901

---- packages/hexastack_otel/src/hexastack_otel/adapters/tracing/in_memory.py (7) ----

4942-4943, 4948, 4954, 4958, 4982, 4995

---- packages/hexastack_otel/src/hexastack_otel/adapters/tracing/otel.py (15) ----

5001-5005, 5009-5010, 5012-5014, 5024-5028

---- packages/hexastack_otel/src/hexastack_otel/domain/context.py (5) ----

5116, 5118-5121

---- packages/hexastack_otel/src/hexastack_otel/infra/bootstrap.py (6) ----

5038, 5041, 5048-5049, 5053-5054

---- packages/hexastack_otel/src/hexastack_otel/infra/config.py (2) ----

5063-5064

---- packages/hexastack_otel/src/hexastack_otel/infra/middleware.py (14) ----

5091, 5094, 5099-5101, 5105, 5108-5115

---- packages/hexastack_otel/src/hexastack_otel/ports/tracing.py (11) ----

4931-4941

Untested/skipped (303)

---- packages/hexastack_ai/src/hexastack_ai/infra/config.py (18) ----

157, 160, 163, 165-166, 169, 172, 174-175, 180, 183, 186, 189, 191-192, 194, 196, 198

---- packages/hexastack_auth/src/hexastack_auth/infra/config.py (14) ----

567, 570, 573, 575-576, 578-579, 581-582, 584, 586-587, 589, 595

---- packages/hexastack_cli/src/hexastack_cli/adapters/app.py (1) ----

1146

---- packages/hexastack_cli/src/hexastack_cli/adapters/routing.py (17) ----

951, 956, 963, 968, 972, 977, 982, 1025-1026, 1084-1087, 1091-1094

---- packages/hexastack_cli/src/hexastack_cli/infra/config.py (13) ----

1179-1191

---- packages/hexastack_core/src/hexastack_core/infra/config.py (6) ----

1793-1798

---- packages/hexastack_cqrs/src/hexastack_cqrs/infra/config.py (36) ----

2097-2130, 2136-2137

---- packages/hexastack_db/src/hexastack_db/infra/config.py (33) ----

2721, 2724, 2727, 2730, 2732-2733, 2735-2736, 2739, 2742, 2745, 2748, 2750-2752, 2754, 2756-2758, 2760, 2763, 2766, 2771, 2774, 2777, 2780, 2783, 2786, 2789, 2792, 2794, 2796, 2798

---- packages/hexastack_events/src/hexastack_events/domain/models.py (16) ----

3191-3193, 3196, 3198-3200, 3203, 3205-3206, 3208-3209, 3212, 3215, 3217-3218

---- packages/hexastack_events/src/hexastack_events/infra/config.py (10) ----

3147, 3149-3152, 3154, 3157, 3160, 3163, 3166

---- packages/hexastack_fastapi/src/hexastack_fastapi/adapters/routing.py (6) ----

3652-3653, 3660-3661, 3666-3667

---- packages/hexastack_fastapi/src/hexastack_fastapi/infra/config.py (48) ----

3802-3822, 3830-3835, 3838-3855, 3860-3862

---- packages/hexastack_flags/src/hexastack_flags/domain/models.py (1) ----

4227

---- packages/hexastack_flags/src/hexastack_flags/infra/config.py (9) ----

4188, 4190-4195, 4202, 4204

---- packages/hexastack_grpc/src/hexastack_grpc/infra/config.py (5) ----

4314, 4317, 4320, 4323, 4326

---- packages/hexastack_logging/src/hexastack_logging/infra/config.py (43) ----

4523-4552, 4555-4566, 4570

---- packages/hexastack_mcp/src/hexastack_mcp/infra/config.py (8) ----

4780, 4783, 4786, 4789, 4791, 4793, 4796, 4807

---- packages/hexastack_mcp/src/hexastack_mcp/infra/decorators.py (6) ----

4831-4832, 4839-4840, 4847-4848

---- packages/hexastack_mcp/src/hexastack_mcp/infra/registries/server.py (4) ----

4871-4872, 4875, 4887

---- packages/hexastack_otel/src/hexastack_otel/infra/config.py (9) ----

5066, 5069, 5071-5074, 5076, 5079, 5082
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
