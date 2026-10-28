from hexastack_db.domain.exceptions import (
    ColumnarQueryError,
    DatabaseConnectionError,
    DatabaseError,
    EntityNotFoundError,
    UniqueConstraintViolationError,
)


class DummyEntity:
    pass


def test_database_exceptions():
    base_err = DatabaseError("General database error")
    msg_base = str(base_err)
    assert msg_base == "General database error"

    conn_err = DatabaseConnectionError("Connection timed out")
    is_db = isinstance(conn_err, DatabaseError)
    assert is_db is True

    not_found = EntityNotFoundError(DummyEntity, "entity-123")
    assert not_found.entity_cls is DummyEntity
    assert not_found.entity_id == "entity-123"
    msg_nf = str(not_found)
    assert msg_nf == "Entity 'DummyEntity' with id 'entity-123' was not found."

    uniq_err = UniqueConstraintViolationError("Duplicate email")
    is_uniq = isinstance(uniq_err, DatabaseError)
    assert is_uniq is True
    msg_uniq = str(uniq_err)
    assert msg_uniq == "Duplicate email"

    default_uniq_err = UniqueConstraintViolationError()
    msg_def = str(default_uniq_err)
    assert msg_def == "Unique constraint violation occurred."

    col_err = ColumnarQueryError(
        "Arrow projection failed", query="SELECT * FROM metrics"
    )
    is_col = isinstance(col_err, DatabaseError)
    assert is_col is True
    assert col_err.query == "SELECT * FROM metrics"
    msg_col = str(col_err)
    assert msg_col == "Arrow projection failed [query=SELECT * FROM metrics]"

    col_err_no_q = ColumnarQueryError("Arrow failure")
    assert col_err_no_q.query is None
    msg_no_q = str(col_err_no_q)
    assert msg_no_q == "Arrow failure"
