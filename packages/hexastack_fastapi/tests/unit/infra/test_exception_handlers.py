import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from inline_snapshot import snapshot

from hexastack_core.domain import HexastackError
from hexastack_core.infra.registries.exception import ExceptionRegistry
from hexastack_fastapi.infra.exception_handlers import (
    register_exception_handlers,
)
from hexastack_fastapi.infra.middleware.correlation import (
    CorrelationHttpMiddleware,
)


class UserNotFoundError(HexastackError):
    pass


class DuplicateEmailConflictError(HexastackError):
    pass


class CustomMappedError(HexastackError):
    pass


@pytest.mark.snapshot
def test_exception_handler_status_codes():
    app = FastAPI()
    app.add_middleware(CorrelationHttpMiddleware)
    register_exception_handlers(app)

    @app.get("/not-found")
    async def raise_not_found():
        raise UserNotFoundError("User 123 does not exist")

    @app.get("/conflict")
    async def raise_conflict():
        raise DuplicateEmailConflictError("Email already in use")

    client = TestClient(app)

    res404 = client.get("/not-found")
    assert res404.status_code == 404
    body404 = res404.json()
    assert body404["correlation_id"]  # dynamic — just assert truthy
    assert {k: v for k, v in body404.items() if k != "correlation_id"} == snapshot(
        {"error": "User 123 does not exist", "error_type": "UserNotFoundError"}
    )

    res409 = client.get("/conflict")
    assert res409.status_code == 409
    body409 = res409.json()
    assert body409["correlation_id"]
    assert {k: v for k, v in body409.items() if k != "correlation_id"} == snapshot(
        {"error": "Email already in use", "error_type": "DuplicateEmailConflictError"}
    )


@pytest.mark.snapshot
def test_exception_handler_with_registry():
    app = FastAPI()
    app.add_middleware(CorrelationHttpMiddleware)
    registry = ExceptionRegistry()
    registry.register(
        CustomMappedError,
        lambda exc: {"status_code": 418, "custom_reason": "I am a teapot"},
    )
    register_exception_handlers(app, exception_registry=registry)

    @app.get("/custom")
    async def raise_custom():
        raise CustomMappedError("Custom error message")

    client = TestClient(app)
    res = client.get("/custom")
    assert res.status_code == 418
    assert res.json() == snapshot({"custom_reason": "I am a teapot"})
