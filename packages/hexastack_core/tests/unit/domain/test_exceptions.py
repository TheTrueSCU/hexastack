from hexastack_core.domain.exceptions import (
    DependencyResolutionError,
    HexastackError,
    HexastackRegistryError,
    MissingDependencyError,
    UnitOfWorkError,
)


def test_exception_hierarchy():
    base_err = HexastackError("base error")
    assert isinstance(base_err, Exception)

    registry_err = HexastackRegistryError("registry error")
    assert isinstance(registry_err, HexastackError)

    uow_err = UnitOfWorkError("uow error")
    assert isinstance(uow_err, HexastackError)

    dep_err = DependencyResolutionError("missing dependency")
    assert isinstance(dep_err, HexastackError)

    missing_err = MissingDependencyError("missing optional package")
    assert isinstance(missing_err, HexastackError)
    assert isinstance(missing_err, ImportError)
