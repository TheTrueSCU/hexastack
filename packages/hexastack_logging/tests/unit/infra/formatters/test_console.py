import logging

import pytest

from hexastack_logging.infra.formatters.console import (
    _MUTED,
    _RESET,
    ConsoleFormatter,
)


def test_console_formatter_uncolorized():
    formatter = ConsoleFormatter(
        colorize=False, include_context=True, datefmt="%Y-%m-%d %H:%M:%S"
    )
    record = logging.LogRecord(
        name="console_test",
        level=logging.INFO,
        pathname=__file__,
        lineno=30,
        msg="Service initialized",
        args=(),
        exc_info=None,
    )
    record.created = 1700000000.0  # 2023-11-14 22:13:20 UTC
    record.correlation_id = "cid-88889999"

    out = formatter.format(record)
    assert out == "[2023-11-14 22:13:20] [INFO    ] [corr:cid-8888] Service initialized"


def test_console_formatter_default_constructor():
    formatter = ConsoleFormatter()
    record = logging.LogRecord(
        name="console_test",
        level=logging.INFO,
        pathname=__file__,
        lineno=30,
        msg="Default run",
        args=(),
        exc_info=None,
    )
    record.created = 1700000000.0
    record.correlation_id = "cid-88889999"

    out = formatter.format(record)
    assert (
        out
        == f"{_MUTED}[2023-11-14 22:13:20]{_RESET} \033[32m[INFO    ]{_RESET} {_MUTED}[corr:cid-8888]{_RESET} Default run"
    )


def test_console_formatter_no_context():
    formatter = ConsoleFormatter(colorize=False, include_context=False)
    record = logging.LogRecord(
        name="console_test",
        level=logging.INFO,
        pathname=__file__,
        lineno=30,
        msg="Service initialized",
        args=(),
        exc_info=None,
    )
    record.correlation_id = "cid-88889999"

    out = formatter.format(record)
    assert "[INFO    ]" in out
    assert "[corr:" not in out
    assert "Service initialized" in out


@pytest.mark.parametrize(
    ("level_name", "level_no", "expected_color"),
    [
        ("DEBUG", logging.DEBUG, "\033[36m"),
        ("INFO", logging.INFO, "\033[32m"),
        ("WARNING", logging.WARNING, "\033[33m"),
        ("ERROR", logging.ERROR, "\033[31m"),
        ("CRITICAL", logging.CRITICAL, "\033[1;31m"),
    ],
)
def test_console_formatter_all_levels_colorized(
    level_name: str, level_no: int, expected_color: str
):
    formatter = ConsoleFormatter(colorize=True, include_context=True)
    record = logging.LogRecord(
        name="console_test",
        level=level_no,
        pathname=__file__,
        lineno=30,
        msg=f"Message for {level_name}",
        args=(),
        exc_info=None,
    )
    record.correlation_id = "123456789abcdef"

    out = formatter.format(record)
    assert f"{expected_color}[{level_name:<8}]{_RESET}" in out
    assert f"{_MUTED}[corr:12345678]{_RESET}" in out
    assert f"Message for {level_name}" in out


def test_console_formatter_colorized_and_exception():
    formatter = ConsoleFormatter(colorize=True, include_context=True)
    try:
        raise ValueError("test exception")
    except ValueError:
        import sys

        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="console_err",
        level=logging.ERROR,
        pathname=__file__,
        lineno=30,
        msg="Failed operation",
        args=(),
        exc_info=exc_info,
    )
    out = formatter.format(record)
    assert "Failed operation" in out
    assert "ValueError: test exception" in out
    assert "\033[31m[ERROR   ]\033[0m" in out
