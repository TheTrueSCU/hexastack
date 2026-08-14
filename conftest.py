"""Root conftest.py for the Hexastack monorepo test suite.

Notes/Architectural Intent:
    Provides monorepo-wide pytest configuration shared across all 14 packages.

    inline-snapshot + xdist interaction:
        Normal CI runs use pytest-xdist (parallel workers) for speed. When xdist
        is active, inline-snapshot operates in read-only mode — existing snapshots
        pass/fail as expected but are not written back to source. This is correct
        CI behaviour.

        To create or update snapshots, use the dedicated script which disables
        xdist for a single-process run:

            uv run python scripts/update_snapshots.py --package <name> --mode fix
            uv run python scripts/update_snapshots.py --package <name> --mode create
            uv run python scripts/update_snapshots.py --package <name> --mode review
"""

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register custom monorepo-wide pytest markers.

    Args:
        config: The active pytest configuration object.

    Notes/Architectural Intent:
        Markers are registered here rather than per-package to avoid
        PytestUnknownMarkWarning across the workspace.
    """
    config.addinivalue_line(
        "markers",
        "snapshot: mark a test as containing inline-snapshot assertions. "
        "Run with 'uv run python scripts/update_snapshots.py' to create or fix.",
    )
    config.addinivalue_line(
        "markers",
        "integration: mark a test as requiring external infrastructure "
        "(database, message broker, etc.).",
    )
    config.addinivalue_line(
        "markers",
        "slow: mark a test as slow-running (excluded from fast local runs).",
    )
