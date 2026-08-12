import logging

from hexastack_logging.infra.formatters.console import ConsoleFormatter


def test_console_formatter():
    formatter = ConsoleFormatter(colorize=False, include_context=True)
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
    assert "[corr:cid-8888]" in out
    assert "Service initialized" in out


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
