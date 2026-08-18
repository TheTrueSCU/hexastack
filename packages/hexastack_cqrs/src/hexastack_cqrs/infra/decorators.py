from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from hexastack_core.domain import Command, Event, Generic, Query
from hexastack_core.infra.decorators import (
    ConfigMetadata,
    ExceptionMetadata,
    config_section,
    exception_handler,
)

_HANDLER_META_ATTR = "__hexastack_handler__"


@dataclass(frozen=True)
class HandlerMetadata:
    """Metadata tag attached to handler functions for autodiscovery.

    Notes/Architectural Intent:
        Encapsulates metadata defining handler lifecycle type and target class
        without invoking or referencing global registry singletons.
    """

    kind: Literal["command", "query", "event"]
    target_cls: type[Any]


@dataclass(frozen=True)
class PresenterMetadata:
    """Metadata tag attached to presenter classes or callables for autodiscovery.

    Notes/Architectural Intent:
        Associates target Generic domain models and output format identifiers
        with Presenter implementations without global registry singletons.
    """

    target_cls: type[Generic]
    output_format: str


__all__ = [
    "ConfigMetadata",
    "ExceptionMetadata",
    "HandlerMetadata",
    "PresenterMetadata",
    "command_handler",
    "config_section",
    "event_listener",
    "exception_handler",
    "presenter",
    "query_handler",
]


def _tag_object(obj: Any, metadata: Any) -> None:
    """Attach metadata tag to target object."""
    setattr(obj, _HANDLER_META_ATTR, metadata)


def command_handler(
    target_cls: type[Command],
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Mark a callable as a handler for a target Command class.

    Args:
        target_cls: The Command class type handled by the decorated function.

    Returns:
        Decorator function attaching HandlerMetadata.

    Raises:
        None.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        _tag_object(fn, HandlerMetadata(kind="command", target_cls=target_cls))
        return fn

    return decorator


def event_listener(
    target_cls: type[Event],
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Mark a callable as a subscriber for a target Event class.

    Args:
        target_cls: The Event class type subscribed by the decorated function.

    Returns:
        Decorator function attaching HandlerMetadata.

    Raises:
        None.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        _tag_object(fn, HandlerMetadata(kind="event", target_cls=target_cls))
        return fn

    return decorator


def presenter(
    target_cls: type[Generic],
    output_format: str,
) -> Callable[[Any], Any]:
    """Mark a class or callable as a presenter for target_cls in output_format.

    Args:
        target_cls: The Generic domain object class type to be presented.
        output_format: Target format string (e.g. 'json', 'html', 'csv').

    Returns:
        Decorator function attaching PresenterMetadata.

    Raises:
        None.
    """

    def decorator(obj: Any) -> Any:
        _tag_object(
            obj,
            PresenterMetadata(target_cls=target_cls, output_format=output_format),
        )
        return obj

    return decorator


def query_handler(
    target_cls: type[Query[Any]],
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Mark a callable as a handler for a target Query class.

    Args:
        target_cls: The Query class type handled by the decorated function.

    Returns:
        Decorator function attaching HandlerMetadata.

    Raises:
        None.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        _tag_object(fn, HandlerMetadata(kind="query", target_cls=target_cls))
        return fn

    return decorator
