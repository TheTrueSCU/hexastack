"""Alembic migration support for hexastack-db.

Provides programmatic migration management, auto-generated env.py factories,
and integration with the hexastack bootstrap context.

Requires: pip install hexastack-db[migrations]
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING

from hexastack_core.domain.exceptions import MissingDependencyError
from hexastack_db.infra.config import HexastackDatabaseConfig

if TYPE_CHECKING:
    from alembic.config import Config as AlembicConfig


__all__ = [
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


def _env_py_template(default_url: str) -> str:
    """Return the content of a hexastack-aware alembic env.py.

    Args:
        default_url: Default SQLAlchemy URL to embed.

    Returns:
        String content for env.py.
    """
    return f'''\
"""Hexastack-generated Alembic env.py.

Edit target_metadata to include your application\'s DeclarativeBase.metadata.
"""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ---------------------------------------------------------------------------
# User configuration: import your HexastackBase (or DeclarativeBase) here
# and assign its metadata to target_metadata so autogenerate can detect changes.
#
# Example:
#   from myapp.models import HexastackBase
#   target_metadata = HexastackBase.metadata
# ---------------------------------------------------------------------------
target_metadata = None

config = context.config

# Allow DATABASE_URL env var to override alembic.ini / hexastack config
db_url = os.environ.get("DATABASE_URL", "{default_url}")
config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def run_migrations_offline() -> None:
    """Run migrations in \'offline\' mode (SQL script output)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={{"paramstyle": "named"}},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in \'online\' mode (direct database connection)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {{}}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''


def _require_alembic() -> None:
    """Guard against missing alembic installation.

    Raises:
        MissingDependencyError: If alembic is not installed.
    """
    if importlib.util.find_spec("alembic") is None:
        raise MissingDependencyError(
            "alembic is required for migration support. "
            "Install via 'pip install hexastack-db[migrations]'."
        )


def get_alembic_config(
    migrations_dir: str | Path,
    db_url: str | None = None,
    alembic_ini: str | Path | None = None,
) -> AlembicConfig:
    """Build an Alembic Config object pointed at a migrations directory.

    Notes/Architectural Intent:
        Provides programmatic configuration so users never need to parse
        alembic.ini manually; the script_location and sqlalchemy.url are
        injected at runtime from hexastack config.

    Args:
        migrations_dir: Absolute or relative path to the alembic migrations folder.
        db_url: SQLAlchemy connection URL; overrides alembic.ini if supplied.
        alembic_ini: Path to an existing alembic.ini (optional).

    Returns:
        Configured alembic Config instance.

    Raises:
        MissingDependencyError: If alembic package is not installed.
    """
    _require_alembic()
    from alembic.config import Config

    cfg = Config(str(alembic_ini) if alembic_ini else None)
    cfg.set_main_option("script_location", str(migrations_dir))
    if db_url:
        cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def init_migrations(
    migrations_dir: str | Path,
    db_config: HexastackDatabaseConfig | None = None,
) -> None:
    """Initialise a new alembic migrations directory with a hexastack-ready env.py.

    Notes/Architectural Intent:
        Creates the migrations directory structure and writes an env.py that
        reads the db URL from the hexastack config chain, avoiding the need
        to hard-code connection strings in the migrations folder.

    Args:
        migrations_dir: Path to create the migrations directory at.
        db_config: Optional HexastackDatabaseConfig for embedding defaults.

    Raises:
        MissingDependencyError: If alembic is not installed.
        FileExistsError: If migrations_dir already exists.
    """
    _require_alembic()

    migrations_dir = Path(migrations_dir)
    if migrations_dir.exists():
        raise FileExistsError(f"Migrations directory already exists: {migrations_dir}")

    # Build directory structure manually — we own env.py entirely,
    # so we don't need alembic's command.init (which in >=1.19 requires
    # a config_file_name to emit alembic.ini).
    migrations_dir.mkdir(parents=True)
    (migrations_dir / "versions").mkdir()
    (migrations_dir / "README").write_text(
        "Hexastack DB Migrations — managed by hexastack-db[migrations]\n"
    )
    (migrations_dir / "script.py.mako").write_text(
        '"""${message}\n\nRevision ID: ${up_revision}\nRevises: ${down_revision | comma,n}\n'
        'Create Date: ${create_date}\n\n"""\n\nfrom typing import Sequence, Union\n\n'
        'from alembic import op\nimport sqlalchemy as sa\n${imports if imports else ""}\n\n'
        "revision: str = ${repr(up_revision)}\ndown_revision: Union[str, Sequence[str], None] = ${repr(down_revision)}\n"
        "branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}\n"
        "depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}\n\n\n"
        "def upgrade() -> None:\n    ${upgrades if upgrades else 'pass'}\n\n\n"
        "def downgrade() -> None:\n    ${downgrades if downgrades else 'pass'}\n"
    )

    # Overwrite env.py with hexastack-aware version
    url = db_config.url if db_config else "sqlite:///hexastack.db"
    (migrations_dir / "env.py").write_text(_env_py_template(url))


