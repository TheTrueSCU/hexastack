from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from rodi import Container

from hexastack_core.adapters.circuit_breaker import InMemoryCircuitBreaker
from hexastack_core.adapters.logging import StandardLogger
from hexastack_core.infra.bootstrap import (
    BootstrapContext,
    BootstrapResult,
)
from hexastack_core.infra.bootstrap import (
    bootstrap as core_bootstrap,
)
from hexastack_core.infra.config import HexastackConfig
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_core.infra.registries.exception import ExceptionRegistry
from hexastack_core.ports.bootstrap import BootstrapperPort
from hexastack_core.ports.circuit_breaker import CircuitBreakerPort
from hexastack_core.ports.logging import LoggingPort
from hexastack_core.ports.unit_of_work import UnitOfWorkPort
from hexastack_cqrs.adapters.buses.command.synchronous import (
    SynchronousCommandBus,
)
from hexastack_cqrs.adapters.buses.event.synchronous import (
    SynchronousEventBus,
)
from hexastack_cqrs.adapters.buses.query.synchronous import (
    SynchronousQueryBus,
)
from hexastack_cqrs.infra.autodiscovery import create_cqrs_visitor
from hexastack_cqrs.infra.config import (
    CqrsMiddlewareConfig,
    HexastackCqrsConfig,
    register_cqrs_config,
)
from hexastack_cqrs.infra.middleware.circuit_breaker import (
    CircuitBreakerMiddleware,
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
class CqrsBootstrapResult:
    """Dataclass holding initialized CQRS registries, container, and execution pipeline.

    Notes/Architectural Intent:
        Encapsulates the complete bootstrapped CQRS runtime context for application adapters.
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


class CqrsBootstrapper(BootstrapperPort):
    """Bootstrap extension configuring CQRS buses, middleware pipeline, and autodiscovery.

    Notes/Architectural Intent:
        Implements BootstrapperPort for hexastack-cqrs, registering 'cqrs' config
        schemas in Phase 1 and assembling ExecutionPipeline with DI in Phase 2.
    """

    name: str = "cqrs"
    order: int = 20

    def configure(self, context: BootstrapContext) -> None:
        """Phase 2: Assemble CQRS registries, buses, middleware, and pipeline.

        Args:
            context: BootstrapContext containing DI container and configuration.

        Returns:
            None.

        Raises:
            None.
        """
        di = context.container

        # 1. Initialize CQRS Registries
        exc_reg = ExceptionRegistry()
        pres_reg = PresenterRegistry()
        hand_reg = HandlerRegistry()
        cmd_reg = CommandRegistry()
        qry_reg = QueryRegistry()

        di.add_instance(exc_reg, declared_class=ExceptionRegistry)
        di.add_instance(pres_reg, declared_class=PresenterRegistry)
        di.add_instance(hand_reg, declared_class=HandlerRegistry)
        di.add_instance(cmd_reg, declared_class=CommandRegistry)
        di.add_instance(qry_reg, declared_class=QueryRegistry)

        # 2. Resolve or fallback logger
        active_logger: LoggingPort
        if LoggingPort in di:
            active_logger = di.resolve(LoggingPort)
        else:
            active_logger = StandardLogger()
            di.add_instance(active_logger, declared_class=LoggingPort)

        # 3. Read CQRS configuration
        cqrs_config = HexastackCqrsConfig()
        if context.config is not None:
            section = context.config.get_section("cqrs", HexastackCqrsConfig)
            if section is not None:
                cqrs_config = section

        # 4. Assemble Ordered Middleware Pipeline
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
        if mw_conf.circuit_breaker.enable:
            active_cb: CircuitBreakerPort
            if CircuitBreakerPort in di:
                active_cb = di.resolve(CircuitBreakerPort)
            else:
                active_cb = InMemoryCircuitBreaker(
                    failure_threshold=mw_conf.circuit_breaker.failure_threshold,
                    recovery_timeout_seconds=mw_conf.circuit_breaker.recovery_timeout_seconds,
                    half_open_max_trials=mw_conf.circuit_breaker.half_open_max_trials,
                )
                di.add_instance(active_cb, declared_class=CircuitBreakerPort)
            ordered_middlewares.append(
                (
                    mw_conf.circuit_breaker.order,
                    CircuitBreakerMiddleware(
                        breaker=active_cb,
                        config=mw_conf.circuit_breaker,
                        logger=active_logger,
                    ),
                )
            )
        if mw_conf.retry.enable:
            ordered_middlewares.append(
                (
                    mw_conf.retry.order,
                    TenacityRetryMiddleware(logger=active_logger, config=mw_conf.retry),
                )
            )

        middleware_list: list[GenericMiddleware] = [
            mw for _, mw in sorted(ordered_middlewares, key=lambda p: p[0])
        ]

        # 5. Assemble Buses
        cmd_bus = SynchronousCommandBus(
            handler_registry=hand_reg, middleware=middleware_list
        )
        qry_bus = SynchronousQueryBus(
            handler_registry=hand_reg, middleware=middleware_list
        )
        evt_bus = SynchronousEventBus(middleware=middleware_list)

        di.add_instance(cmd_bus, declared_class=CommandBusPort)
        di.add_instance(qry_bus, declared_class=QueryBusPort)
        di.add_instance(evt_bus, declared_class=EventBusPort)

        # 6. Construct ExecutionPipeline
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
        context.properties["pipeline"] = pipeline
        context.properties["cqrs_result"] = CqrsBootstrapResult(
            pipeline=pipeline,
            container=di,
            config=context.config,
            config_registry=context.config_registry,
            exception_registry=exc_reg,
            presenter_registry=pres_reg,
            handler_registry=hand_reg,
            command_registry=cmd_reg,
            query_registry=qry_reg,
        )

        # 7. Register CQRS discovery visitor for single-pass scanning
        visitor = create_cqrs_visitor(
            pipeline=pipeline,
            container=di,
            config_registry=context.config_registry,
        )
        context.register_visitor(visitor)

    def register_config(self, registry: ConfigRegistry) -> None:
        """Phase 1: Register CQRS configuration schemas under 'cqrs'.

        Args:
            registry: Target ConfigRegistry instance.

        Returns:
            None.

        Raises:
            None.
        """
        register_cqrs_config(registry)


__all__ = [
    "bootstrap_cqrs",
    "CqrsBootstrapper",
    "CqrsBootstrapResult",
]


def bootstrap_cqrs(
    config_path: str | Path | None = None,
    packages_to_scan: list[str | ModuleType] | None = None,
    container: Container | None = None,
    bootstrappers: list[BootstrapperPort] | None = None,
) -> CqrsBootstrapResult:
    """Convenience helper to bootstrap application and extract CQRS runtime context.

    Args:
        config_path: Optional path to TOML configuration file.
        packages_to_scan: Optional list of packages to scan.
        container: Optional rodi Container.
        bootstrappers: Optional list of extra bootstrappers.

    Returns:
        CqrsBootstrapResult containing pipeline, DI container, and registries.

    Raises:
        None.
    """
    bts: list[BootstrapperPort] = [CqrsBootstrapper()]
    if bootstrappers:
        bts.extend(bootstrappers)

    res: BootstrapResult = core_bootstrap(
        config_path=config_path,
        packages_to_scan=packages_to_scan,
        container=container,
        bootstrappers=bts,
        auto_discover=True,
    )
    result: CqrsBootstrapResult = res.get("cqrs_result")
    return result
