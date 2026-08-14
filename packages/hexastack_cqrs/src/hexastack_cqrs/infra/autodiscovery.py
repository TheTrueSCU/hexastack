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
from hexastack_core.ports.presenter import PresenterPort
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

        meta = getattr(obj, "__hexastack_handler__", None)
        if isinstance(meta, HandlerMetadata):
            handler_fn = _resolve_callable(obj, container)
            if meta.kind == "command":
                pipeline._handler_registry.register(meta.target_cls, handler_fn)
                pipeline._command_registry.register(meta.target_cls)
            elif meta.kind == "query":
                pipeline._handler_registry.register(meta.target_cls, handler_fn)
                pipeline._query_registry.register(meta.target_cls)
            elif meta.kind == "event":
                event_bus: Any = pipeline._event_bus
                if hasattr(event_bus, "subscribe"):
                    event_bus.subscribe(meta.target_cls, handler_fn)
        elif isinstance(meta, PresenterMetadata):
            presenter_inst: PresenterPort
            if inspect.isclass(obj) and container is not None:
                if obj not in container:
                    container.register(obj)
                presenter_inst = cast(PresenterPort, container.resolve(obj))
            elif inspect.isclass(obj):
                presenter_inst = cast(PresenterPort, obj())
            else:
                presenter_inst = cast(PresenterPort, obj)

            pipeline._presenter_registry.register(
                meta.target_cls, meta.output_format, presenter_inst
            )
        elif isinstance(meta, ExceptionMetadata):
            if pipeline._exception_registry is not None:
                handler_fn = _resolve_callable(obj, container)
                pipeline._exception_registry.register(meta.target_cls, handler_fn)
        elif isinstance(meta, ConfigMetadata):
            if (
                config_registry is not None
                and inspect.isclass(obj)
                and issubclass(obj, BaseModel)
            ):
                config_registry.register_config_section(meta.section_name, obj)

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
