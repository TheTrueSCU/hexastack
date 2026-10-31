"""Unit tests for RemoteExecutionPort contract and RemoteExecResult domain model.

Notes/Architectural Intent:
    Verifies that RemoteExecResult is immutable and memory-optimized with slots,
    and that RemoteExecutionPort enforces abstract method implementation.
"""

import inspect

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
        res.exit_status = 1  # ty: ignore[invalid-assignment]


def test_remote_execution_port_cannot_be_instantiated_directly() -> None:
    """Validate that RemoteExecutionPort is an abstract ABC requiring implementation."""
    with pytest.raises(TypeError):
        RemoteExecutionPort()  # ty: ignore[call-non-callable]


def test_remote_execution_port_is_abstract() -> None:
    """Verify that RemoteExecutionPort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(RemoteExecutionPort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        RemoteExecutionPort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_remote_execution_port_abstract_methods() -> None:
    """Verify abstract methods on RemoteExecutionPort."""
    expected = {"download_file", "run", "stream_output", "upload_file"}
    abstracts = RemoteExecutionPort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0
