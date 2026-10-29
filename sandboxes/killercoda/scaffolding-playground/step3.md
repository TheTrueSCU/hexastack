## Step 3: Validating Quality Gates & Test Symmetry

Hexastack projects include the `hexaqual` governance toolsuite to ensure zero architectural drift.

Run the scoped sanity quality gate:

```bash
uv run hexaqual sanity
```{{exec}}

This single command audits:
- **Ruff**: Code formatting and linting.
- **Ty**: Static type checking.
- **Cognitive Complexity**: Ensures all functions maintain a complexity score $\le 25$.
- **`__all__` Integrity**: Verifies casefold alphabetical sorting.
- **Test Parity**: Enforces 1:1 symmetry between `src/` modules and `tests/unit/`.
- **Pytest**: Executes hermetic unit tests.

Everything passes out of the box!
