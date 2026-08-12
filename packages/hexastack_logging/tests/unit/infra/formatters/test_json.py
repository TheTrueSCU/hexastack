import json
import logging

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


def test_json_formatter_with_exception():
    formatter = JsonFormatter(include_context=False)
    try:
        raise RuntimeError("json error")
    except RuntimeError:
        import sys

        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="json_err",
        level=logging.CRITICAL,
        pathname=__file__,
        lineno=30,
        msg="Critical failure",
        args=(),
        exc_info=exc_info,
    )
    out = formatter.format(record)
    parsed = json.loads(out)
    assert parsed["level"] == "CRITICAL"
    assert "exception" in parsed
    assert "RuntimeError: json error" in parsed["exception"]
