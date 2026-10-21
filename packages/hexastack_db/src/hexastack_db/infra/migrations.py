"""Backward compatibility shim for migrations relocated to hexastack_db.utils.migrations.

Notes/Architectural Intent:
    Database migration helpers (Alembic configuration, run_upgrade, run_downgrade, etc.)
    are developer tooling utilities with no dependency on DI runtime bootstrap.
    Relocated to hexastack_db.utils.migrations. This module re-exports them to preserve
    backward compatibility.
"""

from hexastack_db.utils.migrations import (
    _env_py_template,
    _require_alembic,
    get_alembic_config,
    init_migrations,
    run_check,
    run_current,
    run_downgrade,
    run_history,
    run_revision,
    run_upgrade,
    stamp,
)

__all__ = [
    "_env_py_template",
    "_require_alembic",
    "get_alembic_config",
    "init_migrations",
    "run_check",
    "run_current",
    "run_downgrade",
    "run_history",
    "run_revision",
    "run_upgrade",
    "stamp",
]
