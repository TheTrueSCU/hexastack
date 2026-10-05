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
from hexastack_logging.adapters.logger.loguru import LoguruAdapter


def test_loguru_adapter_all_methods_and_mock():
    mock_logger = MagicMock()
    bound_mock = MagicMock()
    mock_logger.bind.return_value = bound_mock

    adapter = LoguruAdapter(logger=mock_logger)

    corr_token = set_correlation_id("corr-12345")
    user_token = set_user_context(UserContext(user_id="usr-1", tenant_id="t-1"))

    # 1. Debug
    adapter.debug("Loguru debug", extra={"meta": "x"})
    mock_logger.bind.assert_called_with(
        meta="x",
        correlation_id="corr-12345",
        user_id="usr-1",
        tenant_id="t-1",
    )
    bound_mock.debug.assert_called_with("Loguru debug")

    # 2. Info
    adapter.info("Loguru info")
    bound_mock.info.assert_called_with("Loguru info")

    # 3. Warning
    adapter.warning("Loguru warn")
    bound_mock.warning.assert_called_with("Loguru warn")

    # 4. Error
    err = ValueError("Error")
    adapter.error("Loguru err", exc=err)
    bound_mock.opt.assert_called_with(exception=err)
    bound_mock.opt.return_value.error.assert_called_with("Loguru err")

    # 5. Critical
    adapter.critical("Loguru crit", exc=err)
    bound_mock.opt.assert_called_with(exception=err)
    bound_mock.opt.return_value.critical.assert_called_with("Loguru crit")

    correlation_id_ctx.reset(corr_token)
    user_ctx.reset(user_token)


def test_loguru_adapter_default_constructor():
    if importlib.util.find_spec("loguru") is not None:
        adapter = LoguruAdapter()
        assert adapter._logger is not None


def test_loguru_adapter_missing_dependency():
    with (
        patch("importlib.import_module", side_effect=ImportError("No loguru")),
        pytest.raises(MissingDependencyError, match="loguru is required") as exc_info,
    ):
        LoguruAdapter()
    assert isinstance(exc_info.value, HexastackError)
