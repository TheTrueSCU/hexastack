import inspect
from collections.abc import Callable
from functools import wraps
from typing import Any

from fastapi import HTTPException, Request, status

from hexastack_core.domain.exceptions import MissingDependencyError
from hexastack_core.ports.ratelimit import RateLimiterPort
from hexastack_core.utils.context import get_user_context


def get_remote_address(request: Request) -> str:
    """Extract client IP address from FastAPI request headers or client socket.

    Args:
        request: Incoming FastAPI Request object.

    Returns:
        Client IP string.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


def get_user_or_ip_key(request: Request) -> str:
    """Extract rate limit bucket key from ambient UserContext or fallback to client IP.

    Args:
        request: Incoming FastAPI Request object.

    Returns:
        Rate limit identifier string (e.g. 'user:usr_123', 'tenant:t_456', or 'ip:1.2.3.4').
    """
    user_ctx = get_user_context()
    if user_ctx and user_ctx.user_id:
        return f"user:{user_ctx.user_id}"
    if user_ctx and user_ctx.tenant_id:
        return f"tenant:{user_ctx.tenant_id}"
    return f"ip:{get_remote_address(request)}"


class SlowapiRateLimiterAdapter(RateLimiterPort):
    """RateLimiterPort implementation backed by slowapi and limits libraries.

    Notes/Architectural Intent:
        Wraps slowapi Limiter and limits storage backends (memory, redis),
        enforcing uniform rate limit verification across HTTP endpoints.
    """

    def __init__(
        self,
        key_func: Callable[[Request], str] | None = None,
        default_limits: list[str] | None = None,
        storage_uri: str = "memory://",
    ) -> None:
        """Initialize SlowapiRateLimiterAdapter.

        Args:
            key_func: Callable to extract bucket key from Request.
            default_limits: List of default rate limit strings (e.g. ['100/minute']).
            storage_uri: Storage URI ('memory://' or 'redis://localhost:6379').

        Raises:
            MissingDependencyError: If slowapi or limits is not installed.
        """
        try:
            from limits.storage import storage_from_string
            from slowapi import Limiter
        except ImportError as e:
            raise MissingDependencyError(
                "slowapi and limits are required for SlowapiRateLimiterAdapter. "
                "Install with 'pip install hexastack-fastapi[ratelimit]'."
            ) from e

        self._key_func = key_func or get_user_or_ip_key
        self._default_limits: list[Any] = list(default_limits or ["100/minute"])
        self._storage: Any = storage_from_string(storage_uri)
        self._limiter = Limiter(
            key_func=self._key_func,
            default_limits=self._default_limits,
            storage_uri=storage_uri,
        )

    @property
    def limiter(self) -> Any:
        """Underlying slowapi Limiter instance."""
        return self._limiter

    def hit(self, key: str, limit: str) -> bool:
        """Record a hit against the rate limit window using limits storage."""
        from limits import parse

        rate_item = parse(limit)
        storage: Any = self._storage
        count = int(storage.incr(rate_item.key_for(key), rate_item.get_expiry()))
        return count <= rate_item.amount

    def get_reset_window(self, key: str, limit: str) -> int:
        """Get remaining seconds until rate limit window resets."""
        from limits import parse

        rate_item = parse(limit)
        storage: Any = self._storage
        expiry = float(storage.get_expiry(rate_item.key_for(key)))
        return max(1, int(expiry)) if expiry > 0 else 0

    def clear(self, key: str | None = None) -> None:
        """Clear rate limit storage."""
        storage: Any = self._storage
        if hasattr(storage, "reset"):
            storage.reset()


def rate_limit(
    limit: str,
    key_func: Callable[[Request], str] | None = None,
    detail: str | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator guarding a FastAPI route endpoint with rate limiting.

    Notes/Architectural Intent:
        Enforces rate limits on endpoint execution. If quota is exceeded,
        raises an HTTPException with status 429 Too Many Requests and
        includes a 'Retry-After' header.

    Args:
        limit: Rate limit specification string (e.g. '5/minute', '10/second').
        key_func: Optional custom callable to extract bucket key from request.
        detail: Optional error detail message.

    Returns:
        Decorator wrapping the endpoint function.
    """
    key_extractor = key_func or get_user_or_ip_key

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        fn_name = getattr(fn, "__name__", "endpoint")

        if inspect.iscoroutinefunction(fn):

            @wraps(fn)
            async def async_wrapped(*args: Any, **kwargs: Any) -> Any:
                request = kwargs.get("request")
                if request is None:
                    for arg in args:
                        if isinstance(arg, Request):
                            request = arg
                            break

                if request is not None:
                    limiter_port: RateLimiterPort | None = getattr(
                        request.app.state, "rate_limiter", None
                    )
                    if limiter_port is not None:
                        base_key = key_extractor(request)
                        key = f"{base_key}:{fn_name}"
                        if not limiter_port.hit(key, limit):
                            reset_sec = limiter_port.get_reset_window(key, limit)
                            raise HTTPException(
                                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                                detail=detail or f"Rate limit exceeded: {limit}.",
                                headers={"Retry-After": str(reset_sec)},
                            )
                return await fn(*args, **kwargs)

            return async_wrapped

        @wraps(fn)
        def sync_wrapped(*args: Any, **kwargs: Any) -> Any:
            request = kwargs.get("request")
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if request is not None:
                limiter_port: RateLimiterPort | None = getattr(
                    request.app.state, "rate_limiter", None
                )
                if limiter_port is not None:
                    base_key = key_extractor(request)
                    key = f"{base_key}:{fn_name}"
                    if not limiter_port.hit(key, limit):
                        reset_sec = limiter_port.get_reset_window(key, limit)
                        raise HTTPException(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail=detail or f"Rate limit exceeded: {limit}.",
                            headers={"Retry-After": str(reset_sec)},
                        )
            return fn(*args, **kwargs)

        return sync_wrapped

    return decorator


__all__ = [
    "SlowapiRateLimiterAdapter",
    "get_remote_address",
    "get_user_or_ip_key",
    "rate_limit",
]
