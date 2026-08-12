import importlib
import inspect
import pkgutil
from collections.abc import Callable
from types import ModuleType
from typing import Any, cast

from hexastack_core.infra.decorators import ConfigMetadata, ExceptionMetadata
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_core.ports.presenter import Presenter
from pydantic import BaseModel
from rodi import Container

from hexastack_cqrs.infra.decorators import HandlerMetadata, PresenterMetadata
from hexastack_cqrs.infra.pipeline import ExecutionPipeline


class AutodiscoveryScanner:
    """Scanner discovering metadata-tagged components and binding them to an ExecutionPipeline.

    Notes/Architectural Intent:
        Eliminates global singleton registries by discovering metadata-tagged commands, queries,
        events, presenters, exception handlers, and configuration schemas, binding them
        explicitly to the supplied ExecutionPipeline, rodi Container, and ConfigRegistry instances.
    """

    def __init__(
        self,
        pipeline: ExecutionPipeline,
        config_registry: ConfigRegistry | None = None,
        container: Container | None = None,
    ) -> None:
        """Initialize AutodiscoveryScanner with pipeline, config registry, and optional DI container.

        Args:
            pipeline: The ExecutionPipeline instance to register discovered handlers and presenters into.
            config_registry: Optional ConfigRegistry instance to register discovered configuration sections.
            container: Optional rodi Container for resolving class-based handler dependencies.
        """
        self._pipeline = pipeline
        self._config_registry = config_registry
        self._container = container

    def _resolve_callable(self, obj: Any) -> Callable[..., Any]:
        """Resolve a callable handler from a function or class object.

        Args:
            obj: The discovered function or class object.

        Returns:
            Callable handler invoking the function or container-resolved class instance.
        """
        if inspect.isclass(obj):
            container = self._container
            if container is not None:
                if obj not in container:
                    container.register(obj)
                return lambda *args, **kwargs: cast(Callable[..., Any], container.resolve(obj))(*args, **kwargs)
            return cast(Callable[..., Any], obj())
        return cast(Callable[..., Any], obj)

    def scan_module(self, module: ModuleType | str) -> int:
        """Scan a Python module and register all tagged components into pipeline and registries.

        Args:
            module: ModuleType or dot-separated module path string to import and scan.

        Returns:
            The number of discovered and registered components.

        Raises:
            ImportError: If string module path cannot be imported.
        """
        if isinstance(module, str):
            module = importlib.import_module(module)

        count = 0
        for _, obj in inspect.getmembers(module):
            if not (inspect.isfunction(obj) or inspect.isclass(obj)):
                continue

            match getattr(obj, "__hexastack_handler__", None):
                case HandlerMetadata(kind="command", target_cls=target_cls):
                    callable_handler = self._resolve_callable(obj)
                    self._pipeline._handler_registry.register(target_cls, callable_handler)
                    self._pipeline._command_registry.register(target_cls)
                    count += 1
                case HandlerMetadata(kind="query", target_cls=target_cls):
                    callable_handler = self._resolve_callable(obj)
                    self._pipeline._handler_registry.register(target_cls, callable_handler)
                    self._pipeline._query_registry.register(target_cls)
                    count += 1
                case HandlerMetadata(kind="event", target_cls=target_cls):
                    callable_handler = self._resolve_callable(obj)
                    event_bus: Any = self._pipeline._event_bus
                    if hasattr(event_bus, "subscribe"):
                        event_bus.subscribe(target_cls, callable_handler)
                        count += 1
                case PresenterMetadata(target_cls=target_cls, output_format=output_format):
                    presenter_inst: Presenter
                    if inspect.isclass(obj) and self._container is not None:
                        if obj not in self._container:
                            self._container.register(obj)
                        presenter_inst = cast(Presenter, self._container.resolve(obj))
                    elif inspect.isclass(obj):
                        presenter_inst = cast(Presenter, obj())
                    else:
                        presenter_inst = cast(Presenter, obj)

                    self._pipeline._presenter_registry.register(
                        target_cls, output_format, presenter_inst
                    )
                    count += 1
                case ExceptionMetadata(target_cls=target_cls):
                    if self._pipeline._exception_registry is not None:
                        callable_handler = self._resolve_callable(obj)
                        self._pipeline._exception_registry.register(target_cls, callable_handler)
                        count += 1
                case ConfigMetadata(section_name=section_name):
                    if (
                        self._config_registry is not None
                        and inspect.isclass(obj)
                        and issubclass(obj, BaseModel)
                    ):
                        self._config_registry.register_config_section(
                            section_name, obj
                        )
                        count += 1
                case _:
                    pass

        return count

    def scan_package(self, package: ModuleType | str) -> int:
        """Recursively scan a package and all its submodules for tagged components.

        Args:
            package: ModuleType or dot-separated package path string.

        Returns:
            Total count of discovered and registered components across the package tree.

        Raises:
            ImportError: If package path cannot be imported.
        """
        if isinstance(package, str):
            package = importlib.import_module(package)

        count = self.scan_module(package)

        if hasattr(package, "__path__"):
            for _, sub_name, _ in pkgutil.walk_packages(
                package.__path__, package.__name__ + "."
            ):
                sub_mod = importlib.import_module(sub_name)
                count += self.scan_module(sub_mod)

        return count
