from starlette.types import ASGIApp, Message, Receive, Scope, Send

from hexastack_core.utils.context import (
    UserContext,
    correlation_id_ctx,
    new_correlation_id,
    set_correlation_id,
    set_user_context,
    user_ctx,
)
from hexastack_fastapi.infra.config import HexastackFastApiConfig


class CorrelationHttpMiddleware:
    """ASGI middleware managing correlation and user identity context from HTTP headers.

    Notes/Architectural Intent:
        Extracts or generates correlation IDs and tenant/user identities from incoming
        request headers, sets them in ContextVars for CQRS/logging consumption, and
        attaches the correlation ID to outgoing HTTP response headers.
    """

    def __init__(
        self,
        app: ASGIApp,
        config: HexastackFastApiConfig | None = None,
    ) -> None:
        """Initialize middleware with target ASGI application and configuration.

        Args:
            app: The downstream ASGI application callable.
            config: Optional HexastackFastApiConfig controlling header names.
        """
        self._app = app
        cfg = config or HexastackFastApiConfig()
        self._correlation_header = cfg.correlation_header.lower().encode("latin1")
        self._correlation_header_name = cfg.correlation_header
        self._user_header = cfg.user_header.lower().encode("latin1")
        self._tenant_header = cfg.tenant_header.lower().encode("latin1")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process incoming ASGI request, inject context tokens, and wrap response.

        Args:
            scope: ASGI connection scope dictionary.
            receive: ASGI receive callable.
            send: ASGI send callable.

        Returns:
            None.

        Raises:
            Exception: Propagates unhandled exceptions to upstream exception handlers.
        """
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        headers: list[tuple[bytes, bytes]] = scope.get("headers", [])
        header_map: dict[bytes, bytes] = dict(headers)

        # 1. Extract or generate Correlation ID
        raw_cid = header_map.get(self._correlation_header)
        correlation_id = raw_cid.decode("latin1") if raw_cid else new_correlation_id()
        corr_token = set_correlation_id(correlation_id)

        # 2. Extract User / Tenant context
        raw_uid = header_map.get(self._user_header)
        raw_tid = header_map.get(self._tenant_header)
        user_token = None
        if raw_uid or raw_tid:
            user_context = UserContext(
                user_id=raw_uid.decode("latin1") if raw_uid else "anonymous",
                tenant_id=raw_tid.decode("latin1") if raw_tid else None,
            )
            user_token = set_user_context(user_context)

        # 3. Intercept response to inject correlation header
        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                resp_headers: list[tuple[bytes, bytes]] = list(
                    message.get("headers", [])
                )
                resp_headers.append(
                    (self._correlation_header, correlation_id.encode("latin1"))
                )
                message["headers"] = resp_headers
            await send(message)

        try:
            await self._app(scope, receive, send_wrapper)
        finally:
            correlation_id_ctx.reset(corr_token)
            if user_token is not None:
                user_ctx.reset(user_token)


__all__ = [
    "CorrelationHttpMiddleware",
]