def run_check(config: AlembicConfig) -> None:
    """Check if there are any ungenerated schema revisions or unapplied migrations.

    Notes/Architectural Intent:
        Executes alembic's check command to guarantee that DeclarativeBase metadata
        matches the migration history, raising an error if drift is detected.

    Args:
        config: Configured AlembicConfig instance.

    Raises:
        MissingDependencyError: If alembic is not installed.
    """
    _require_alembic()
    from alembic import command

    command.check(config)


def run_current(config: AlembicConfig) -> None:
    """Print the current alembic revision applied to the database.

    Args:
        config: Configured AlembicConfig instance.

    Raises:
        MissingDependencyError: If alembic is not installed.
    """
    _require_alembic()
    from alembic import command

    command.current(config)


def run_downgrade(
    config: AlembicConfig,
    revision: str = "-1",
) -> None:
    """Run alembic downgrade to the target revision.

    Args:
        config: Configured AlembicConfig instance.
        revision: Target revision identifier (default: '-1', one step back).

    Raises:
        MissingDependencyError: If alembic is not installed.
    """
    _require_alembic()
    from alembic import command

    command.downgrade(config, revision)


def run_history(config: AlembicConfig) -> None:
    """Print the alembic migration history.

    Args:
        config: Configured AlembicConfig instance.

    Raises:
        MissingDependencyError: If alembic is not installed.
    """
    _require_alembic()
    from alembic import command

    command.history(config)


def run_revision(
    config: AlembicConfig,
    message: str,
    autogenerate: bool = True,
) -> None:
    """Generate a new alembic migration revision.

    Args:
        config: Configured AlembicConfig instance.
        message: Short description for the revision.
        autogenerate: If True, autogenerate diff from SQLAlchemy metadata.

    Raises:
        MissingDependencyError: If alembic is not installed.
    """
    _require_alembic()
    from alembic import command

    command.revision(config, message=message, autogenerate=autogenerate)


def run_upgrade(
    config: AlembicConfig,
    revision: str = "head",
) -> None:
    """Run alembic upgrade to the target revision.

    Args:
        config: Configured AlembicConfig instance.
        revision: Target revision identifier (default: 'head').

    Raises:
        MissingDependencyError: If alembic is not installed.
    """
    _require_alembic()
    from alembic import command

    command.upgrade(config, revision)


def stamp(config: AlembicConfig, revision: str = "head") -> None:
    """Stamp the database at the given revision without running migrations.

    Notes/Architectural Intent:
        Used when an existing database is adopted into alembic management
        for the first time without replaying all historical revisions.

    Args:
        config: Configured AlembicConfig instance.
        revision: Revision to stamp (default: 'head').

    Raises:
        MissingDependencyError: If alembic is not installed.
    """
    _require_alembic()
    from alembic import command

    command.stamp(config, revision)
