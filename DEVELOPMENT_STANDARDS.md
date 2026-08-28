# Development Standards & CI/CD Pipeline

This document defines the standard for professional, type-safe, and robust Python project maintenance.

## 1. Robust Testing Strategy (Tiered)

To balance development speed with code reliability, we employ a tiered testing approach.

### Unit & Integration Tests (Fast Lane)
*   **Location:** `tests/unit/`, `tests/integration/`
*   **Responsibility:** Validate core business logic and "golden path" scenarios.
*   **Execution:** Run on every commit via local development and the `check` job in CI.
*   **Code Coverage Gate:** Enforces `>=90%` statement coverage gate across production packages (`--cov-fail-under=90`).
*   **Parallelization & Randomization:** Tests run concurrently across CPU cores via `pytest-xdist` (`-n auto`) and with randomized test execution order via `pytest-randomly` to ensure zero hidden test state dependencies or test pollution.

### Property-Based Fuzzing (Robustness Lane)
*   **Location:** `tests/properties/`
*   **Dependency:** `hypothesis`
*   **Responsibility:** Discover edge-case failures through stress-testing complex structures.
*   **Execution:** Runs only during the Pull Request process (`hypothesis` job in CI) to maintain CI speed for main.

### Mutation Testing (Deep Quality Lane)
*   **Dependency:** `mutmut<3` (v2.x AST engine).
*   **Configuration:** `mutmut_config.py` filters non-logical boilerplate, type annotations, and logging to prevent false positives.
*   **Execution:** On-demand or scheduled via `scripts/run_mutation_tests.py --package <name>`.

---

## 2. CI/CD Pipeline Configuration (.github/workflows/ci.yml)

The CI pipeline enforces quality through a multi-stage dependency chain.

```yaml
jobs:
  check:
    # Executes pre-commit run --all-files (DRY quality checks: ruff, ty, import-linter, etc.)
    # and runs unit/integration tests with pytest-xdist and pytest-randomly.
    # Must pass before any other jobs trigger.

  hypothesis:
    # Runs property-based fuzzing tests with hypothesis.
    needs: check
    if: github.event_name == 'pull_request'
    # Executes only during PR review to save CI resources.
```

---

## 3. Pre-Commit Enforcement (.pre-commit-config.yaml)

We use pre-commit to ensure code quality **before** it hits the repository.

*   **Hexagonal Architecture Enforcement:** `import-linter` (`lint-imports`) enforcing strict domain/ports purity and inter-package independence.
*   **Linting & Formatting:** `ruff` (with `--fix`) and `ruff-format`.
*   **Standard Hooks:** Trailing whitespace, end-of-file fixes, YAML validation, large file checks.
*   **Type Safety:** `ty check` (using `language: system` to leverage uv environments).

---

## 4. Implementation Protocol

When applying these standards to a new project, follow this sequence:

1.  **Dependencies:** Install dev tools (`uv add --group dev hypothesis pre-commit`).
2.  **Standards:** Add `.pre-commit-config.yaml` and install hooks (`pre-commit install`).
3.  **CI:** Configure `.github/workflows/ci.yml` with the tiered `check` -> `hypothesis` logic.
4.  **Testing:** Initialize `tests/properties/` and implement fuzzer strategies relevant to the project's domain.
5.  **Validation:** Run `pre-commit run --all-files` and verify the CI pipeline passes.

---

## 5. Dependency Auto-Merge Protocol
To automate dependency maintenance safely:
1.  **Enable Auto-Merge:** Ensure "Allow auto-merge" is enabled in Repository Settings.
2.  **Branch Protection:** Require status checks (CI) to pass before merging to main.
3.  **Automate:** Add the workflow to `.github/workflows/dependabot-auto-merge.yml`:
    ```yaml
    name: Dependabot Auto-Merge
    on:
      pull_request:
        types: [opened, synchronize, reopened]
    permissions:
      pull-requests: write
      contents: write
    jobs:
      auto-merge:
        runs-on: ubuntu-latest
        if: github.actor == 'dependabot[bot]'
        steps:
          - name: Enable auto-merge
            run: gh pr merge --auto --merge "$PR_URL"
            env:
              PR_URL: ${{ github.event.pull_request.html_url }}
              GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    ```

---

## 6. Release & Distribution Protocol
Hexastack releases are versioned synchronously across all 15 monorepo packages:
1. **Version Bump & Changelog:** Maintainers bump package versions across `pyproject.toml` and update `CHANGELOG.md` via a standard release pull request (`chore(release): vX.Y.Z`).
2. **Tagging:** After the release PR is merged into `main`, tag the release (`git tag -a vX.Y.Z -m "Release vX.Y.Z"` and `git push origin vX.Y.Z`).
3. **Automated Distribution:** The `.github/workflows/release.yml` pipeline triggers on the tag push, builds all distribution wheels, publishes to PyPI with trusted publishing attestations, and attaches SPDX/CycloneDX SBOMs to the GitHub release.

---

## 7. CLI & Scaffolding Modularity Guidelines
To prevent monolithic file bloat and ensure high testability:
1. **CLI Commands Modularity:** CLI command groups in `hexastack.adapters.cli.*` must be organized in dedicated subdirectories (`commands/`) split by transport and domain concern (e.g. `db.py`, `dev.py`, `fastapi.py`, `graphql.py`, `grpc.py`, `init.py`, `inspect.py`, `mcp.py`, `new.py`, `outbox.py`, `profiling.py`, `serve.py`, `ui.py`).
2. **Scaffolding Template Isolation:** Scaffolding file generators in `hexastack.application.scaffolding` must live in focused template renderer modules under `templates/{adapters, ci, config, domain, infra, openssf, ports, tests}/` rather than hardcoded string monoliths in the generator engine.
