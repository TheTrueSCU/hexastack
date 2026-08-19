from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal

from hexastack_core.domain import Command, Query

_ROUTE_METADATA_ATTR = "__hexastack_route__"


@dataclass(frozen=True)
class RouteMetadata:
    """Metadata describing an HTTP endpoint binding for a Command or Query.

    Notes/Architectural Intent:
        Carries routing parameters attached by decorators for automated endpoint registration,
        including optional feature flag gating.
    """

    path: str
    kind: Literal["command", "query"]
    method: str = "POST"
    status_code: int = 200
    output_format: str | None = None
    summary: str | None = None
    tags: tuple[str | Enum, ...] | None = None
    feature_flag: str | None = None


__all__ = [
    "api_command",
    "api_query",
    "feature_flag_route",
    "RouteMetadata",
]


def api_command[TCommand: Command](
    path: str,
    *,
    method: str = "POST",
    status_code: int = 200,
    output_format: str | None = None,
    summary: str | None = None,
    tags: list[str | Enum] | None = None,
    feature_flag: str | None = None,
) -> Callable[[type[TCommand]], type[TCommand]]:
    """Decorator marking a Command class for automatic HTTP endpoint exposure.

    Args:
        path: URL path for the route.
        method: HTTP method (defaults to 'POST').
        status_code: Success HTTP status code (defaults to 200).
        output_format: Optional presenter output format.
        summary: Optional OpenAPI summary.
        tags: Optional OpenAPI tags list.
        feature_flag: Optional feature flag key required for route access.

    Returns:
        Decorated Command class with attached routing metadata.

    Raises:
        None.
    """

    def decorator(cls: type[TCommand]) -> type[TCommand]:
        meta = RouteMetadata(
            path=path,
            kind="command",
            method=method.upper(),
            status_code=status_code,
            output_format=output_format,
            summary=summary,
            tags=tuple(tags) if tags else None,
            feature_flag=feature_flag,
        )
        setattr(cls, _ROUTE_METADATA_ATTR, meta)
        return cls

    return decorator


def api_query[TQuery: Query](
    path: str,
    *,
    method: str = "GET",
    status_code: int = 200,
    output_format: str | None = None,
    summary: str | None = None,
    tags: list[str | Enum] | None = None,
    feature_flag: str | None = None,
) -> Callable[[type[TQuery]], type[TQuery]]:
    """Decorator marking a Query class for automatic HTTP endpoint exposure.

    Args:
        path: URL path for the route.
        method: HTTP method ('GET' or 'POST', defaults to 'GET').
        status_code: Success HTTP status code (defaults to 200).
        output_format: Optional presenter output format.
        summary: Optional OpenAPI summary.
        tags: Optional OpenAPI tags list.
        feature_flag: Optional feature flag key required for route access.

    Returns:
        Decorated Query class with attached routing metadata.

    Raises:
        None.
    """

    def decorator(cls: type[TQuery]) -> type[TQuery]:
        meta = RouteMetadata(
            path=path,
            kind="query",
            method=method.upper(),
            status_code=status_code,
            output_format=output_format,
            summary=summary,
            tags=tuple(tags) if tags else None,
            feature_flag=feature_flag,
        )
        setattr(cls, _ROUTE_METADATA_ATTR, meta)
        return cls

    return decorator


def feature_flag_route(
    flag_key: str,
    *,
    default: bool = False,
    status_code: int = 404,
    detail: str | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator guarding a custom FastAPI route function with dynamic feature flag evaluation.

    Notes/Architectural Intent:
        Wraps standard FastAPI endpoint callables with dynamic feature flag evaluation,
        returning an HTTP error (default 404) when the flag evaluates to False.

    Args:
        flag_key: Unique identifier of the feature flag to check.
        default: Fallback boolean value if flag is not explicitly configured.
        status_code: HTTP status code returned when disabled.
        detail: Optional error message string.

    Returns:
        Decorator wrapping the endpoint callable.
    """
    import inspect
    from functools import wraps

    from fastapi import HTTPException

    from hexastack_core.adapters.feature_flags.config import ConfigFeatureFlagAdapter
    from hexastack_core.domain.feature_flags import EvaluationContext
    from hexastack_core.ports.feature_flags import FeatureFlagPort
    from hexastack_fastapi.adapters.dependencies import get_feature_flags

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        if inspect.iscoroutinefunction(fn):

            @wraps(fn)
            async def async_wrapped(*args: Any, **kwargs: Any) -> Any:
                request = kwargs.get("request")
                flags: FeatureFlagPort = (
                    get_feature_flags(request)
                    if request is not None
                    else ConfigFeatureFlagAdapter()
                )
                eval_ctx = EvaluationContext.from_current_context()
                if not flags.is_enabled(flag_key, default=default, context=eval_ctx):
                    raise HTTPException(
                        status_code=status_code,
                        detail=detail or f"Feature '{flag_key}' is disabled.",
                    )
                return await fn(*args, **kwargs)

            return async_wrapped

        @wraps(fn)
        def sync_wrapped(*args: Any, **kwargs: Any) -> Any:
            request = kwargs.get("request")
            flags: FeatureFlagPort = (
                get_feature_flags(request)
                if request is not None
                else ConfigFeatureFlagAdapter()
            )
            eval_ctx = EvaluationContext.from_current_context()
            if not flags.is_enabled(flag_key, default=default, context=eval_ctx):
                raise HTTPException(
                    status_code=status_code,
                    detail=detail or f"Feature '{flag_key}' is disabled.",
                )
            return fn(*args, **kwargs)

        return sync_wrapped

    return decorator
