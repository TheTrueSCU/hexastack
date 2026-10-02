import hexastack_db as db


def test_top_level_submodule_exports():
    assert db.adapters is not None
    assert db.domain is not None
    assert db.infra is not None
