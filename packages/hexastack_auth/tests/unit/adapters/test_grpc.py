from unittest.mock import MagicMock

from hexastack_auth.adapters.grpc import AuthServerInterceptor
from hexastack_auth.domain.models import Identity
from hexastack_core.utils.context import correlation_scope, get_user_context


class MockHandlerCallDetails:
    def __init__(self, metadata):
        self.invocation_metadata = metadata


def test_grpc_auth_interceptor_spiffe():
    workload_mock = MagicMock()
    interceptor = AuthServerInterceptor(workload_port=workload_mock)

    continuation = MagicMock(return_value="ok")
    details = MockHandlerCallDetails((("x-spiffe-id", "spiffe://example.org/billing"),))

    with correlation_scope("test-grpc-spiffe"):
        res = interceptor.intercept_service(continuation, details)
        assert res == "ok"
        user_ctx = get_user_context()
        assert user_ctx is not None
        assert user_ctx.user_id == "spiffe://example.org/billing"


def test_grpc_auth_interceptor_valid_token():
    sec_mock = MagicMock()
    sec_mock.verify_token.return_value = Identity(
        user_id="alice",
        roles=frozenset({"admin"}),
        tenant_id="tenant-1",
    )

    interceptor = AuthServerInterceptor(security_port=sec_mock)

    continuation = MagicMock(return_value="continuation_result")
    details = MockHandlerCallDetails((("authorization", "Bearer valid.token.jwt"),))

    with correlation_scope("test-grpc"):
        res = interceptor.intercept_service(continuation, details)
        assert res == "continuation_result"
        user_ctx = get_user_context()
        assert user_ctx is not None
        assert user_ctx.user_id == "alice"
        assert "admin" in user_ctx.roles
