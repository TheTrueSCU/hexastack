"""Unit tests for hexastack-qual domain exceptions.

Notes/Architectural Intent:
    Verifies that all domain exceptions carry structured attributes and format
    helpful error messages.
"""

from __future__ import annotations

from hexastack_qual.domain.exceptions import (
    AdapterNotAvailableError,
    ComplexityExceededError,
    ParityViolationError,
    QualityError,
    QualityGateFailedError,
    StatementIntegrityError,
)


def test_quality_error_base() -> None:
    """Ensure QualityError is a standard Exception."""
    err = QualityError("base error")
    msg = str(err)
    assert msg == "base error"
    assert isinstance(err, Exception)


def test_complexity_exceeded_error() -> None:
    """Ensure ComplexityExceededError formats attributes and message."""
    err = ComplexityExceededError(
        function_name="bad_func",
        file_path="src/pkg/mod.py",
        complexity=32,
        threshold=25,
    )
    msg = str(err)
    has_func = "bad_func" in msg
    has_file = "src/pkg/mod.py" in msg
    assert has_func is True
    assert has_file is True
    assert err.complexity == 32
    assert err.threshold == 25
    assert isinstance(err, QualityError)


def test_parity_violation_error() -> None:
    """Ensure ParityViolationError records missing test paths."""
    missing = ["tests/unit/test_foo.py", "tests/unit/test_bar.py"]
    err = ParityViolationError(missing_tests=missing)
    msg = str(err)
    has_count = "2 missing" in msg
    assert has_count is True
    assert len(err.missing_tests) == 2
    assert isinstance(err, QualityError)


def test_statement_integrity_error() -> None:
    """Ensure StatementIntegrityError records invalid files."""
    invalid = ["src/pkg/a.py"]
    err = StatementIntegrityError(invalid_files=invalid)
    msg = str(err)
    has_count = "1 file(s)" in msg
    assert has_count is True
    assert err.invalid_files == invalid
    assert isinstance(err, QualityError)


def test_quality_gate_failed_error() -> None:
    """Ensure QualityGateFailedError encapsulates check and details."""
    err = QualityGateFailedError(check_name="Ruff", details="Linting syntax error")
    msg = str(err)
    has_check = "Ruff" in msg
    has_details = "Linting syntax error" in msg
    assert has_check is True
    assert has_details is True
    assert err.check_name == "Ruff"
    assert err.details == "Linting syntax error"
    assert isinstance(err, QualityError)


def test_adapter_not_available_error() -> None:
    """Ensure AdapterNotAvailableError provides installation instructions."""
    err = AdapterNotAvailableError(
        extra_name="mcp",
        install_command="pip install 'hexastack-qual[mcp]'",
    )
    msg = str(err)
    has_extra = "mcp" in msg
    has_cmd = "pip install 'hexastack-qual[mcp]'" in msg
    assert has_extra is True
    assert has_cmd is True
    assert err.extra_name == "mcp"
    assert err.install_command == "pip install 'hexastack-qual[mcp]'"
    assert isinstance(err, QualityError)
