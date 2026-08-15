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

# ---------------------------------------------------------------------------
# Domain exception classes — one per status code branch
# ---------------------------------------------------------------------------


class UserNotFoundError(HexastackError):
    pass


class DuplicateEmailConflictError(HexastackError):
    pass


class UnauthorizedAccessError(HexastackError):
    pass


class ForbiddenActionError(HexastackError):
    pass


class PayloadValidationError(HexastackError):
    pass


class GenericDomainError(HexastackError):
    pass


class CustomMappedError(HexastackError):
    pass


def _build_app(*error_routes: tuple) -> tuple[FastAPI, TestClient]:
    """Build a FastAPI test app with all exception routes registered."""
    app = FastAPI()
    app.add_middleware(CorrelationHttpMiddleware)
    register_exception_handlers(app)
    for path, exc_cls, msg in error_routes:
        exc_cls_local = exc_cls
        msg_local = msg
        path_local = path

        @app.get(path_local)
        async def _route(
            _exc=exc_cls_local,
            _msg=msg_local,
        ):  # pragma: no cover
            raise _exc(_msg)

    return app, TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# All 5 domain → HTTP status code branches
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("exc_cls", "path", "message", "expected_status", "expected_type"),
    [
        (UserNotFoundError, "/nf", "User 42 not found", 404, "UserNotFoundError"),
        (
            DuplicateEmailConflictError,
            "/conflict",
            "Email taken",
            409,
            "DuplicateEmailConflictError",
        ),
        (
            UnauthorizedAccessError,
            "/unauth",
            "Token invalid",
            401,
            "UnauthorizedAccessError",
        ),
        (ForbiddenActionError, "/forbidden", "No access", 401, "ForbiddenActionError"),
        (PayloadValidationError, "/val", "Bad payload", 422, "PayloadValidationError"),
        (GenericDomainError, "/generic", "Something broke", 400, "GenericDomainError"),
    ],
    ids=[
        "not_found",
        "conflict",
        "unauthorized",
        "forbidden",
        "validation",
        "generic_400",
    ],
)
def test_exception_handler_all_branches(
    exc_cls, path, message, expected_status, expected_type
):
    """Kills all 20 mutants in exception_handlers.py — one per status code branch
    plus error_type and error message field assignments."""
    _, client = _build_app((path, exc_cls, message))
    res = client.get(path)

    assert res.status_code == expected_status
    body = res.json()
    assert body["error"] == message
    assert body["error_type"] == expected_type
    assert body["correlation_id"]  # dynamic — assert truthy


@pytest.mark.snapshot
def test_exception_handler_status_codes():
    """Snapshot the response bodies for 404 and 409 (excluding dynamic correlation_id)."""
    app = FastAPI()
    app.add_middleware(CorrelationHttpMiddleware)
    register_exception_handlers(app)

    @app.get("/not-found")
    async def raise_not_found():
        raise UserNotFoundError("User 123 does not exist")

    @app.get("/conflict")
    async def raise_conflict():
        raise DuplicateEmailConflictError("Email already in use")

    client = TestClient(app, raise_server_exceptions=False)

    res404 = client.get("/not-found")
    assert res404.status_code == 404
    body404 = res404.json()
    assert body404["correlation_id"]
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
    """Kills registry-branch mutants — custom status_code popped from mapped dict."""
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

    client = TestClient(app, raise_server_exceptions=False)
    res = client.get("/custom")
    assert res.status_code == 418
    assert res.json() == snapshot({"custom_reason": "I am a teapot"})
