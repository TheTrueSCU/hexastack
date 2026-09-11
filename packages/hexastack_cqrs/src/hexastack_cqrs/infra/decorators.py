import inspect
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
    "circuit_breaker",
    "CircuitBreakerMetadata",
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
    "saga",
    "SagaMetadata",
    "step",
    "StepMetadata",
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


_CIRCUIT_BREAKER_META_ATTR = "__hexastack_circuit_breaker__"


@dataclass(frozen=True)
class CircuitBreakerMetadata:
    """Metadata tag attached to command or query classes for declarative circuit breaker protection.

    Notes/Architectural Intent:
        Associates custom failure threshold and recovery timeout directly with domain messages.
    """

    failure_threshold: int = 5
    recovery_timeout_seconds: float = 10.0


def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout_seconds: float = 10.0,
) -> Callable[[type[Generic]], type[Generic]]:
    """Decorate a Command or Query class for declarative circuit breaker protection.

    Args:
        failure_threshold: Number of consecutive failures before tripping the circuit.
        recovery_timeout_seconds: Seconds to wait before probing recovery in HALF_OPEN.

    Returns:
        Decorator function attaching CircuitBreakerMetadata.
    """

    def decorator[G: Generic](cls: type[G]) -> type[G]:
        setattr(
            cls,
            _CIRCUIT_BREAKER_META_ATTR,
            CircuitBreakerMetadata(
                failure_threshold=failure_threshold,
                recovery_timeout_seconds=recovery_timeout_seconds,
            ),
        )
        return cls

    return decorator


_STEP_META_ATTR = "__hexastack_saga_step__"
_SAGA_META_ATTR = "__hexastack_saga__"


@dataclass(frozen=True)
class StepMetadata:
    """Metadata tag attached to class methods representing saga steps.

    Notes/Architectural Intent:
        Encapsulates step ordering, optional compensation binding, and prerequisites
        for deterministic topological assembly into a SagaDefinition.
    """

    name: str
    order: int = 0
    compensate: str | Callable[..., Any] | None = None
    depends_on: tuple[str, ...] = ()
    timeout_seconds: float | None = None


@dataclass(frozen=True)
class SagaMetadata:
    """Metadata tag attached to saga workflow classes or builder functions.

    Notes/Architectural Intent:
        Tags saga definitions for autodiscovery and optional Command trigger binding,
        supporting both functional DSL (Pattern A) and class-based step methods (Pattern B).
    """

    name: str
    trigger: type[Command] | None = None
    is_class: bool = False
    builder_fn: Callable[..., Any] | None = None


