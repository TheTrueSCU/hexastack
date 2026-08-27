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


def test_otel_bootstrapper_attributes_and_registration():
    bootstrapper = OtelBootstrapper()
    assert bootstrapper.name == "otel"
    assert bootstrapper.order == 12

    config_reg = ConfigRegistry()
    bootstrapper.register_config(config_reg)
    assert "otel" in config_reg
    assert config_reg.get("otel") == HexastackOtelConfig


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
    assert ctx.properties.get("tracing_port") is tracer
    assert ctx.properties.get("otel_config") is cfg


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
    assert ctx.properties.get("tracing_port") is tracer


def test_otel_bootstrapper_configuration_otlp_http_and_grpc():
    bootstrapper = OtelBootstrapper()
    container = Container()
    config_reg = ConfigRegistry()
    bootstrapper.register_config(config_reg)

    cfg = HexastackOtelConfig(
        service_name="http-svc",
        exporter="otlp_http",
        endpoint="http://localhost:4318",
    )
    container.add_instance(cfg, declared_class=HexastackOtelConfig)

    ctx = BootstrapContext(container=container, config=None, config_registry=config_reg)
    bootstrapper.configure(ctx)

    tracer = container.resolve(TracingPort)
    assert isinstance(tracer, OtelTracingAdapter)


def test_otel_bootstrapper_configuration_otlp_grpc():
    bootstrapper = OtelBootstrapper()
    container = Container()
    config_reg = ConfigRegistry()
    bootstrapper.register_config(config_reg)

    cfg = HexastackOtelConfig(
        service_name="grpc-svc",
        exporter="otlp_grpc",
        endpoint="localhost:4317",
    )
    container.add_instance(cfg, declared_class=HexastackOtelConfig)

    ctx = BootstrapContext(container=container, config=None, config_registry=config_reg)
    bootstrapper.configure(ctx)

    tracer = container.resolve(TracingPort)
    assert isinstance(tracer, OtelTracingAdapter)


def test_otel_bootstrapper_configuration_default_fallback():
    bootstrapper = OtelBootstrapper()
    container = Container()
    config_reg = ConfigRegistry()
    bootstrapper.register_config(config_reg)

    cfg = HexastackOtelConfig.model_construct(
        service_name="unknown-svc",
        exporter="unknown_exporter",
    )
    container.add_instance(cfg, declared_class=HexastackOtelConfig)

    ctx = BootstrapContext(container=container, config=None, config_registry=config_reg)
    bootstrapper.configure(ctx)

    tracer = container.resolve(TracingPort)
    assert isinstance(tracer, InMemoryTracingAdapter)


def test_otel_bootstrapper_configuration_otlp_grpc_and_http():
    """Verify OTLP gRPC and HTTP exporter configuration branches."""
    bootstrapper = OtelBootstrapper()

    # 1. otlp_grpc branch
    c_grpc = Container()
    cfg_grpc = HexastackOtelConfig(
        service_name="grpc-svc",
        exporter="otlp_grpc",
        endpoint="localhost:4317",
    )
    c_grpc.add_instance(cfg_grpc, declared_class=HexastackOtelConfig)
    ctx_grpc = BootstrapContext(
        container=c_grpc, config=None, config_registry=ConfigRegistry()
    )
    bootstrapper.configure(ctx_grpc)
    assert isinstance(c_grpc.resolve(TracingPort), OtelTracingAdapter)

    # 2. otlp_http branch
    c_http = Container()
    cfg_http = HexastackOtelConfig(
        service_name="http-svc",
        exporter="otlp_http",
        endpoint="http://localhost:4318",
    )
    c_http.add_instance(cfg_http, declared_class=HexastackOtelConfig)
    ctx_http = BootstrapContext(
        container=c_http, config=None, config_registry=ConfigRegistry()
    )
    bootstrapper.configure(ctx_http)
    assert isinstance(c_http.resolve(TracingPort), OtelTracingAdapter)

    # 3. fallback unknown branch
    c_unknown = Container()
    cfg_unknown = HexastackOtelConfig.model_construct(
        service_name="unknown-svc",
        exporter="unknown_val",
        enabled=True,
        endpoint="",
    )
    c_unknown.add_instance(cfg_unknown, declared_class=HexastackOtelConfig)
    ctx_unknown = BootstrapContext(
        container=c_unknown, config=None, config_registry=ConfigRegistry()
    )
    bootstrapper.configure(ctx_unknown)
    assert isinstance(c_unknown.resolve(TracingPort), InMemoryTracingAdapter)


def test_otel_bootstrapper_configure_without_explicit_config():
    """Verify OtelBootstrapper resolves default config when HexastackOtelConfig is not added in container."""
    bootstrapper = OtelBootstrapper()
    container = Container()
    config_reg = ConfigRegistry()
    bootstrapper.register_config(config_reg)

    ctx = BootstrapContext(container=container, config=None, config_registry=config_reg)
    bootstrapper.configure(ctx)

    assert "tracing_port" in ctx.properties
    assert isinstance(ctx.properties["tracing_port"], InMemoryTracingAdapter)
