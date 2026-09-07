"""Unit tests for hexastack_ui presentation ports."""

import pytest

from hexastack_ui.domain.models import DevToolsDashboardState
from hexastack_ui.ports.presenter import DevToolsPresenterPort, UIPresenterPort


def test_ports_abstract_instantiation_raises():
    """Verify abstract presentation ports cannot be instantiated directly."""
    with pytest.raises(TypeError):
        UIPresenterPort()  # type: ignore[abstract]

    with pytest.raises(TypeError):
        DevToolsPresenterPort()  # type: ignore[abstract]


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
