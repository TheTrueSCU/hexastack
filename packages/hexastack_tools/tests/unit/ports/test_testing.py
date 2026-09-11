"""Unit tests for testing ports ABC contracts.

Notes/Architectural Intent:
    Verifies that TestingRunnerPort and TestingPresenterPort enforce
    subclassing and method implementation contracts.
"""

from __future__ import annotations

import pytest

from hexastack_tools.ports.testing import TestingPresenterPort, TestingRunnerPort


def test_testing_ports_cannot_be_instantiated_directly():
    """Verify ABC contracts prevent direct instantiation."""
    with pytest.raises(TypeError):
        TestingRunnerPort()  # type: ignore[abstract]

    with pytest.raises(TypeError):
        TestingPresenterPort()  # type: ignore[abstract]
