"""Unit tests for hexastack_ui bootstrap."""

from rodi import Container

from hexastack_ui.infra.bootstrap import UIBootstrapper


def test_ui_bootstrapper():
    """Verify UIBootstrapper.bootstrap executes without error."""
    container = Container()
    UIBootstrapper.bootstrap(container)
    assert container is not None
