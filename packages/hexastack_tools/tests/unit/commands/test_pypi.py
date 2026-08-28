"""Unit tests for pypi commands."""

from hexastack_tools.commands.pypi import (
    build_main,
    check_main,
    publish_main,
)


def test_pypi_callables() -> None:
    """Verify pypi distribution callables."""
    assert callable(build_main)
    assert callable(check_main)
    assert callable(publish_main)
