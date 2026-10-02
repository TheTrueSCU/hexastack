"""Unit tests for RemoteExecutionPort contract and RemoteExecResult domain model.

Notes/Architectural Intent:
    Verifies that RemoteExecResult is immutable and memory-optimized with slots,
    and that RemoteExecutionPort enforces abstract method implementation.
"""

import pytest

from hexastack_core.ports.remote_exec import RemoteExecResult, RemoteExecutionPort


def test_remote_exec_result_slots_and_immutability() -> None:
    """Validate that RemoteExecResult declares slots and rejects mutation."""
    res = RemoteExecResult(
        exit_status=0,
        stdout="hello world\n",
        stderr="",
        duration_ms=42.5,
    )

    exit_code = res.exit_status
    out = res.stdout
    err = res.stderr
    dur = res.duration_ms

    assert exit_code == 0
    assert out == "hello world\n"
    assert err == ""
    assert dur == 42.5
    assert not hasattr(res, "__dict__")

    with pytest.raises((AttributeError, TypeError)):
        # Frozen dataclass should reject attribute mutation
        res.exit_status = 1  # type: ignore[misc]


def test_remote_execution_port_cannot_be_instantiated_directly() -> None:
    """Validate that RemoteExecutionPort is an abstract ABC requiring implementation."""
    with pytest.raises(TypeError):
        RemoteExecutionPort()  # type: ignore[abstract]
