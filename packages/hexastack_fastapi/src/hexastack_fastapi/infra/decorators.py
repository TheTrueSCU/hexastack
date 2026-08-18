from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Literal

from hexastack_core.domain import Command, Query

_ROUTE_METADATA_ATTR = "__hexastack_route__"


@dataclass(frozen=True)
class RouteMetadata:
    """Metadata describing an HTTP endpoint binding for a Command or Query.

    Notes/Architectural Intent:
        Carries routing parameters attached by decorators for automated endpoint registration.
    """

    path: str
    kind: Literal["command", "query"]
    method: str = "POST"
    status_code: int = 200
    output_format: str | None = None
    summary: str | None = None
    tags: tuple[str | Enum, ...] | None = None


__all__ = [
    "RouteMetadata",
    "api_command",
    "api_query",
]


def api_command[TCommand: Command](
    path: str,
    *,
    method: str = "POST",
    status_code: int = 200,
    output_format: str | None = None,
    summary: str | None = None,
    tags: list[str | Enum] | None = None,
) -> Callable[[type[TCommand]], type[TCommand]]:
    """Decorator marking a Command class for automatic HTTP endpoint exposure.

    Args:
        path: URL path for the route.
        method: HTTP method (defaults to 'POST').
        status_code: Success HTTP status code (defaults to 200).
        output_format: Optional presenter output format.
        summary: Optional OpenAPI summary.
        tags: Optional OpenAPI tags list.

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
) -> Callable[[type[TQuery]], type[TQuery]]:
    """Decorator marking a Query class for automatic HTTP endpoint exposure.

    Args:
        path: URL path for the route.
        method: HTTP method ('GET' or 'POST', defaults to 'GET').
        status_code: Success HTTP status code (defaults to 200).
        output_format: Optional presenter output format.
        summary: Optional OpenAPI summary.
        tags: Optional OpenAPI tags list.

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
        )
        setattr(cls, _ROUTE_METADATA_ATTR, meta)
        return cls

    return decorator
