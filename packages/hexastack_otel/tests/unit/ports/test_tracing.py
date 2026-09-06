from typing import Any

import pytest

from hexastack_otel.ports.tracing import SpanPort, TracingPort


def test_span_port_abstract():
    with pytest.raises(TypeError):
        SpanPort()  # type: ignore[abstract]

    # Subclasses missing specific abstract methods
    class IncompleteSpan1(SpanPort):
        def end(self) -> None: pass
        def record_exception(self, exception: BaseException) -> None: pass
        def set_attribute(self, key: str, value: Any) -> None: pass
        def set_attributes(self, attributes: dict[str, Any]) -> None: pass
        # Missing set_status

    with pytest.raises(TypeError):
        IncompleteSpan1()  # type: ignore[abstract]

    class IncompleteSpan2(SpanPort):
        def set_status(self, status: str, description: str | None = None) -> None: pass
        def record_exception(self, exception: BaseException) -> None: pass
        def set_attribute(self, key: str, value: Any) -> None: pass
        def set_attributes(self, attributes: dict[str, Any]) -> None: pass
        # Missing end

    with pytest.raises(TypeError):
        IncompleteSpan2()  # type: ignore[abstract]

    class IncompleteSpan3(SpanPort):
        def end(self) -> None: pass
        def set_status(self, status: str, description: str | None = None) -> None: pass
        def set_attribute(self, key: str, value: Any) -> None: pass
        def set_attributes(self, attributes: dict[str, Any]) -> None: pass
        # Missing record_exception

    with pytest.raises(TypeError):
        IncompleteSpan3()  # type: ignore[abstract]

    class IncompleteSpan4(SpanPort):
        def end(self) -> None: pass
        def set_status(self, status: str, description: str | None = None) -> None: pass
        def record_exception(self, exception: BaseException) -> None: pass
        def set_attributes(self, attributes: dict[str, Any]) -> None: pass
        # Missing set_attribute

    with pytest.raises(TypeError):
        IncompleteSpan4()  # type: ignore[abstract]

    class IncompleteSpan5(SpanPort):
        def end(self) -> None: pass
        def set_status(self, status: str, description: str | None = None) -> None: pass
        def record_exception(self, exception: BaseException) -> None: pass
        def set_attribute(self, key: str, value: Any) -> None: pass
        # Missing set_attributes

    with pytest.raises(TypeError):
        IncompleteSpan5()  # type: ignore[abstract]


def test_tracing_port_abstract():
    with pytest.raises(TypeError):
        TracingPort()  # type: ignore[abstract]

    class IncompleteTracing1(TracingPort):
        def extract_context(self, carrier: dict[str, str]): pass
        def get_current_span(self): pass
        def inject_context(self, carrier: dict[str, str]) -> None: pass
        def start_span(self, name: str, *, attributes=None, parent_context=None): pass
        # Missing trace_scope

    with pytest.raises(TypeError):
        IncompleteTracing1()  # type: ignore[abstract]

    class IncompleteTracing2(TracingPort):
        def extract_context(self, carrier: dict[str, str]): pass
        def get_current_span(self): pass
        def inject_context(self, carrier: dict[str, str]) -> None: pass
        def trace_scope(self, name: str, *, attributes=None): pass
        # Missing start_span

    with pytest.raises(TypeError):
        IncompleteTracing2()  # type: ignore[abstract]

    class IncompleteTracing3(TracingPort):
        def extract_context(self, carrier: dict[str, str]): pass
        def get_current_span(self): pass
        def start_span(self, name: str, *, attributes=None, parent_context=None): pass
        def trace_scope(self, name: str, *, attributes=None): pass
        # Missing inject_context

    with pytest.raises(TypeError):
        IncompleteTracing3()  # type: ignore[abstract]

    class IncompleteTracing4(TracingPort):
        def extract_context(self, carrier: dict[str, str]): pass
        def inject_context(self, carrier: dict[str, str]) -> None: pass
        def start_span(self, name: str, *, attributes=None, parent_context=None): pass
        def trace_scope(self, name: str, *, attributes=None): pass
        # Missing get_current_span

    with pytest.raises(TypeError):
        IncompleteTracing4()  # type: ignore[abstract]

    class IncompleteTracing5(TracingPort):
        def get_current_span(self): pass
        def inject_context(self, carrier: dict[str, str]) -> None: pass
        def start_span(self, name: str, *, attributes=None, parent_context=None): pass
        def trace_scope(self, name: str, *, attributes=None): pass
        # Missing extract_context

    with pytest.raises(TypeError):
        IncompleteTracing5()  # type: ignore[abstract]

