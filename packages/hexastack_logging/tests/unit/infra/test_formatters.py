import json
import logging

from hexastack_logging.infra.formatters.console import ConsoleFormatter
from hexastack_logging.infra.formatters.json import JsonFormatter


def test_json_formatter():
    formatter = JsonFormatter(include_context=True)
    record = logging.LogRecord(
        name="json_test",
        level=logging.ERROR,
        pathname=__file__,
        lineno=20,
        msg="Error processing order %s",
        args=("ord-100",),
        exc_info=None,
    )
    record.correlation_id = "cid-777"
    record.user_id = "u-1"
    record.tenant_id = "t-1"

    out = formatter.format(record)
    parsed = json.loads(out)

    assert parsed["level"] == "ERROR"
    assert parsed["logger"] == "json_test"
    assert parsed["message"] == "Error processing order ord-100"
    assert parsed["correlation_id"] == "cid-777"
    assert parsed["user_id"] == "u-1"
    assert parsed["tenant_id"] == "t-1"
    assert "timestamp" in parsed


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
