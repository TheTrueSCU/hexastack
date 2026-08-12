from fastapi import FastAPI
from fastapi.testclient import TestClient
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

    # 1. 404 test
    res404 = client.get("/not-found")
    assert res404.status_code == 404
    data404 = res404.json()
    assert data404["error"] == "User 123 does not exist"
    assert data404["error_type"] == "UserNotFoundError"
    assert data404["correlation_id"] is not None

    # 2. 409 test
    res409 = client.get("/conflict")
    assert res409.status_code == 409
    data409 = res409.json()
    assert data409["error"] == "Email already in use"
    assert data409["error_type"] == "DuplicateEmailConflictError"


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
    assert res.json() == {"custom_reason": "I am a teapot"}
