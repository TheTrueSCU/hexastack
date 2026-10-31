import inspect
from typing import Any

import pytest

from hexastack_otel.ports.tracing import SpanPort, TracingPort


def test_span_port_abstract():
    with pytest.raises(TypeError):
        SpanPort()  # ty: ignore[call-non-callable]

    # Subclasses missing specific abstract methods
    class IncompleteSpan1(SpanPort):
        def end(self) -> None:
            pass

        def record_exception(self, exception: BaseException) -> None:
            pass

        def set_attribute(self, key: str, value: Any) -> None:
            pass

        def set_attributes(self, attributes: dict[str, Any]) -> None:
            pass

        # Missing set_status

    with pytest.raises(TypeError):
        IncompleteSpan1()  # ty: ignore[call-non-callable]

    class IncompleteSpan2(SpanPort):
        def set_status(self, status: str, description: str | None = None) -> None:
            pass

        def record_exception(self, exception: BaseException) -> None:
            pass

        def set_attribute(self, key: str, value: Any) -> None:
            pass

        def set_attributes(self, attributes: dict[str, Any]) -> None:
            pass

        # Missing end

    with pytest.raises(TypeError):
        IncompleteSpan2()  # ty: ignore[call-non-callable]

    class IncompleteSpan3(SpanPort):
        def end(self) -> None:
            pass

        def set_status(self, status: str, description: str | None = None) -> None:
            pass

        def set_attribute(self, key: str, value: Any) -> None:
            pass

        def set_attributes(self, attributes: dict[str, Any]) -> None:
            pass

        # Missing record_exception

    with pytest.raises(TypeError):
        IncompleteSpan3()  # ty: ignore[call-non-callable]

    class IncompleteSpan4(SpanPort):
        def end(self) -> None:
            pass

        def set_status(self, status: str, description: str | None = None) -> None:
            pass

        def record_exception(self, exception: BaseException) -> None:
            pass

        def set_attributes(self, attributes: dict[str, Any]) -> None:
            pass

        # Missing set_attribute

    with pytest.raises(TypeError):
        IncompleteSpan4()  # ty: ignore[call-non-callable]

    class IncompleteSpan5(SpanPort):
        def end(self) -> None:
            pass

        def set_status(self, status: str, description: str | None = None) -> None:
            pass

        def record_exception(self, exception: BaseException) -> None:
            pass

        def set_attribute(self, key: str, value: Any) -> None:
            pass

        # Missing set_attributes

    with pytest.raises(TypeError):
        IncompleteSpan5()  # ty: ignore[call-non-callable]


def test_tracing_port_abstract():
    with pytest.raises(TypeError):
        TracingPort()  # ty: ignore[call-non-callable]

    class IncompleteTracing1(TracingPort):
        def extract_context(self, carrier: dict[str, str]):
            pass

        def get_current_span(self):
            pass

        def inject_context(self, carrier: dict[str, str]) -> None:
            pass

        def start_span(self, name: str, *, attributes=None, parent_context=None):
            pass

        def shutdown(self) -> None:
            pass

        # Missing trace_scope

    with pytest.raises(TypeError):
        IncompleteTracing1()

    class IncompleteTracing2(TracingPort):
        def extract_context(self, carrier: dict[str, str]):
            pass

        def get_current_span(self):
            pass

        def inject_context(self, carrier: dict[str, str]) -> None:
            pass

        def trace_scope(self, name: str, *, attributes=None):
            pass

        def shutdown(self) -> None:
            pass

        # Missing start_span

    with pytest.raises(TypeError):
        IncompleteTracing2()  # ty: ignore[call-non-callable]

    class IncompleteTracing3(TracingPort):
        def extract_context(self, carrier: dict[str, str]):
            pass

        def get_current_span(self):
            pass

        def start_span(self, name: str, *, attributes=None, parent_context=None):
            pass

        def trace_scope(self, name: str, *, attributes=None):
            pass

        def shutdown(self) -> None:
            pass

        # Missing inject_context

    with pytest.raises(TypeError):
        IncompleteTracing3()  # ty: ignore[call-non-callable]

    class IncompleteTracing4(TracingPort):
        def extract_context(self, carrier: dict[str, str]):
            pass

        def inject_context(self, carrier: dict[str, str]) -> None:
            pass

        def start_span(self, name: str, *, attributes=None, parent_context=None):
            pass

        def trace_scope(self, name: str, *, attributes=None):
            pass

        def shutdown(self) -> None:
            pass

        # Missing get_current_span

    with pytest.raises(TypeError):
        IncompleteTracing4()  # ty: ignore[call-non-callable]

    class IncompleteTracing5(TracingPort):
        def get_current_span(self):
            pass

        def inject_context(self, carrier: dict[str, str]) -> None:
            pass

        def start_span(self, name: str, *, attributes=None, parent_context=None):
            pass

        def trace_scope(self, name: str, *, attributes=None):
            pass

        def shutdown(self) -> None:
            pass

        # Missing extract_context

    with pytest.raises(TypeError):
        IncompleteTracing5()  # ty: ignore[call-non-callable]

    class IncompleteTracing6(TracingPort):
        def extract_context(self, carrier: dict[str, str]):
            pass

        def get_current_span(self):
            pass

        def inject_context(self, carrier: dict[str, str]) -> None:
            pass

        def start_span(self, name: str, *, attributes=None, parent_context=None):
            pass

        def trace_scope(self, name: str, *, attributes=None):
            pass

        # Missing shutdown

    with pytest.raises(TypeError):
        IncompleteTracing6()  # ty: ignore[call-non-callable]


def test_span_port_is_abstract() -> None:
    """Verify that SpanPort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(SpanPort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        SpanPort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_span_port_abstract_methods() -> None:
    """Verify abstract methods on SpanPort."""
    expected = {
        "end",
        "record_exception",
        "set_attribute",
        "set_attributes",
        "set_status",
    }
    abstracts = SpanPort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0


def test_tracing_port_is_abstract() -> None:
    """Verify that TracingPort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(TracingPort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        TracingPort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_tracing_port_abstract_methods() -> None:
    """Verify abstract methods on TracingPort."""
    expected = {
        "extract_context",
        "get_current_span",
        "inject_context",
        "shutdown",
        "start_span",
        "trace_scope",
    }
    abstracts = TracingPort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0
