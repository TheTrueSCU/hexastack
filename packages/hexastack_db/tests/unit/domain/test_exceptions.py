from hexastack_db.domain.exceptions import (
    DatabaseConnectionError,
    DatabaseError,
    EntityNotFoundError,
    UniqueConstraintViolationError,
)


class DummyEntity:
    pass


def test_database_exceptions():
    base_err = DatabaseError("General database error")
    assert str(base_err) == "General database error"

    conn_err = DatabaseConnectionError("Connection timed out")
    assert isinstance(conn_err, DatabaseError)

    not_found = EntityNotFoundError(DummyEntity, "entity-123")
    assert not_found.entity_cls is DummyEntity
    assert not_found.entity_id == "entity-123"
    assert "DummyEntity" in str(not_found)
    assert "entity-123" in str(not_found)

    uniq_err = UniqueConstraintViolationError("Duplicate email")
    assert isinstance(uniq_err, DatabaseError)
    assert "Duplicate email" in str(uniq_err)
