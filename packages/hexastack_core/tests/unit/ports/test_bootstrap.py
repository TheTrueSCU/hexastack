"""Unit tests for bootstrap ports."""

from hexastack_core.ports.bootstrap import BootstrapperPort


def test_bootstrapper_port_interface() -> None:
    assert hasattr(BootstrapperPort, "bootstrap")
