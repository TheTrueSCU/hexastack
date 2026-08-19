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


@dataclass(frozen=True)
class FeatureFlagMetadata:
    """Metadata tag attached to handlers or pipeline targets for feature flag gating.

    Notes/Architectural Intent:
        Associates feature flag identifier, fallback handler callable, and default
        boolean value for conditional execution without modifying the underlying handler.
    """

    flag_key: str
    fallback: Callable[..., Any] | None = None
    default: bool = False


__all__ = [
    "command_handler",
    "config_section",
    "ConfigMetadata",
    "event_listener",
    "exception_handler",
    "ExceptionMetadata",
    "feature_flag",
    "FeatureFlagMetadata",
    "HandlerMetadata",
    "presenter",
    "PresenterMetadata",
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


def feature_flag(
    flag_key: str,
    *,
    fallback: Callable[..., Any] | None = None,
    default: bool = False,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Wrap a handler or function with dynamic feature flag evaluation.

    Notes/Architectural Intent:
        Evaluates the specified feature flag via ambient UserContext / FeatureFlagPort.
        If enabled, executes the target function; if disabled, executes fallback (if supplied)
        or raises FeatureFlagDisabledError.

    Args:
        flag_key: Unique identifier of the feature flag to check.
        fallback: Optional callable to invoke if the flag is disabled.
        default: Fallback boolean value if flag is not explicitly configured.

    Returns:
        Decorator function wrapping target callable.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        from hexastack_core.domain.feature_flags import EvaluationContext
        from hexastack_core.ports.feature_flags import FeatureFlagPort
        from hexastack_cqrs.infra.middleware.feature_flag import (
            FeatureFlagDisabledError,
        )

        def wrapped(*args: Any, **kwargs: Any) -> Any:
            eval_ctx = EvaluationContext.from_current_context()
            flags: FeatureFlagPort | None = kwargs.pop("__feature_flags__", None)
            if flags is None:
                from hexastack_core.adapters.feature_flags.config import (
                    ConfigFeatureFlagAdapter,
                )

                flags = ConfigFeatureFlagAdapter()

            is_active = flags.is_enabled(flag_key, default=default, context=eval_ctx)
            if is_active:
                return fn(*args, **kwargs)

            if fallback is not None:
                return fallback(*args, **kwargs)

            raise FeatureFlagDisabledError(
                f"Feature flag '{flag_key}' is disabled for current context."
            )

        _tag_object(
            wrapped,
            FeatureFlagMetadata(flag_key=flag_key, fallback=fallback, default=default),
        )
        return wrapped

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
