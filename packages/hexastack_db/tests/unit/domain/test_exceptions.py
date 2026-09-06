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
    assert str(not_found) == "Entity 'DummyEntity' with id 'entity-123' was not found."

    uniq_err = UniqueConstraintViolationError("Duplicate email")
    assert isinstance(uniq_err, DatabaseError)
    assert str(uniq_err) == "Duplicate email"

    default_uniq_err = UniqueConstraintViolationError()
    assert str(default_uniq_err) == "Unique constraint violation occurred."
