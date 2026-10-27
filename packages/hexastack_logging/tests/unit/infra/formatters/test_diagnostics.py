"""Unit tests for DiagnosticExceptionFormatter and format_diagnostics utilities.

Notes/Architectural Intent:
    Verifies that stackprinter-powered diagnostic formatters accurately capture
    frame-level variables, respect secret suppression rules, sanitize inline PII,
    and integrate cleanly with standard Python logging.Formatter pipelines.
"""

import logging
import sys

import pytest

from hexastack_core.domain.exceptions import MissingDependencyError
from hexastack_logging.infra.formatters.diagnostics import (
    DiagnosticExceptionFormatter,
    format_diagnostics,
)


def _trigger_failing_function(order_id: str, secret_token: str, quantity: int) -> int:
    """Helper to simulate an exception inside a nested function frame."""
    discount = 5
    calculated = quantity - discount
    if calculated < 0 and secret_token:
        msg = f"Invalid order {order_id} with Bearer secret-payload-token-12345"
        raise ValueError(msg)
    return calculated


def test_diagnostic_formatter_frame_variables_and_redaction() -> None:
    """Verify that frame variables are displayed and sensitive names are masked."""
    formatter = DiagnosticExceptionFormatter(style="plaintext", show_vals="all")

    captured_err: BaseException | None = None
    auth_token = "".join(["dyn", "_secret", "_val"])
    try:
        _trigger_failing_function("ord_42", auth_token, 2)
    except ValueError as err:
        captured_err = err

    assert captured_err is not None
    output = formatter.format_exception(captured_err)

    # 1. Non-sensitive variables should be visible in frame
    assert "ord_42" in output
    assert "quantity" in output

    # 2. Secret variable name should be masked in both frames (suppressed_vars replaces with *****)
    assert auth_token not in output
    assert "*****" in output

    # 3. Inline Bearer token in error message should be scrubbed by LogSanitizer
    assert "secret-payload-token-12345" not in output
    assert "***REDACTED***" in output


def test_format_diagnostics_convenience_function() -> None:
    """Verify format_diagnostics standalone helper generates sanitized traces."""
    captured_err: BaseException | None = None
    user_password = "".join(["cleartext", "_", "pass"])
    try:
        user_name = "test_user_alice"
        if user_password:
            msg = f"User {user_name} failed auth"
            raise RuntimeError(msg)
    except RuntimeError as err:
        captured_err = err

    assert captured_err is not None
    output = format_diagnostics(captured_err, style="plaintext")

    assert "test_user_alice" in output
    assert user_password not in output
    assert "*****" in output


def test_diagnostic_formatter_logging_record_integration() -> None:
    """Verify DiagnosticExceptionFormatter integrates with logging.LogRecord."""
    formatter = DiagnosticExceptionFormatter(
        fmt="%(levelname)s: %(message)s\n%(exc_text)s",
        style="plaintext",
    )

    logger = logging.getLogger("hexastack.test.diagnostics")
    record: logging.LogRecord | None = None
    api_key = "".join(["sk_live", "_", "testkey123"])

    try:
        x = 100
        if api_key:
            msg = f"Failure on calculation with {x}"
            raise ArithmeticError(msg)
    except ArithmeticError:
        exc_info = sys.exc_info()
        record = logger.makeRecord(
            name=logger.name,
            level=logging.ERROR,
            fn="test_diagnostics.py",
            lno=75,
            msg="Calculation crashed",
            args=(),
            exc_info=exc_info,
        )

    assert record is not None
    assert record.exc_info is not None
    formatted_trace = formatter.formatException(record.exc_info)
    assert "ArithmeticError: Failure on calculation with 100" in formatted_trace
    assert api_key not in formatted_trace
    assert "*****" in formatted_trace


def test_diagnostic_formatter_missing_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify MissingDependencyError is raised when stackprinter is not installed."""
    monkeypatch.setitem(sys.modules, "stackprinter", None)

    with pytest.raises(
        MissingDependencyError, match="hexastack-logging\\[diagnostics\\]"
    ):
        DiagnosticExceptionFormatter()
