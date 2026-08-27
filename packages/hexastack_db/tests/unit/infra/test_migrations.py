import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest

from hexastack_core.domain.exceptions import MissingDependencyError
from hexastack_db.infra.config import HexastackDatabaseConfig
from hexastack_db.infra.migrations import (
    _env_py_template,
    _require_alembic,
    get_alembic_config,
    init_migrations,
    run_current,
    run_downgrade,
    run_history,
    run_revision,
    run_upgrade,
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


def test_init_migrations_creates_directory_and_templates(tmp_path: Path):
    migrations_dir = tmp_path / "alembic_migrations"
    db_config = HexastackDatabaseConfig(url="sqlite:///custom_app.db")

    init_migrations(migrations_dir=migrations_dir, db_config=db_config)

    assert migrations_dir.exists()
    assert (migrations_dir / "env.py").exists()
    assert (migrations_dir / "versions").exists()
    assert (migrations_dir / "README").exists()
    assert (migrations_dir / "script.py.mako").exists()

    readme_content = (migrations_dir / "README").read_text()
    assert "Hexastack DB Migrations" in readme_content

    mako_content = (migrations_dir / "script.py.mako").read_text()
    assert "${message}" in mako_content
    assert "${up_revision}" in mako_content
    assert "def upgrade()" in mako_content
    assert "def downgrade()" in mako_content

    env_content = (migrations_dir / "env.py").read_text()
    assert "sqlite:///custom_app.db" in env_content

    # Directory already exists raises FileExistsError
    with pytest.raises(FileExistsError, match="already exists"):
        init_migrations(migrations_dir=migrations_dir, db_config=db_config)


def test_init_migrations_default_config(tmp_path: Path):
    migrations_dir = tmp_path / "default_migrations"
    init_migrations(migrations_dir=migrations_dir, db_config=None)
    env_content = (migrations_dir / "env.py").read_text()
    assert "sqlite:///hexastack.db" in env_content


def test_migration_commands_dispatch(tmp_path: Path):
    cfg, _, _ = _make_config(tmp_path)

    with patch("alembic.command.upgrade") as mock_upgrade:
        run_upgrade(cfg, revision="head")
        mock_upgrade.assert_called_once_with(cfg, "head")

    with patch("alembic.command.downgrade") as mock_downgrade:
        run_downgrade(cfg, revision="-1")
        mock_downgrade.assert_called_once_with(cfg, "-1")

    with patch("alembic.command.revision") as mock_revision:
        run_revision(cfg, message="initial_schema", autogenerate=True)
        mock_revision.assert_called_once_with(
            cfg, message="initial_schema", autogenerate=True
        )

    with patch("alembic.command.stamp") as mock_stamp:
        stamp(cfg, revision="head")
        mock_stamp.assert_called_once_with(cfg, "head")

    with patch("alembic.command.current") as mock_current:
        run_current(cfg)
        mock_current.assert_called_once_with(cfg)

    with patch("alembic.command.history") as mock_history:
        run_history(cfg)
        mock_history.assert_called_once_with(cfg)


def test_require_alembic_missing():
    with (
        patch("importlib.util.find_spec", return_value=None),
        pytest.raises(MissingDependencyError, match="alembic is required"),
    ):
        _require_alembic()


def test_run_check_and_missing_alembic(tmp_path: Path):
    """Verify run_check and missing alembic exception."""
    from hexastack_db.infra.migrations import run_check

    cfg, _, _ = _make_config(tmp_path)
    with patch("alembic.command.check") as mock_check:
        run_check(cfg)
        mock_check.assert_called_once_with(cfg)

    with (
        patch("importlib.util.find_spec", return_value=None),
        pytest.raises(MissingDependencyError, match="alembic is required"),
    ):
        _require_alembic()