def step(
    name: str | None = None,
    order: int = 0,
    compensate: str | Callable[..., Any] | None = None,
    depends_on: list[str] | tuple[str, ...] | None = None,
    timeout_seconds: float | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Mark a class method as a forward step in a distributed saga.

    Args:
        name: Unique step name. If omitted, uses the decorated method name.
        order: Execution sequence index (lower runs first).
        compensate: Name of the compensating method on the same class, or a callable.
        depends_on: Optional list of prerequisite step names.
        timeout_seconds: Optional timeout bound in seconds for this step.

    Returns:
        Decorated method with StepMetadata attached.

    Notes/Architectural Intent:
        Enables Pattern B declarative class-based sagas with deterministic ordering.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        step_name = name or getattr(fn, "__name__", "anonymous_step")
        meta = StepMetadata(
            name=step_name,
            order=order,
            compensate=compensate,
            depends_on=tuple(depends_on) if depends_on else (),
            timeout_seconds=timeout_seconds,
        )
        setattr(fn, _STEP_META_ATTR, meta)
        return fn

    return decorator


def _collect_sorted_steps(
    target: type[Any], saga_name: str
) -> list[tuple[str, StepMetadata]]:
    """Collect and deterministically sort @step methods on a saga class.

    Args:
        target: Target class to inspect.
        saga_name: Name of the saga for error reporting.

    Returns:
        List of (attribute_name, StepMetadata) sorted by order.

    Raises:
        ValueError: If no @step methods are found.

    Notes/Architectural Intent:
        Guarantees deterministic forward step execution ordering regardless of
        method declaration order in class bodies.
    """
    steps_meta: list[tuple[str, StepMetadata]] = []
    for attr_name in dir(target):
        member = getattr(target, attr_name, None)
        if callable(member):
            meta = getattr(member, _STEP_META_ATTR, None)
            if isinstance(meta, StepMetadata):
                steps_meta.append((attr_name, meta))

    if not steps_meta:
        raise ValueError(
            f"Saga class '{saga_name}' must define at least one method decorated with @step."
        )

    steps_meta.sort(key=lambda item: item[1].order)
    return steps_meta


def _create_step_action(act: Callable[..., Any], context: Any) -> Callable[[Any], Any]:
    """Create invocation wrapper for a forward saga step action.

    Args:
        act: Method or callable to invoke.
        context: Top-level saga context/command.

    Returns:
        Callable accepting orchestrator ctx dict.

    Notes/Architectural Intent:
        Dynamically adapts between 0-arg, 1-arg (command/context), and 2-arg (command, ctx) signatures.
    """
    sig = inspect.signature(act)
    params = len(sig.parameters)

    def _invoker(ctx: Any) -> Any:
        if params == 0:
            return act()
        if params == 1:
            return act(context if context is not None else ctx)
        return act(context if context is not None else ctx, ctx)

    return _invoker


def _resolve_step_compensation(
    instance: Any, step_meta: StepMetadata, saga_name: str
) -> Callable[..., Any] | None:
    """Resolve compensation callable from method name or callable reference.

    Args:
        instance: Saga class instance.
        step_meta: Metadata of the current step.
        saga_name: Saga name for exception diagnostics.

    Returns:
        Resolved compensation callable or None.

    Raises:
        ValueError: If compensation method name does not exist on instance.

    Notes/Architectural Intent:
        Validates compensation seam presence at workflow assembly time.
    """
    if isinstance(step_meta.compensate, str):
        if not hasattr(instance, step_meta.compensate):
            raise ValueError(
                f"Saga step '{step_meta.name}' references non-existent "
                f"compensation method '{step_meta.compensate}' on '{saga_name}'."
            )
        return getattr(instance, step_meta.compensate)
    if callable(step_meta.compensate):
        return step_meta.compensate
    return None


def _create_step_compensation(
    cmp_fn: Callable[..., Any] | None,
) -> Callable[..., Any] | None:
    """Create invocation wrapper for a saga step compensation.

    Args:
        cmp_fn: Compensation callable or None.

    Returns:
        Wrapped compensation callable or None.

    Notes/Architectural Intent:
        Adapts between 0-arg, 1-arg (forward_result), and 2-arg (result, ctx) signatures.
    """
    if cmp_fn is None:
        return None
    sig = inspect.signature(cmp_fn)
    params = len(sig.parameters)

    def _comp_invoker(forward_res: Any, ctx: Any = None) -> Any:
        if params == 0:
            return cmp_fn()
        if params == 1:
            return cmp_fn(forward_res)
        return cmp_fn(forward_res, ctx)

    return _comp_invoker


def _build_class_saga(
    self: Any,
    steps_meta: list[tuple[str, StepMetadata]],
    saga_name: str,
    context: Any = None,
) -> Any:
    """Build SagaDefinition by configuring steps on SagaBuilder.

    Args:
        self: Saga class instance.
        steps_meta: Sequence of sorted step metadata pairs.
        saga_name: Workflow name.
        context: Optional trigger command or context data.

    Returns:
        Constructed SagaDefinition.

    Notes/Architectural Intent:
        Translates decorated class methods into fluent SagaDefinition configuration.
    """
    from hexastack_cqrs.infra.sagas import SagaBuilder

    builder = SagaBuilder(name=saga_name)
    for attr, step_meta in steps_meta:
        bound_action = getattr(self, attr)
        bound_comp = _resolve_step_compensation(self, step_meta, saga_name)

        builder.step(
            name=step_meta.name,
            action=_create_step_action(bound_action, context),
            compensate=_create_step_compensation(bound_comp),
            timeout_seconds=step_meta.timeout_seconds,
        )
    return builder.build()


def saga[T: Any](
    name: str | None = None,
    trigger: type[Command] | None = None,
) -> Callable[[T], T]:
    """Declare a distributed saga from a class (Pattern B) or a function (Pattern A).

    Args:
        name: Unique name for the saga workflow. Defaults to target class or function name.
        trigger: Optional domain Command type that triggers this saga in CQRS pipelines.

    Returns:
        Decorated class or function with SagaMetadata and saga generation capabilities attached.

    Notes/Architectural Intent:
        Unifies Pattern A (functional DSL) and Pattern B (class-based steps) under
        a single declarative decorator. For classes, automatically generates a
        `build_saga(self, context=None) -> SagaDefinition` method by sorting @step methods.
    """

    def decorator(target: T) -> T:
        from hexastack_cqrs.domain.sagas import SagaDefinition

        saga_name = name or getattr(target, "__name__", "UnnamedSaga")

        if inspect.isclass(target):
            steps_meta = _collect_sorted_steps(target, saga_name)

            def build_saga(self: Any, context: Any = None) -> SagaDefinition:
                return _build_class_saga(self, steps_meta, saga_name, context)

            target.build_saga = build_saga  # type: ignore[attr-defined]
            setattr(
                target,
                _SAGA_META_ATTR,
                SagaMetadata(name=saga_name, trigger=trigger, is_class=True),
            )
            return target

        # Pattern A: Function-based saga
        setattr(
            target,
            _SAGA_META_ATTR,
            SagaMetadata(
                name=saga_name,
                trigger=trigger,
                is_class=False,
                builder_fn=target,
            ),
        )
        return target

    return decorator
