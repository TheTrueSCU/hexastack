"""Unit tests for hexastack_ui presentation ports."""

import inspect

import pytest

from hexastack_ui.domain.models import DevToolsDashboardState
from hexastack_ui.ports.presenter import DevToolsPresenterPort, UIPresenterPort


def test_ports_abstract_instantiation_raises():
    """Verify abstract presentation ports cannot be instantiated directly."""
    with pytest.raises(TypeError):
        UIPresenterPort()  # ty: ignore[call-non-callable]

    with pytest.raises(TypeError):
        DevToolsPresenterPort()  # ty: ignore[call-non-callable]


def test_concrete_port_implementation():
    """Verify concrete subclass can implement abstract methods."""

    class DummyUIPresenter(UIPresenterPort):
        def mount(self, target_app, **kwargs):
            return "mounted"

    class DummyDevToolsPresenter(DevToolsPresenterPort):
        def render_dashboard(self, state: DevToolsDashboardState, target_app, **kwargs):
            return "rendered"

    ui_p = DummyUIPresenter()
    assert ui_p.mount(None) == "mounted"

    dt_p = DummyDevToolsPresenter()
    assert dt_p.render_dashboard(DevToolsDashboardState(), None) == "rendered"


def test_u_i_presenter_port_is_abstract() -> None:
    """Verify that UIPresenterPort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(UIPresenterPort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        UIPresenterPort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_u_i_presenter_port_abstract_methods() -> None:
    """Verify abstract methods on UIPresenterPort."""
    expected = {"mount"}
    abstracts = UIPresenterPort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0


def test_dev_tools_presenter_port_is_abstract() -> None:
    """Verify that DevToolsPresenterPort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(DevToolsPresenterPort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        DevToolsPresenterPort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_dev_tools_presenter_port_abstract_methods() -> None:
    """Verify abstract methods on DevToolsPresenterPort."""
    expected = {"render_dashboard"}
    abstracts = DevToolsPresenterPort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0
