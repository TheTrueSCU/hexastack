# Contributing to Hexastack

Thank you for your interest in contributing! This document covers everything
you need to get from zero to a merged pull request.

---

## Quick Start

```bash
# 1. Fork the repo on GitHub, then clone your fork
git clone https://github.com/<your-username>/hexastack.git
cd hexastack

# 2. Install all workspace packages, extras, and dev tooling
uv sync --all-packages --all-extras --all-groups

# 3. Install the pre-commit hooks (runs on every commit)
uv run pre-commit install
```

That's it. The first `git commit` will run all 26 hooks automatically.

---

## Project Structure

```
hexastack/
├── packages/          # Individual PyPI packages (hexastack-core, hexastack-auth, …)
│   └── <pkg>/
│       ├── src/<pkg>/ # Source code
│       └── tests/     # Unit, integration, and property-based tests
├── scripts/           # Monorepo tooling (pre-commit helpers, diagram generation, …)
└── docs/              # MkDocs documentation site
```

Each directory under `packages/` is an independently publishable PyPI package
that participates in the `uv` workspace.

---

## Architectural Rules (Non-Negotiable)

Hexastack enforces the **Hexagonal Architecture golden rules** automatically via
`import-linter`. Violations block the commit.

| Layer | May import from | Must NOT import from |
|---|---|---|
| **Domain** (`domain/`) | Nothing framework-specific | FastAPI, SQLAlchemy, Typer, gRPC, … |
| **Ports** (`ports/`) | Domain only | Adapters, infrastructure |
| **Adapters** (`adapters/`) | Ports + Domain | Other adapters directly |

If `import-linter` rejects your commit, the architecture is wrong — not the rule.
Do not add exclusions without a maintainer discussion.

---

## Code Standards

| Tool | Standard |
|---|---|
| **Linting** | `ruff` — auto-fixed in pre-commit; zero warnings policy |
| **Formatting** | `ruff format` — enforced in pre-commit |
| **Type checking** | `ty` strict — no `Any` escapes, no untyped defs |
| **Complexity** | `complexipy` — max cognitive complexity **25** per function |
| **Dead code** | `vulture` — no unused public symbols |

### Docstrings

All public API must use **Google-style docstrings** with the following sections:

```python
def my_function(x: int) -> str:
    """One-line summary.

    Args:
        x: Description of the parameter.

    Returns:
        Description of the return value.

    Raises:
        ValueError: When x is negative.

    Notes/Architectural Intent:
        Explain non-obvious design decisions or invariants here.
    """
```

---

## Testing Requirements & Change Proposal Policy

### Automated Test Policy for New Functionality
**It is a strict project policy that all pull requests and change proposals introducing new functionality, modifying existing behavior, or fixing defects MUST include corresponding automated tests.** Change proposals without accompanying tests will not be reviewed or merged.

| Test type | Required? | Location | Scope / Policy |
|---|---|---|---|
| Unit tests for all public API | ✅ Yes — mandatory | `tests/unit/` | 100% parity across public classes, functions, and handlers. Enforced by `check-test-parity`. |
| Integration tests | ✅ Yes — mandatory | `tests/integration/` | Required for all database, outbox, gRPC, and third-party adapters. |
| Property-based (Hypothesis) | ✅ Yes — mandatory | `tests/properties/` | Required for serialization algorithms, domain logic, and state machines. |
| End-to-End & Browser (Playwright) | ✅ Yes | `tests/e2e/` | Required for new CLI workflows and UI dashboard views. |
| Mutation testing (mutmut) | 🔄 Periodic CI | — | Automated periodic regression suite. |

`check-test-parity` runs in pre-commit and will block commits if any public module is missing a corresponding test suite. Minimum line coverage must remain $\ge 90\%$.

Run tests locally:

```bash
# Unit + integration
uv run pytest packages/

# Property-based fuzzing only
uv run pytest packages/*/tests/properties/
```

---

## Commit Message Format

Hexastack uses standard structured commit messages:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

| Type | When to use |
|---|---|
| `feat` | A new feature |
| `fix` | A bug fix |
| `docs` | Documentation changes only |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `test` | Adding or correcting tests |
| `chore` | Build process, tooling, dependency updates |
| `perf` | Performance improvements |

---

## Pull Request Process

1. **Branch from `main`**: `git checkout -b feat/my-feature`
2. **Keep PRs focused** — one logical change per PR
3. **All pre-commit hooks must pass** before opening the PR
4. **CI must be green** — all required quality gates must pass for merge
6. Request a review from a maintainer; at least one approval is required

---

## Protobuf Changes

Hexastack uses [Buf](https://buf.build) for `.proto` linting and breaking-change detection.

```bash
# Lint proto files
buf lint

# Check for breaking changes against main
buf breaking --against 'https://github.com/TheTrueSCU/hexastack.git#branch=main'
```

Breaking changes to `.proto` files (field removals, type changes, renumbering)
require an **explicit maintainer discussion before implementation**. Wire
compatibility is a hard constraint for any released gRPC service.

---

## Developer Certificate of Origin (DCO)

All contributions to Hexastack must be accompanied by a Developer Certificate of Origin sign-off. By adding a `Signed-off-by` line in your commit message, you certify the requirements outlined in [DCO.md](DCO.md):

```bash
git commit -s -m "feat: add support for Redis cache invalidation"
```

---

## Code of Conduct

We are committed to providing a friendly, safe, and welcoming environment. All participants are expected to adhere to our [Code of Conduct](CODE_OF_CONDUCT.md).

---

## Security Issues

**Do not open a public GitHub issue for security vulnerabilities.**

Please follow the process in [SECURITY.md](SECURITY.md) and use GitHub's
private vulnerability reporting.

---

## License

By submitting a pull request you agree that your contribution will be licensed
under the [Apache License 2.0](LICENSE) — the same license as the project.
