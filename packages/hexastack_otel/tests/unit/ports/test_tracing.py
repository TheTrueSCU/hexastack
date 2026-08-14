import pytest

from hexastack_otel.ports.tracing import SpanPort, TracingPort


def test_span_port_abstract():
    with pytest.raises(TypeError):
        SpanPort()  # type: ignore[abstract]


def test_tracing_port_abstract():
    with pytest.raises(TypeError):
        TracingPort()  # type: ignore[abstract]
