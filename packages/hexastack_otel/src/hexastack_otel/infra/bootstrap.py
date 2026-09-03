from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SpanExporter

from hexastack_core.infra.bootstrap import BootstrapContext
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_core.ports.bootstrap import BootstrapperPort
from hexastack_otel.adapters.tracing.in_memory import InMemoryTracingAdapter
from hexastack_otel.adapters.tracing.otel import OtelTracingAdapter
from hexastack_otel.infra.config import HexastackOtelConfig, register_otel_config
from hexastack_otel.infra.middleware import TracingMiddleware
from hexastack_otel.ports.tracing import TracingPort


class OtelBootstrapper(BootstrapperPort):
    """Bootstrapper configuring OpenTelemetry tracing, exporters, and CQRS telemetry middleware.

    Notes/Architectural Intent:
        Executes at priority order=12 (after logging at 10, before auth at 16).
        Registers TracingPort and TracingMiddleware into the rodi Container.
    """

    order: int = 12
    name: str = "otel"

    def configure(self, context: BootstrapContext) -> None:
        """Assemble TracingPort and TracingMiddleware into the DI container in Phase 2.

        Args:
            context: The active BootstrapContext containing DI Container.
        """
        di = context.container

        # 1. Read OTel Configuration
        if HexastackOtelConfig in di:
            cfg = di.resolve(HexastackOtelConfig)
        else:
            cfg = context.get_config("otel", HexastackOtelConfig)

        # 2. Instantiate TracingPort Adapter
        tracer: TracingPort
        if cfg.exporter == "memory":
            tracer = InMemoryTracingAdapter()
        elif cfg.exporter == "console":
            tracer = OtelTracingAdapter(
                service_name=cfg.service_name,
                exporter=ConsoleSpanExporter(),
            )
        elif cfg.exporter == "otlp_grpc":
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter as GrpcOTLPExporter,
            )

            grpc_exporter: SpanExporter = GrpcOTLPExporter(
                endpoint=cfg.endpoint, insecure=True
            )
            tracer = OtelTracingAdapter(
                service_name=cfg.service_name,
                exporter=grpc_exporter,
            )
        elif cfg.exporter == "otlp_http":
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter as HttpOTLPExporter,
            )

            http_exporter: SpanExporter = HttpOTLPExporter(
                endpoint=f"{cfg.endpoint}/v1/traces"
            )
            tracer = OtelTracingAdapter(
                service_name=cfg.service_name,
                exporter=http_exporter,
            )
        else:
            tracer = InMemoryTracingAdapter()

        # 3. Register TracingPort in DI Container
        di.add_instance(tracer, declared_class=TracingPort)

        # 4. Instantiate & Register TracingMiddleware
        middleware = TracingMiddleware(tracer=tracer, enabled=cfg.enabled)
        di.add_instance(middleware, declared_class=TracingMiddleware)

        # 5. Instantiate & Register MetricsPort
        from hexastack_core.ports.metrics import MetricsPort
        from hexastack_otel.adapters.metrics.prometheus import PrometheusMetricsAdapter

        metrics_adapter = PrometheusMetricsAdapter()
        di.add_instance(metrics_adapter, declared_class=MetricsPort)

        # 6. Store in context properties
        context.properties["tracing_port"] = tracer
        context.properties["metrics_port"] = metrics_adapter
        context.properties["otel_config"] = cfg

    def register_config(self, registry: ConfigRegistry) -> None:
        """Register the OpenTelemetry configuration section in Phase 1.

        Args:
            registry: The active ConfigRegistry instance.
        """
        register_otel_config(registry)


__all__ = [
    "OtelBootstrapper",
]
