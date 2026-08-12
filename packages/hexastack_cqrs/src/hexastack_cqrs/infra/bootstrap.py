from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from hexastack_core.adapters.logging import StandardLogger
from hexastack_core.infra.config import HexastackConfig
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_core.infra.registries.exception import ExceptionRegistry
from hexastack_core.ports.logging import LoggingPort
from hexastack_core.ports.unit_of_work import UnitOfWorkPort
from rodi import Container

from hexastack_cqrs.adapters.buses.command.synchronous import (
    SynchronousCommandBus,
)
from hexastack_cqrs.adapters.buses.event.synchronous import (
    SynchronousEventBus,
)
from hexastack_cqrs.adapters.buses.query.synchronous import (
    SynchronousQueryBus,
)
from hexastack_cqrs.infra.autodiscovery import AutodiscoveryScanner
from hexastack_cqrs.infra.config import (
    CqrsMiddlewareConfig,
    HexastackCqrsConfig,
    register_cqrs_config,
)
from hexastack_cqrs.infra.middleware.correlation import CorrelationMiddleware
from hexastack_cqrs.infra.middleware.generic import GenericMiddleware
from hexastack_cqrs.infra.middleware.logging import LoggingMiddleware
from hexastack_cqrs.infra.middleware.retry import TenacityRetryMiddleware
from hexastack_cqrs.infra.middleware.timing import TimingMiddleware
from hexastack_cqrs.infra.middleware.unit_of_work import UnitOfWorkMiddleware
from hexastack_cqrs.infra.pipeline import ExecutionPipeline
from hexastack_cqrs.infra.registries.command import CommandRegistry
from hexastack_cqrs.infra.registries.handler import HandlerRegistry
from hexastack_cqrs.infra.registries.presenter import PresenterRegistry
from hexastack_cqrs.infra.registries.query import QueryRegistry
from hexastack_cqrs.ports.buses import (
    CommandBusPort,
    EventBusPort,
    QueryBusPort,
)


@dataclass(frozen=True)
class BootstrapResult:
    """Dataclass holding all initialized registries, container, and execution pipeline.

    Notes/Architectural Intent:
        Encapsulates the complete bootstrapped application runtime context for web and CLI adapters.
    """

    pipeline: ExecutionPipeline
    container: Container
    config: HexastackConfig | None
    config_registry: ConfigRegistry
    exception_registry: ExceptionRegistry
    presenter_registry: PresenterRegistry
    handler_registry: HandlerRegistry
    command_registry: CommandRegistry
    query_registry: QueryRegistry


