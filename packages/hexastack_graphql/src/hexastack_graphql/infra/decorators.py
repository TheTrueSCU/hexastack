from collections.abc import Callable
from typing import Any, cast

import strawberry

from hexastack_core.ports.feature_flags import FeatureFlagPort
from hexastack_graphql.infra.autodiscovery import (
    _GRAPHQL_FIELD_ATTR,
    _GRAPHQL_TYPE_ATTR,
    GraphQLFieldMetadata,
    GraphQLTypeMetadata,
)
from hexastack_graphql.infra.registries.schema import GraphQLSchemaRegistry

_default_registry = GraphQLSchemaRegistry()


__all__ = [
    "feature_flag_field",
    "get_schema_registry",
    "graphql_mutation",
    "graphql_mutation_type",
    "graphql_query",
    "graphql_query_type",
]


def _resolve_flags(args: tuple[Any, ...], kwargs: dict[str, Any]) -> FeatureFlagPort:
    """Helper to extract FeatureFlagPort from arguments context or fallback to ConfigFeatureFlagAdapter."""
    from hexastack_core.adapters.feature_flags.config import ConfigFeatureFlagAdapter
    from hexastack_core.ports.feature_flags import FeatureFlagPort

    for item in (*args, *kwargs.values()):
        if hasattr(item, "context") and getattr(item.context, "container", None):
            container = item.context.container
            if FeatureFlagPort in container:
                return container.resolve(FeatureFlagPort)
            break
    return ConfigFeatureFlagAdapter()


def feature_flag_field(
    flag_key: str,
    *,
    default: bool = False,
    fallback: Any = None,
    raise_error: bool = True,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Wrap a Strawberry GraphQL field resolver with dynamic feature flag evaluation.

    Notes/Architectural Intent:
        Evaluates the specified feature flag against ambient UserContext / GraphQLContext.
        If disabled:
        - If raise_error is True, raises a GraphQLError with a descriptive message.
        - If raise_error is False, returns fallback value (e.g. None).

    Args:
        flag_key: Unique identifier of the feature flag to check.
        default: Fallback boolean value if flag is not explicitly configured.
        fallback: Value to return if flag is disabled and raise_error is False (defaults to None).
        raise_error: Whether to raise a GraphQLError when disabled (defaults to True).

    Returns:
        Decorator wrapping the GraphQL resolver function.
    """
    import inspect
    from functools import wraps

    from hexastack_core.domain.feature_flags import EvaluationContext
    from hexastack_graphql.domain.exceptions import GraphQLError

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        if inspect.iscoroutinefunction(fn):

            @wraps(fn)
            async def async_wrapped(*args: Any, **kwargs: Any) -> Any:
                flags = _resolve_flags(args, kwargs)
                eval_ctx = EvaluationContext.from_current_context()
                if not flags.is_enabled(flag_key, default=default, context=eval_ctx):
                    if raise_error:
                        raise GraphQLError(
                            f"GraphQL field is disabled by feature flag '{flag_key}'."
                        )
                    return fallback
                return await fn(*args, **kwargs)

            return async_wrapped

        @wraps(fn)
        def sync_wrapped(*args: Any, **kwargs: Any) -> Any:
            flags = _resolve_flags(args, kwargs)
            eval_ctx = EvaluationContext.from_current_context()
            if not flags.is_enabled(flag_key, default=default, context=eval_ctx):
                if raise_error:
                    raise GraphQLError(
                        f"GraphQL field is disabled by feature flag '{flag_key}'."
                    )
                return fallback
            return fn(*args, **kwargs)

        return sync_wrapped

    return decorator


def get_schema_registry() -> GraphQLSchemaRegistry:
    """Return the global default GraphQLSchemaRegistry instance.

    Returns:
        GraphQLSchemaRegistry instance.
    """
    return _default_registry


def graphql_mutation(
    name: str | None = None,
    *,
    description: str | None = None,
) -> Callable[[Callable[..., Any]], Any]:
    """Decorator registering a standalone function as a root GraphQL mutation field.

    Args:
        name: Optional custom field name.
        description: Optional GraphQL documentation description.

    Returns:
        Decorator function.
    """

    def decorator(fn: Callable[..., Any]) -> Any:
        field_name = name or getattr(fn, "__name__", "field")
        s_field = strawberry.mutation(fn, name=field_name, description=description)
        setattr(
            s_field,
            _GRAPHQL_FIELD_ATTR,
            GraphQLFieldMetadata(kind="mutation", name=field_name),
        )
        _default_registry.register_mutation_field(field_name, s_field)
        return s_field

    return decorator


def graphql_mutation_type[T: type[Any]](cls: T) -> T:
    """Decorator registering a class as a root Mutation type.

    Notes/Architectural Intent:
        Automatically applies @strawberry.type if not already applied,
        attaches discovery metadata, and registers in the default schema registry.

    Args:
        cls: Target class containing mutation fields.

    Returns:
        Decorated Strawberry type class.
    """
    wrapped: Any = cls
    if not hasattr(cls, "__strawberry_definition__"):
        wrapped = strawberry.type(cls)
    setattr(wrapped, _GRAPHQL_TYPE_ATTR, GraphQLTypeMetadata(kind="mutation"))
    _default_registry.register_mutation_type(cast("type[Any]", wrapped))
    return cast("T", wrapped)


def graphql_query(
    name: str | None = None,
    *,
    description: str | None = None,
) -> Callable[[Callable[..., Any]], Any]:
    """Decorator registering a standalone function as a root GraphQL query field.

    Args:
        name: Optional custom field name.
        description: Optional GraphQL documentation description.

    Returns:
        Decorator function.
    """

    def decorator(fn: Callable[..., Any]) -> Any:
        field_name = name or getattr(fn, "__name__", "field")
        s_field = strawberry.field(fn, name=field_name, description=description)
        setattr(
            s_field,
            _GRAPHQL_FIELD_ATTR,
            GraphQLFieldMetadata(kind="query", name=field_name),
        )
        _default_registry.register_query_field(field_name, s_field)
        return s_field

    return decorator


def graphql_query_type[T: type[Any]](cls: T) -> T:
    """Decorator registering a class as a root Query type.

    Notes/Architectural Intent:
        Automatically applies @strawberry.type if not already applied,
        attaches discovery metadata, and registers in the default schema registry.

    Args:
        cls: Target class containing query fields.

    Returns:
        Decorated Strawberry type class.
    """
    wrapped: Any = cls
    if not hasattr(cls, "__strawberry_definition__"):
        wrapped = strawberry.type(cls)
    setattr(wrapped, _GRAPHQL_TYPE_ATTR, GraphQLTypeMetadata(kind="query"))
    _default_registry.register_query_type(cast("type[Any]", wrapped))
    return cast("T", wrapped)
