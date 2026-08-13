# Development Standards & CI/CD Pipeline

This document defines the standard for professional, type-safe, and robust Python project maintenance.

## 1. Robust Testing Strategy (Tiered)

To balance development speed with code reliability, we employ a tiered testing approach.

### Unit & Integration Tests (Fast Lane)
*   **Location:** `tests/unit/`, `tests/integration/`
*   **Responsibility:** Validate core business logic and "golden path" scenarios.
*   **Execution:** Run on every commit via local development and the `check` job in CI.

### Property-Based Fuzzing (Robustness Lane)
*   **Location:** `tests/properties/`
*   **Dependency:** `hypothesis`
*   **Responsibility:** Discover edge-case failures through stress-testing complex structures.
*   **Execution:** Runs only during the Pull Request process (`hypothesis` job in CI) to maintain CI speed for main.

---

## 2. CI/CD Pipeline Configuration (.github/workflows/ci.yml)

The CI pipeline enforces quality through a multi-stage dependency chain.

```yaml
jobs:
  check:
    # Runs static analysis, formatting, and unit/integration tests.
    # Must pass before any other jobs trigger.

  hypothesis:
    # Runs property-based tests.
    needs: check
    if: github.event_name == 'pull_request'
    # Executes only during PR review to save CI resources.
```

---

## 3. Pre-Commit Enforcement (.pre-commit-config.yaml)

We use pre-commit to ensure code quality **before** it hits the repository.

*   **Standard Hooks:** Trailing whitespace, end-of-file fixes, YAML validation, large file checks.
*   **Linting & Formatting:** `ruff` (with `--fix`) and `ruff-format`.
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

## 6. Automated Release Protocol
To automate versioning and changelog generation using python-semantic-release (Bot Proposes, Human Approves pattern):
1. **Conventional Commits:** All commits must follow Conventional Commits.
2. **Repository Permissions:** In GitHub Settings > Actions > General > Workflow permissions, select "Read and write permissions" and check "Allow GitHub Actions to create and approve pull requests."
3. **Automate:** Add the workflow to `.github/workflows/release.yml`.
