import logging

from hexastack_core.utils.context import (
    UserContext,
    correlation_id_ctx,
    set_correlation_id,
    set_user_context,
    user_ctx,
)
from hexastack_logging.infra.filters import (
    CorrelationIdFilter,
    SanitizerFilter,
)


def test_correlation_id_filter_enriches_record():
    corr_token = set_correlation_id("test-corr-999")
    user = UserContext(user_id="user-123", tenant_id="tenant-abc")
    user_token = set_user_context(user)

    filt = CorrelationIdFilter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="test message",
        args=(),
        exc_info=None,
    )

    res = filt.filter(record)
    assert res is True
    assert record.__dict__["correlation_id"] == "test-corr-999"
    assert record.__dict__["user_id"] == "user-123"
    assert record.__dict__["tenant_id"] == "tenant-abc"

    correlation_id_ctx.reset(corr_token)
    user_ctx.reset(user_token)


def test_sanitizer_filter_masks_record():
    filt = SanitizerFilter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Login with Bearer secret-tok-123",
        args=({"password": "plain_password", "name": "Alice"},),
        exc_info=None,
    )
    record.exc_text = "Traceback: in check(token='Bearer secret-tok-123')"
    record.__dict__["custom_secret"] = {"api_key": "sk-12345", "public": "ok"}

    assert filt.filter(record) is True
    assert "secret-tok-123" not in record.msg
    assert "***REDACTED***" in record.msg

    assert isinstance(record.args, dict)
    assert record.args["password"] == "***REDACTED***"
    assert record.args["name"] == "Alice"

    assert record.exc_text is not None
    assert "secret-tok-123" not in record.exc_text
    assert record.__dict__["custom_secret"]["api_key"] == "***REDACTED***"
    assert record.__dict__["custom_secret"]["public"] == "ok"
