import importlib.util
from unittest.mock import MagicMock, patch

import pytest

from hexastack_core.domain.exceptions import (
    HexastackError,
    MissingDependencyError,
)
from hexastack_core.utils.context import (
    UserContext,
    correlation_id_ctx,
    set_correlation_id,
    set_user_context,
    user_ctx,
)
from hexastack_logging.adapters.logger.structlog import StructlogAdapter


def test_structlog_adapter_all_methods_and_mock():
    mock_logger = MagicMock()
    adapter = StructlogAdapter(logger=mock_logger)

    corr_token = set_correlation_id("corr-structlog")
    user_token = set_user_context(
        UserContext(user_id="usr-struct", tenant_id="t-struct")
    )

    # 1. Debug
    adapter.debug("Structlog debug", extra={"meta": "abc"})
    mock_logger.debug.assert_called_with(
        "Structlog debug",
        meta="abc",
        correlation_id="corr-structlog",
        user_id="usr-struct",
        tenant_id="t-struct",
    )

    # 2. Info
    adapter.info("Structlog info")
    mock_logger.info.assert_called_with(
        "Structlog info",
        correlation_id="corr-structlog",
        user_id="usr-struct",
        tenant_id="t-struct",
    )

    # 3. Warning
    adapter.warning("Structlog warn")
    mock_logger.warning.assert_called_with(
        "Structlog warn",
        correlation_id="corr-structlog",
        user_id="usr-struct",
        tenant_id="t-struct",
    )

    # 4. Error
    err = ValueError("Structlog Error")
    adapter.error("Structlog err", exc=err)
    mock_logger.error.assert_called_with(
        "Structlog err",
        exc_info=err,
        correlation_id="corr-structlog",
        user_id="usr-struct",
        tenant_id="t-struct",
    )

    # 5. Critical
    adapter.critical("Structlog crit", exc=err)
    mock_logger.critical.assert_called_with(
        "Structlog crit",
        exc_info=err,
        correlation_id="corr-structlog",
        user_id="usr-struct",
        tenant_id="t-struct",
    )

    correlation_id_ctx.reset(corr_token)
    user_ctx.reset(user_token)


def test_structlog_adapter_default_constructor():
    if importlib.util.find_spec("structlog") is not None:
        adapter = StructlogAdapter()
        assert adapter._logger is not None


def test_structlog_adapter_missing_dependency():
    with (
        patch("importlib.import_module", side_effect=ImportError("No structlog")),
        pytest.raises(
            MissingDependencyError, match="structlog is required"
        ) as exc_info,
    ):
        StructlogAdapter()
    assert isinstance(exc_info.value, HexastackError)
