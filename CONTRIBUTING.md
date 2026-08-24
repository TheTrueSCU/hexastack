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

## Testing Requirements

| Test type | Required? | Location |
|---|---|---|
| Unit tests for all public API | ✅ Yes — enforced by `check-test-parity` | `tests/unit/` |
| Integration tests | ✅ For adapters and repositories | `tests/integration/` |
| Property-based (Hypothesis) | ✅ For core algorithmic logic | `tests/properties/` |
| Mutation testing (mutmut) | 🔄 Periodic CI — not required per PR | — |

`check-test-parity` runs in pre-commit and will block your commit if any public
module is missing a corresponding test file.

Run tests locally:

```bash
# Unit + integration
uv run pytest packages/

# Property-based fuzzing only
uv run pytest packages/*/tests/properties/
```

---

## Commit Message Format

Hexastack uses **[Conventional Commits](https://www.conventionalcommits.org/)**
— `python-semantic-release` reads them to bump versions and generate the CHANGELOG
automatically.

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

**Breaking changes** — add `!` after the type or a `BREAKING CHANGE:` footer:

```
feat!: remove deprecated SyncRepositoryPort

BREAKING CHANGE: SyncRepositoryPort has been removed. Use AsyncRepositoryPort instead.
```

---

## Pull Request Process

1. **Branch from `main`**: `git checkout -b feat/my-feature`
2. **Keep PRs focused** — one logical change per PR
3. **All pre-commit hooks must pass** before opening the PR
4. **CI must be green** — the `check` job (including `hypothesis`) is required for merge
5. **Update `CHANGELOG.md` entries are automatic** — do not edit it manually
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

## Security Issues

**Do not open a public GitHub issue for security vulnerabilities.**

Please follow the process in [SECURITY.md](SECURITY.md) and use GitHub's
private vulnerability reporting.

---

## License

By submitting a pull request you agree that your contribution will be licensed
under the [Apache License 2.0](LICENSE) — the same license as the project.
