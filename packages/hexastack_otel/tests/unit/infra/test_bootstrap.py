from rodi import Container

from hexastack_core.infra.bootstrap import BootstrapContext
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_otel.adapters.tracing import (
    InMemoryTracingAdapter,
    OtelTracingAdapter,
)
from hexastack_otel.infra.bootstrap import OtelBootstrapper
from hexastack_otel.infra.config import HexastackOtelConfig
from hexastack_otel.infra.middleware import TracingMiddleware
from hexastack_otel.ports.tracing import TracingPort


def test_otel_bootstrapper_configuration_console():
    bootstrapper = OtelBootstrapper()
    container = Container()
    config_reg = ConfigRegistry()
    bootstrapper.register_config(config_reg)

    cfg = HexastackOtelConfig(
        service_name="payment-svc",
        exporter="console",
    )
    container.add_instance(cfg, declared_class=HexastackOtelConfig)

    ctx = BootstrapContext(container=container, config=None, config_registry=config_reg)
    bootstrapper.configure(ctx)

    tracer = container.resolve(TracingPort)
    assert isinstance(tracer, OtelTracingAdapter)


def test_otel_bootstrapper_configuration_memory():
    bootstrapper = OtelBootstrapper()
    container = Container()
    config_reg = ConfigRegistry()
    bootstrapper.register_config(config_reg)

    ctx = BootstrapContext(container=container, config=None, config_registry=config_reg)
    bootstrapper.configure(ctx)

    tracer = container.resolve(TracingPort)
    assert isinstance(tracer, InMemoryTracingAdapter)

    middleware = container.resolve(TracingMiddleware)
    assert isinstance(middleware, TracingMiddleware)
