from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

_HANDLER_META_ATTR = "__hexastack_handler__"


@dataclass(frozen=True)
class ConfigMetadata:
    """Metadata tag attached to configuration classes for autodiscovery.

    Notes/Architectural Intent:
        Associates configuration section names with Pydantic model schemas without global state.
    """

    section_name: str


@dataclass(frozen=True)
class ExceptionMetadata:
    """Metadata tag attached to exception handlers for autodiscovery.

    Notes/Architectural Intent:
        Associates target exception classes with handler callables without global state.
    """

    target_cls: type[BaseException]


def _tag_object(obj: Any, metadata: Any) -> None:
    """Attach metadata tag to target object."""
    setattr(obj, _HANDLER_META_ATTR, metadata)


def config_section[T: BaseModel](
    section_name: str,
) -> Callable[[type[T]], type[T]]:
    """Mark a Pydantic BaseModel as a configuration section schema.

    Args:
        section_name: The TOML section name identifier (e.g. 'cqrs.middleware.retry').

    Returns:
        Decorator function attaching ConfigMetadata.

    Raises:
        None.
    """

    def decorator(cls: type[BaseModel]) -> type[BaseModel]:
        _tag_object(cls, ConfigMetadata(section_name=section_name))
        return cls

    return decorator


def exception_handler(
    target_cls: type[BaseException],
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Mark a callable as an exception handler for a target exception class.

    Args:
        target_cls: The Exception class type handled by the decorated function.

    Returns:
        Decorator function attaching ExceptionMetadata.

    Raises:
        None.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        _tag_object(fn, ExceptionMetadata(target_cls=target_cls))
        return fn

    return decorator
