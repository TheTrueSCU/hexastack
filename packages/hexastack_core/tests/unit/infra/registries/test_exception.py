from typing import Any

import pytest
from hexastack_core.infra.registries.exception import (
    ExceptionRegistry,
    ExceptionRegistryError,
)


class CustomTestError(Exception):
    pass


def test_exception_registry_mapping():
    registry = ExceptionRegistry()

    def handle_custom(exc: CustomTestError) -> dict[str, Any]:
        return {"error": "custom", "message": str(exc)}

    registry.register(CustomTestError, handle_custom)

    res = registry.handle(CustomTestError("failed"))
    assert res == {"error": "custom", "message": "failed"}


def test_exception_registry_unregistered_raises():
    registry = ExceptionRegistry()

    with pytest.raises(ExceptionRegistryError):
        registry.handle(KeyError("missing_key"), reraise=True)
