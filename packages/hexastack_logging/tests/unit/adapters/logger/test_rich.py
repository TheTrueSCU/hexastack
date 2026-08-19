import importlib.util
from unittest.mock import MagicMock, patch

import pytest

from hexastack_core.domain.exceptions import (
    HexastackError,
    MissingDependencyError,
)
from hexastack_core.utils.context import (
    correlation_id_ctx,
    set_correlation_id,
)
from hexastack_logging.adapters.logger.rich import RichLogger


def test_rich_logger_all_methods_and_console_mock():
    mock_console = MagicMock()
    logger = RichLogger(console=mock_console)

    corr_token = set_correlation_id("123456789abcdef")

    # 1. Debug
    logger.debug("Debug msg", extra={"user": "alice"})
    mock_console.print.assert_called_with(
        "[cyan][DEBUG   ][/cyan] [dim][corr:12345678][/dim] Debug msg [dim]{'user': 'alice'}[/dim]"
    )

    # 2. Info
    logger.info("Info msg")
    mock_console.print.assert_called_with(
        "[green][INFO    ][/green] [dim][corr:12345678][/dim] Info msg"
    )

    # 3. Warning
    logger.warning("Warning msg", extra={"warn_code": 42})
    mock_console.print.assert_called_with(
        "[yellow][WARNING ][/yellow] [dim][corr:12345678][/dim] Warning msg [dim]{'warn_code': 42}[/dim]"
    )

    # 4. Error
    err = ValueError("Something failed")
    logger.error("Error msg", extra={"err_code": 500}, exc=err)
    mock_console.print.assert_called_with(
        "[red][ERROR   ][/red] [dim][corr:12345678][/dim] Error msg [dim]{'err_code': 500}[/dim]\n[red]Something failed[/red]"
    )

    # 5. Critical
    logger.critical("Critical msg", exc=err)
    mock_console.print.assert_called_with(
        "[bold red][CRITICAL][/bold red] [dim][corr:12345678][/dim] Critical msg\n[red]Something failed[/red]"
    )

    correlation_id_ctx.reset(corr_token)


def test_rich_logger_default_constructor():
    if importlib.util.find_spec("rich") is not None:
        logger = RichLogger()
        assert logger._console is not None


def test_rich_logger_missing_dependency():
    with (
        patch("importlib.import_module", side_effect=ImportError("No rich")),
        pytest.raises(MissingDependencyError, match="rich is required") as exc_info,
    ):
        RichLogger()
    assert isinstance(exc_info.value, HexastackError)
