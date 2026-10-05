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
    LogSanitizerFilter,
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


def test_correlation_id_filter_no_user():
    token = user_ctx.set(None)
    corr_token = correlation_id_ctx.set("")
    try:
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
        assert record.__dict__["user_id"] is None
        assert record.__dict__["tenant_id"] is None
    finally:
        user_ctx.reset(token)
        correlation_id_ctx.reset(corr_token)


def test_log_sanitizer_filter_masks_record_dict_and_tuple_args():
    filt = LogSanitizerFilter()
    # 1. Dict args
    record_dict = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Login with Bearer secret-tok-123",
        args={"password": "plain_password", "name": "Alice"},
        exc_info=None,
    )
    record_dict.exc_text = "Traceback: in check(token='Bearer secret-tok-123')"
    record_dict.__dict__["custom_secret"] = {"api_key": "sk-12345", "public": "ok"}

    assert filt.filter(record_dict) is True
    assert "secret-tok-123" not in record_dict.msg
    assert "***REDACTED***" in record_dict.msg

    assert isinstance(record_dict.args, dict)
    assert record_dict.args["password"] == "***REDACTED***"
    assert record_dict.args["name"] == "Alice"

    assert record_dict.exc_text is not None
    assert "secret-tok-123" not in record_dict.exc_text
    assert record_dict.__dict__["custom_secret"]["api_key"] == "***REDACTED***"
    assert record_dict.__dict__["custom_secret"]["public"] == "ok"

    # 2. Tuple args
    record_tuple = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="User %s with token %s",
        args=("Alice", "Bearer secret-tok-999"),
        exc_info=None,
    )
    assert filt.filter(record_tuple) is True
    assert isinstance(record_tuple.args, tuple)
    assert record_tuple.args[0] == "Alice"
    assert record_tuple.args[1] == "***REDACTED***"

    # 3. Non-string record msg (e.g. dict payload)
    record_msg_dict = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg={"password": "secret_pwd", "data": 123},  # type: ignore[arg-type]
        args=(),
        exc_info=None,
    )
    res_msg_dict = filt.filter(record_msg_dict)
    assert res_msg_dict is True
    assert isinstance(record_msg_dict.msg, dict)
    assert record_msg_dict.msg["password"] == "***REDACTED***"
    assert record_msg_dict.msg["data"] == 123

    # 4. Exception object in args
    err = ValueError("Failed connection with token Bearer secret-tok-888")
    record_err_args = logging.LogRecord(
        name="test_logger",
        level=logging.ERROR,
        pathname=__file__,
        lineno=10,
        msg="Error occurred: %s",
        args=(err,),
        exc_info=None,
    )
    res_err_args = filt.filter(record_err_args)
    assert res_err_args is True
    assert isinstance(record_err_args.args, tuple)
    assert "secret-tok-888" not in record_err_args.args[0]
    assert "***REDACTED***" in record_err_args.args[0]

    # 5. exc_info without pre-populated exc_text
    try:
        raise RuntimeError("Secret leaked in trace: Bearer secret-tok-777")
    except RuntimeError:
        import sys

        exc_info = sys.exc_info()

    record_exc_info = logging.LogRecord(
        name="test_logger",
        level=logging.ERROR,
        pathname=__file__,
        lineno=10,
        msg="Boom",
        args=(),
        exc_info=exc_info,
    )
    res_exc_info = filt.filter(record_exc_info)
    assert res_exc_info is True
    assert record_exc_info.exc_text is not None
    assert "secret-tok-777" not in record_exc_info.exc_text
    assert "***REDACTED***" in record_exc_info.exc_text
