import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest
from hexastack_core.domain.exceptions import MissingDependencyError
from hexastack_db.infra.config import HexastackDatabaseConfig
from hexastack_db.infra.migrations import (
    _env_py_template,
    get_alembic_config,
    init_migrations,
    run_current,
    run_history,
    stamp,
)

# Skip entire module if alembic is not installed
alembic_installed = importlib.util.find_spec("alembic") is not None
pytestmark = pytest.mark.skipif(not alembic_installed, reason="alembic not installed")


def _make_config(tmp_path: Path):
    """Build a minimal alembic config pointing at a real migrations dir."""
    migrations_dir = tmp_path / "migrations"
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"

    cfg = get_alembic_config(
        migrations_dir=migrations_dir,
        db_url=db_url,
    )
    return cfg, migrations_dir, db_url


def test_env_py_template_contains_url():
    tmpl = _env_py_template("sqlite:///demo.db")
    assert "sqlite:///demo.db" in tmpl
    assert "run_migrations_offline" in tmpl
    assert "run_migrations_online" in tmpl
    assert "DATABASE_URL" in tmpl


def test_get_alembic_config_sets_script_location(tmp_path: Path):
    cfg, migrations_dir, db_url = _make_config(tmp_path)
    assert cfg.get_main_option("script_location") == str(migrations_dir)
    assert cfg.get_main_option("sqlalchemy.url") == db_url


def test_init_migrations_creates_directory(tmp_path: Path):
    migrations_dir = tmp_path / "alembic_migrations"
    db_config = HexastackDatabaseConfig(url="sqlite:///hexastack.db")

    init_migrations(migrations_dir=migrations_dir, db_config=db_config)

    assert migrations_dir.exists()
    assert (migrations_dir / "env.py").exists()
    assert (migrations_dir / "versions").exists()
    env_content = (migrations_dir / "env.py").read_text()
    assert "sqlite:///hexastack.db" in env_content


def test_init_migrations_raises_if_dir_exists(tmp_path: Path):
    migrations_dir = tmp_path / "already_exists"
    migrations_dir.mkdir()
    with pytest.raises(FileExistsError):
        init_migrations(migrations_dir=migrations_dir)


def test_missing_alembic_raises_missing_dependency():
    """All migration helpers raise MissingDependencyError if alembic absent."""
    with (
        patch("importlib.util.find_spec", return_value=None),
        pytest.raises(MissingDependencyError),
    ):
        get_alembic_config("/tmp/migrations")


def test_full_migration_lifecycle(tmp_path: Path):
    """Init → stamp head → current → history (no revision files needed)."""
    migrations_dir = tmp_path / "migrations"
    db_path = tmp_path / "lifecycle.db"
    db_url = f"sqlite:///{db_path}"

    db_config = HexastackDatabaseConfig(url=db_url)
    init_migrations(migrations_dir=migrations_dir, db_config=db_config)

    cfg = get_alembic_config(migrations_dir=migrations_dir, db_url=db_url)

    # stamp and current should complete without error on a fresh DB
    stamp(cfg, "head")
    run_current(cfg)
    run_history(cfg)
