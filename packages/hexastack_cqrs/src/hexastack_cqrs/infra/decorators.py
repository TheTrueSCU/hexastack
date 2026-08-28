from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, TypeVar

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
    "cached_query",
    "command_handler",
    "CommandInvalidationMetadata",
    "config_section",
    "ConfigMetadata",
    "event_listener",
    "exception_handler",
    "ExceptionMetadata",
    "feature_flag",
    "FeatureFlagMetadata",
    "HandlerMetadata",
    "invalidates_cache",
    "presenter",
    "PresenterMetadata",
    "query_handler",
    "QueryCacheMetadata",
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


_QUERY_CACHE_META_ATTR = "__hexastack_query_cache__"
_COMMAND_INVALIDATION_META_ATTR = "__hexastack_cache_invalidation__"


@dataclass(frozen=True)
class QueryCacheMetadata:
    """Metadata tag attached to Query models for declarative result caching.

    Notes/Architectural Intent:
        Encapsulates TTL, custom key fields, cache tag invalidation groups, and
        optional key builder callables without coupling queries to cache storage.
    """

    ttl_seconds: float | None = None
    key_fields: tuple[str, ...] | None = None
    tags: tuple[str, ...] = ()
    key_builder: Callable[[Any], str] | None = None


@dataclass(frozen=True)
class CommandInvalidationMetadata:
    """Metadata tag attached to Command models for declarative cache purging.

    Notes/Architectural Intent:
        Declares cache tags to invalidate when a mutating command executes successfully.
    """

    tags: tuple[str, ...] = ()


Q = TypeVar("Q", bound=type)
C = TypeVar("C", bound=type)


def cached_query(
    ttl_seconds: float | None = 300.0,
    key_fields: list[str] | tuple[str, ...] | None = None,
    tags: list[str] | tuple[str, ...] = (),
    key_builder: Callable[[Any], str] | None = None,
) -> Callable[[Q], Q]:
    """Decorate a Query class to enable automatic declarative result caching.

    Args:
        ttl_seconds: Time-to-live expiration duration in seconds (default: 300s).
        key_fields: Optional list of query field names to incorporate in the deterministic key.
        tags: Optional cache tags for group-based cache invalidation.
        key_builder: Optional custom callable to build the cache key from the query instance.

    Returns:
        Decorator function attaching QueryCacheMetadata.

    Notes/Architectural Intent:
        Allows queries to express caching intent declaratively on the contract without
        polluting query handlers with cache store lookups or mutations.
    """
    normalized_key_fields = tuple(key_fields) if key_fields is not None else None
    normalized_tags = tuple(tags)

    def decorator(cls: Q) -> Q:
        setattr(
            cls,
            _QUERY_CACHE_META_ATTR,
            QueryCacheMetadata(
                ttl_seconds=ttl_seconds,
                key_fields=normalized_key_fields,
                tags=normalized_tags,
                key_builder=key_builder,
            ),
        )
        return cls

    return decorator


def invalidates_cache(
    tags: list[str] | tuple[str, ...] = (),
) -> Callable[[C], C]:
    """Decorate a Command class to automatically purge tagged cache entries upon success.

    Args:
        tags: List of cache tags to invalidate (e.g. ['products', 'user:{user_id}']).

    Returns:
        Decorator function attaching CommandInvalidationMetadata.

    Notes/Architectural Intent:
        Provides declarative cache invalidation on domain commands without manual
        cache purging boilerplate inside command handlers.
    """
    normalized_tags = tuple(tags)

    def decorator(cls: C) -> C:
        setattr(
            cls,
            _COMMAND_INVALIDATION_META_ATTR,
            CommandInvalidationMetadata(tags=normalized_tags),
        )
        return cls

    return decorator
