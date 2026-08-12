from hexastack_core.domain.exceptions import (
    HexastackError,
    HexastackRegistryError,
    UnitOfWorkError,
)


def test_exception_hierarchy():
    base_err = HexastackError("base error")
    assert isinstance(base_err, Exception)

    registry_err = HexastackRegistryError("registry error")
    assert isinstance(registry_err, HexastackError)

    uow_err = UnitOfWorkError("uow error")
    assert isinstance(uow_err, HexastackError)
