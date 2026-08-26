from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest

from hexastack_core.domain.exceptions import HexastackError
from hexastack_grpc.infra.interceptors.exception import (
    AsyncExceptionServerInterceptor,
    ExceptionServerInterceptor,
    _map_exception_to_status_code,
)


class CustomNotFoundError(Exception):
    pass


class CustomValidationError(Exception):
    pass


class CustomUnauthorizedError(Exception):
    pass


class CustomForbiddenError(Exception):
    pass


class CustomConflictError(Exception):
    pass


class CustomHexastackError(HexastackError):
    pass


def test_grpc_exception_interceptors_instantiation() -> None:
    sync_interceptor = ExceptionServerInterceptor()
    async_interceptor = AsyncExceptionServerInterceptor()
    assert sync_interceptor is not None
    assert async_interceptor is not None


def test_map_exception_to_status_code_branches() -> None:
    code, _ = _map_exception_to_status_code(CustomNotFoundError("not found"))
    assert code == grpc.StatusCode.NOT_FOUND

    code, msg = _map_exception_to_status_code(CustomValidationError("invalid"))
    assert code == grpc.StatusCode.INVALID_ARGUMENT
    assert msg == "invalid"

    code, _ = _map_exception_to_status_code(CustomUnauthorizedError("unauth"))
    assert code == grpc.StatusCode.UNAUTHENTICATED

    code, _ = _map_exception_to_status_code(CustomForbiddenError("forbidden"))
    assert code == grpc.StatusCode.PERMISSION_DENIED

    code, _ = _map_exception_to_status_code(CustomConflictError("conflict"))
    assert code == grpc.StatusCode.ALREADY_EXISTS

    class CustomPermissionError(Exception):
        pass

    class CustomAlreadyExistsError(Exception):
        pass

    class CustomAuthenticationError(Exception):
        pass

    code_perm, _ = _map_exception_to_status_code(CustomPermissionError("no perm"))
    assert code_perm == grpc.StatusCode.PERMISSION_DENIED

    code_exists, _ = _map_exception_to_status_code(CustomAlreadyExistsError("exists"))
    assert code_exists == grpc.StatusCode.ALREADY_EXISTS

    code_auth, _ = _map_exception_to_status_code(
        CustomAuthenticationError("unauth user")
    )
    assert code_auth == grpc.StatusCode.UNAUTHENTICATED

    code, _ = _map_exception_to_status_code(CustomHexastackError("internal"))
    assert code == grpc.StatusCode.INTERNAL

    code, _ = _map_exception_to_status_code(RuntimeError("generic"))
    assert code == grpc.StatusCode.UNKNOWN


def test_sync_exception_interceptor_aborts() -> None:
    interceptor = ExceptionServerInterceptor()
    ctx = MagicMock()

    def handler(req, context):
        raise CustomNotFoundError("Resource missing")

    interceptor._handle_unary("req", ctx, handler, MagicMock())
    ctx.abort.assert_called_once_with(grpc.StatusCode.NOT_FOUND, "Resource missing")


@pytest.mark.anyio
async def test_async_exception_interceptor_aborts() -> None:
    interceptor = AsyncExceptionServerInterceptor()
    ctx = AsyncMock()

    async def async_handler(req, context):
        raise CustomValidationError("Bad input")

    await interceptor._handle_unary_async("req", ctx, async_handler, MagicMock())
    ctx.abort.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT, "Bad input")
