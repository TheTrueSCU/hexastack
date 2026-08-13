from hexastack_db.infra.bootstrap import DatabaseBootstrapper
from hexastack_db.infra.mixins import HexastackBase, UuidPrimaryKeyMixin
from hexastack_db.infra.registries.metadata import (
    get_registered_metadata,
    register_metadata,
)
from sqlalchemy import text
from sqlalchemy.orm import Mapped, mapped_column


class ProductRecord(UuidPrimaryKeyMixin, HexastackBase):
    __tablename__ = "test_products_registry"
    name: Mapped[str] = mapped_column()


def test_register_metadata_adds_to_registry():
    assert get_registered_metadata() == []
    register_metadata(HexastackBase.metadata)
    assert len(get_registered_metadata()) == 1
    assert HexastackBase.metadata in get_registered_metadata()


def test_register_metadata_deduplicates():
    register_metadata(HexastackBase.metadata)
    register_metadata(HexastackBase.metadata)
    assert len(get_registered_metadata()) == 1


def _bootstrap_with_url(url: str, auto_create_tables: bool, tmp_path):
    """Helper: write a TOML config and run bootstrap.

    Notes/Architectural Intent:
        ConfigRegistry reads package sections under the [hexastack] table,
        so [db] must be nested as [hexastack.db].
    """
    from hexastack_core.infra.bootstrap import bootstrap

    config_file = tmp_path / "hexastack.toml"
    config_file.write_text(
        f'[hexastack.db]\nurl = "{url}"\nauto_create_tables = {str(auto_create_tables).lower()}\n'
    )
    return bootstrap(
        config_path=str(config_file),
        bootstrappers=[DatabaseBootstrapper()],
        auto_discover=False,
    )


def test_auto_create_tables_creates_schema(tmp_path):
    """Bootstrap with auto_create_tables=True must actually create the table."""
    register_metadata(HexastackBase.metadata)

    db_path = tmp_path / "test.db"
    result = _bootstrap_with_url(
        f"sqlite:///{db_path}", auto_create_tables=True, tmp_path=tmp_path
    )

    engine = result.get("db_engine")
    assert engine is not None

    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        ).fetchall()
        table_names = [r[0] for r in rows]
        assert "test_products_registry" in table_names


def test_auto_create_tables_false_skips_creation(tmp_path):
    """Bootstrap with auto_create_tables=False must NOT create tables."""
    register_metadata(HexastackBase.metadata)

    result = _bootstrap_with_url(
        "sqlite:///:memory:", auto_create_tables=False, tmp_path=tmp_path
    )

    engine = result.get("db_engine")
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        ).fetchall()
        table_names = [r[0] for r in rows]
        assert "test_products_registry" not in table_names