def bootstrap(
    config_path: str | Path | None = None,
    packages_to_scan: list[str | ModuleType] | None = None,
    container: Container | None = None,
    configure_container: Callable[[Container], None] | None = None,
    logger: LoggingPort | None = None,
    command_bus: CommandBusPort | None = None,
    query_bus: QueryBusPort | None = None,
    event_bus: EventBusPort | None = None,
) -> BootstrapResult:
    """Bootstrap a complete Hexastack CQRS application runtime with rodi DI, ordered middleware, and autodiscovery.

    Args:
        config_path: Optional path to a TOML configuration file.
        packages_to_scan: Optional list of package or module paths to autodiscover.
        container: Optional pre-configured rodi Container instance.
        configure_container: Optional callback hook to register user services into container.
        logger: Optional LoggingPort instance (defaults to StandardLogger or InMemoryLogger).
        command_bus: Optional custom CommandBusPort instance.
        query_bus: Optional custom QueryBusPort instance.
        event_bus: Optional custom EventBusPort instance.

    Returns:
        BootstrapResult containing configured pipeline, DI container, and registries.

    Raises:
        None.
    """
    di = container or Container()

    # 1. Initialize Registries
    config_reg = ConfigRegistry()
    register_cqrs_config(config_reg)
    exc_reg = ExceptionRegistry()
    pres_reg = PresenterRegistry()
    hand_reg = HandlerRegistry()
    cmd_reg = CommandRegistry()
    qry_reg = QueryRegistry()

    # Register registries in DI container
    di.add_instance(config_reg, declared_class=ConfigRegistry)
    di.add_instance(exc_reg, declared_class=ExceptionRegistry)
    di.add_instance(pres_reg, declared_class=PresenterRegistry)
    di.add_instance(hand_reg, declared_class=HandlerRegistry)
    di.add_instance(cmd_reg, declared_class=CommandRegistry)
    di.add_instance(qry_reg, declared_class=QueryRegistry)

    # 2. Logger setup
    active_logger = logger or StandardLogger()
    di.add_instance(active_logger, declared_class=LoggingPort)

    # 3. Load TOML Configuration if available
    loaded_config: HexastackConfig | None = None
    cqrs_config = HexastackCqrsConfig()

    if config_path and Path(config_path).exists():
        loaded_config = config_reg.load_config_toml(config_path)
        cqrs_section = loaded_config.get_section("cqrs", HexastackCqrsConfig)
        if cqrs_section is not None:
            cqrs_config = cqrs_section

    # 4. User container customization
    if configure_container is not None:
        configure_container(di)

    # 5. Assemble Ordered Middleware Pipeline
    mw_conf: CqrsMiddlewareConfig = cqrs_config.middleware
    ordered_middlewares: list[tuple[int, GenericMiddleware]] = []

    if mw_conf.correlation.enable:
        ordered_middlewares.append(
            (mw_conf.correlation.order, CorrelationMiddleware())
        )
    if mw_conf.timing.enable_slow_warning:
        ordered_middlewares.append(
            (
                mw_conf.timing.order,
                TimingMiddleware(logger=active_logger, config=mw_conf.timing),
            )
        )
    if mw_conf.logging.enable:
        ordered_middlewares.append(
            (
                mw_conf.logging.order,
                LoggingMiddleware(logger=active_logger, config=mw_conf.logging),
            )
        )
    if mw_conf.unit_of_work.enable and UnitOfWorkPort in di:
        ordered_middlewares.append(
            (
                mw_conf.unit_of_work.order,
                UnitOfWorkMiddleware(lambda: di.resolve(UnitOfWorkPort)),
            )
        )
    if mw_conf.retry.enable:
        ordered_middlewares.append(
            (
                mw_conf.retry.order,
                TenacityRetryMiddleware(
                    logger=active_logger, config=mw_conf.retry
                ),
            )
        )

    # Sort middleware by order ascending (outermost to innermost)
    middleware_list: list[GenericMiddleware] = [
        mw for _, mw in sorted(ordered_middlewares, key=lambda pair: pair[0])
    ]

    # 6. Assemble Buses
    cmd_bus = command_bus or SynchronousCommandBus(
        handler_registry=hand_reg, middleware=middleware_list
    )
    qry_bus = query_bus or SynchronousQueryBus(
        handler_registry=hand_reg, middleware=middleware_list
    )
    evt_bus = event_bus or SynchronousEventBus(middleware=middleware_list)

    di.add_instance(cmd_bus, declared_class=CommandBusPort)
    di.add_instance(qry_bus, declared_class=QueryBusPort)
    di.add_instance(evt_bus, declared_class=EventBusPort)

    # 7. Construct ExecutionPipeline
    pipeline = ExecutionPipeline(
        handler_registry=hand_reg,
        command_registry=cmd_reg,
        query_registry=qry_reg,
        presenter_registry=pres_reg,
        exception_registry=exc_reg,
        command_bus=cmd_bus,
        query_bus=qry_bus,
        event_bus=evt_bus,
    )
    di.add_instance(pipeline, declared_class=ExecutionPipeline)

    # 8. Autodiscovery
    if packages_to_scan:
        scanner = AutodiscoveryScanner(
            pipeline=pipeline, config_registry=config_reg, container=di
        )
        for pkg in packages_to_scan:
            if isinstance(pkg, str) or hasattr(pkg, "__path__"):
                scanner.scan_package(pkg)
            else:
                scanner.scan_module(pkg)

    return BootstrapResult(
        pipeline=pipeline,
        container=di,
        config=loaded_config,
        config_registry=config_reg,
        exception_registry=exc_reg,
        presenter_registry=pres_reg,
        handler_registry=hand_reg,
        command_registry=cmd_reg,
        query_registry=qry_reg,
    )
