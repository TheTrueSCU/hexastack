import inspect
from collections.abc import Callable, Sequence
from types import ModuleType
from typing import Any, cast

from hexastack_core.infra.autodiscovery import (
    DiscoveryVisitor,
    scan_modules,
)
from hexastack_core.infra.decorators import ConfigMetadata, ExceptionMetadata
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_core.ports.presenter import Presenter
from pydantic import BaseModel
from rodi import Container

from hexastack_cqrs.infra.decorators import HandlerMetadata, PresenterMetadata
from hexastack_cqrs.infra.pipeline import ExecutionPipeline


def _resolve_callable(
    obj: Any, container: Container | None = None
) -> Callable[..., Any]:
    """Resolve a callable handler from a function or class object."""
    if inspect.isclass(obj):
        if container is not None:
            if obj not in container:
                container.register(obj)
            return lambda *args, **kwargs: cast(
                Callable[..., Any], container.resolve(obj)
            )(*args, **kwargs)
        return cast(Callable[..., Any], obj())
    return cast(Callable[..., Any], obj)


def create_cqrs_visitor(
    pipeline: ExecutionPipeline,
    container: Container | None = None,
    config_registry: ConfigRegistry | None = None,
) -> DiscoveryVisitor:
    """Create a DiscoveryVisitor callback for single-pass CQRS component registration.

    Notes/Architectural Intent:
        Inspects discovered classes and functions for @command_handler, @query_handler,
        @event_handler, @presenter, and @exception_handler metadata, registering them
        into the supplied ExecutionPipeline and registries.

    Args:
        pipeline: Target ExecutionPipeline instance.
        container: Optional rodi Container for class instantiation.
        config_registry: Optional ConfigRegistry for config sections.

    Returns:
        DiscoveryVisitor callable accepting (member, module).

    Raises:
        None.
    """

    def visitor(obj: Any, module: ModuleType) -> None:
        if not (inspect.isfunction(obj) or inspect.isclass(obj)):
            return

        match getattr(obj, "__hexastack_handler__", None):
            case HandlerMetadata(kind="command", target_cls=target_cls):
                handler_fn = _resolve_callable(obj, container)
                pipeline._handler_registry.register(target_cls, handler_fn)
                pipeline._command_registry.register(target_cls)
            case HandlerMetadata(kind="query", target_cls=target_cls):
                handler_fn = _resolve_callable(obj, container)
                pipeline._handler_registry.register(target_cls, handler_fn)
                pipeline._query_registry.register(target_cls)
            case HandlerMetadata(kind="event", target_cls=target_cls):
                handler_fn = _resolve_callable(obj, container)
                event_bus: Any = pipeline._event_bus
                if hasattr(event_bus, "subscribe"):
                    event_bus.subscribe(target_cls, handler_fn)
            case PresenterMetadata(target_cls=target_cls, output_format=output_format):
                presenter_inst: Presenter
                if inspect.isclass(obj) and container is not None:
                    if obj not in container:
                        container.register(obj)
                    presenter_inst = cast(Presenter, container.resolve(obj))
                elif inspect.isclass(obj):
                    presenter_inst = cast(Presenter, obj())
                else:
                    presenter_inst = cast(Presenter, obj)

                pipeline._presenter_registry.register(
                    target_cls, output_format, presenter_inst
                )
            case ExceptionMetadata(target_cls=target_cls):
                if pipeline._exception_registry is not None:
                    handler_fn = _resolve_callable(obj, container)
                    pipeline._exception_registry.register(target_cls, handler_fn)
            case ConfigMetadata(section_name=section_name):
                if (
                    config_registry is not None
                    and inspect.isclass(obj)
                    and issubclass(obj, BaseModel)
                ):
                    config_registry.register_config_section(section_name, obj)
            case _:
                pass

    return visitor


def autodiscover_cqrs(
    packages_or_modules: Sequence[str | ModuleType],
    pipeline: ExecutionPipeline,
    container: Container | None = None,
    config_registry: ConfigRegistry | None = None,
) -> None:
    """Scan packages and register discovered CQRS handlers, presenters, and config sections.

    Args:
        packages_or_modules: Sequence of package names or module objects to inspect.
        pipeline: Target ExecutionPipeline instance.
        container: Optional rodi Container instance.
        config_registry: Optional ConfigRegistry instance.

    Returns:
        None.

    Raises:
        None.
    """
    visitor = create_cqrs_visitor(
        pipeline=pipeline,
        container=container,
        config_registry=config_registry,
    )
    scan_modules(packages_or_modules, [visitor])


__all__ = [
    "autodiscover_cqrs",
    "create_cqrs_visitor",
]
