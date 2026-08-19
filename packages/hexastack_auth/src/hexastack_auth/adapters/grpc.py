"""gRPC Server Interceptors and security helpers for hexastack-auth.

Notes/Architectural Intent:
    Extracts Bearer tokens or SPIFFE JWT-SVIDs from gRPC invocation metadata,
    validates them against SecurityPort or WorkloadIdentityPort, and establishes
    the ambient UserContext for the duration of the RPC.
"""

import importlib.util
from collections.abc import Callable
from typing import Any

from hexastack_auth.ports.security import SecurityPort
from hexastack_auth.ports.workload import WorkloadIdentityPort
from hexastack_core.domain.exceptions import MissingDependencyError
from hexastack_core.utils.context import UserContext, set_user_context

__all__ = [
    "AuthServerInterceptor",
]


def _require_grpc() -> None:
    if importlib.util.find_spec("grpc") is None:
        raise MissingDependencyError(
            "grpc is required for gRPC auth interceptor. "
            "Install with 'pip install hexastack-auth[grpc]'."
        )


class AuthServerInterceptor:
    """gRPC server interceptor extracting credentials from metadata into UserContext."""

    def __init__(
        self,
        security_port: SecurityPort | None = None,
        workload_port: WorkloadIdentityPort | None = None,
        *,
        auth_header: str = "authorization",
        spiffe_header: str = "x-spiffe-id",
        required: bool = False,
    ) -> None:
        _require_grpc()
        self._security_port = security_port
        self._workload_port = workload_port
        self._auth_header = auth_header.lower()
        self._spiffe_header = spiffe_header.lower()
        self._required = required

    def intercept_service(
        self,
        continuation: Callable[[Any], Any],
        handler_call_details: Any,
    ) -> Any:
        """Inspect invocation metadata and populate ambient UserContext."""
        import grpc

        metadata = dict(getattr(handler_call_details, "invocation_metadata", ()))
        token = metadata.get(self._auth_header)
        spiffe_id = metadata.get(self._spiffe_header)

        user_ctx: UserContext | None = None

        if token and self._security_port:
            raw_token = token.removeprefix("Bearer ").strip()
            try:
                identity = self._security_port.verify_token(raw_token)
                user_ctx = UserContext(
                    user_id=identity.user_id,
                    roles=list(identity.roles),
                    tenant_id=identity.tenant_id,
                )
            except Exception:
                if self._required:
                    return grpc.unary_unary_rpc_method_handler(
                        lambda _req, ctx: ctx.abort(
                            grpc.StatusCode.UNAUTHENTICATED,
                            "Invalid or expired security token",
                        )
                    )

        elif spiffe_id and self._workload_port:
            user_ctx = UserContext(
                user_id=spiffe_id,
                roles=["workload"],
                tenant_id=None,
            )

        elif self._required:
            return grpc.unary_unary_rpc_method_handler(
                lambda _req, ctx: ctx.abort(
                    grpc.StatusCode.UNAUTHENTICATED,
                    "Authentication credentials are required",
                )
            )

        if user_ctx is not None:
            set_user_context(user_ctx)

        return continuation(handler_call_details)
